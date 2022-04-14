# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2022 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

import itertools
from typing import Dict, List, Optional

import pandas as pd

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.engine import BacktestEngineConfig
from nautilus_trader.backtest.results import BacktestResult
from nautilus_trader.config import BacktestDataConfig
from nautilus_trader.config import BacktestRunConfig
from nautilus_trader.config import BacktestVenueConfig
from nautilus_trader.model.currency import Currency
from nautilus_trader.model.data.bar import Bar
from nautilus_trader.model.data.base import DataType
from nautilus_trader.model.data.base import GenericData
from nautilus_trader.model.data.tick import QuoteTick
from nautilus_trader.model.data.tick import TradeTick
from nautilus_trader.model.data.venue import InstrumentStatusUpdate
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import BookTypeParser
from nautilus_trader.model.enums import OMSType
from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.model.orderbook.data import OrderBookData
from nautilus_trader.model.orderbook.data import OrderBookDelta
from nautilus_trader.persistence.batching import batch_files
from nautilus_trader.persistence.catalog import DataCatalog
from nautilus_trader.persistence.util import is_nautilus_class


class BacktestNode:
    """
    Provides a node for orchestrating groups of configurable backtest runs.
    """

    def run(self, run_configs: List[BacktestRunConfig], **kwargs) -> List[BacktestResult]:
        """
        Run a list of backtest configs synchronously.

        Parameters
        ----------
        run_configs : list[BacktestRunConfig]
            The backtest run configurations.

        Returns
        -------
        list[BacktestResult]
            The results of the backtest runs.

        """
        results: List[BacktestResult] = []
        for config in run_configs:
            config.check()  # check all values set
            result = self._run(
                run_config_id=config.id,
                engine_config=config.engine,
                venue_configs=config.venues,
                data_configs=config.data,
                batch_size_bytes=config.batch_size_bytes,
                **kwargs,
            )
            results.append(result)

        return results

    def _run(
        self,
        run_config_id: str,
        engine_config: BacktestEngineConfig,
        venue_configs: List[BacktestVenueConfig],
        data_configs: List[BacktestDataConfig],
        batch_size_bytes: Optional[int] = None,
        return_engine: bool = False,
    ) -> BacktestResult:
        engine: BacktestEngine = self._create_engine(
            config=engine_config,
            venue_configs=venue_configs,
            data_configs=data_configs,
        )

        # Setup persistence
        if engine_config is not None and engine_config.persistence is not None:
            catalog = engine_config.persistence.as_catalog()
            # Manually write instruments
            instrument_ids = set(filter(None, (data.instrument_id for data in data_configs)))
            for writer in engine.kernel.persistence_writers:
                for instrument in catalog.instruments(
                    instrument_ids=list(instrument_ids),
                    as_nautilus=True,
                ):
                    writer.write(instrument)

        # Run backtest
        backtest_runner(
            run_config_id=run_config_id,
            engine=engine,
            data_configs=data_configs,
            batch_size_bytes=batch_size_bytes,
        )

        result = engine.get_result()

        for writer in engine.kernel.persistence_writers:
            writer.close()

        if return_engine:
            return engine

        return result

    def _create_engine(
        self,
        config: BacktestEngineConfig,
        venue_configs: List[BacktestVenueConfig],
        data_configs: List[BacktestDataConfig],
    ) -> BacktestEngine:
        # Build the backtest engine
        engine = BacktestEngine(config=config)

        # Add instruments
        for config in data_configs:
            if is_nautilus_class(config.data_type):
                instruments = config.catalog().instruments(
                    instrument_ids=config.instrument_id, as_nautilus=True
                )
                for instrument in instruments or []:
                    engine.add_instrument(instrument)

        # Add venues
        for config in venue_configs:
            base_currency: Optional[str] = config.base_currency
            engine.add_venue(
                venue=Venue(config.name),
                oms_type=OMSType[config.oms_type],
                account_type=AccountType[config.account_type],
                base_currency=Currency.from_str(base_currency) if base_currency else None,
                starting_balances=[Money.from_str(m) for m in config.starting_balances],
                book_type=BookTypeParser.from_str_py(config.book_type),
                routing=config.routing,
            )
        return engine


def _load_engine_data(engine: BacktestEngine, data) -> None:
    if data["type"] in (QuoteTick, TradeTick):
        engine.add_ticks(data=data["data"])
    elif data["type"] == Bar:
        engine.add_bars(data=data["data"])
    elif data["type"] in (OrderBookDelta, OrderBookData):
        engine.add_order_book_data(data=data["data"])
    elif data["type"] in (InstrumentStatusUpdate,):
        engine.add_data(data=data["data"])
    elif not is_nautilus_class(data["type"]):
        engine.add_generic_data(client_id=data["client_id"], data=data["data"])
    else:
        raise ValueError(f"Data type {data['type']} not setup for loading into backtest engine")


def backtest_runner(
    run_config_id: str,
    engine: BacktestEngine,
    data_configs: List[BacktestDataConfig],
    batch_size_bytes: Optional[int] = None,
):
    """Execute a backtest run."""
    if batch_size_bytes is not None:
        return streaming_backtest_runner(
            run_config_id=run_config_id,
            engine=engine,
            data_configs=data_configs,
            batch_size_bytes=batch_size_bytes,
        )

    # Load data
    for config in data_configs:
        t0 = pd.Timestamp.now()
        engine._log.info(f"Reading {config.data_type} data for instrument={config.instrument_id}.")
        d = config.load()
        if config.instrument_id and d["instrument"] is None:
            print(f"Requested instrument_id={d['instrument']} from data_config not found catalog")
            continue
        if not d["data"]:
            print(f"No data found for {config}")
            continue

        t1 = pd.Timestamp.now()
        engine._log.info(f"Read {len(d['data']):,} events from parquet in {pd.Timedelta(t1-t0)}s.")
        _load_engine_data(engine=engine, data=d)
        t2 = pd.Timestamp.now()
        engine._log.info(f"Engine load took {pd.Timedelta(t2-t1)}s")

    engine.run(run_config_id=run_config_id)


def _groupby_key(x):
    return type(x).__name__


def groupby_datatype(data):
    return [
        {"type": type(v[0]), "data": v}
        for v in [
            list(v) for _, v in itertools.groupby(sorted(data, key=_groupby_key), key=_groupby_key)
        ]
    ]


def _extract_generic_data_client_id(data_configs: List[BacktestDataConfig]) -> Dict:
    """
    Extract a mapping of data_type : client_id from the list of `data_configs`.
    In the process of merging the streaming data, we lose the `client_id` for
    generic data, we need to inject this back in so the backtest engine can be
    correctly loaded.
    """
    data_client_ids = [
        (config.data_type, config.client_id) for config in data_configs if config.client_id
    ]
    assert len(set(data_client_ids)) == len(
        dict(data_client_ids)
    ), "data_type found with multiple client_ids"
    return dict(data_client_ids)


def streaming_backtest_runner(
    run_config_id: str,
    engine: BacktestEngine,
    data_configs: List[BacktestDataConfig],
    batch_size_bytes: Optional[int] = None,
):
    config = data_configs[0]
    catalog: DataCatalog = config.catalog()

    data_client_ids = _extract_generic_data_client_id(data_configs=data_configs)

    for batch in batch_files(
        catalog=catalog,
        data_configs=data_configs,
        target_batch_size_bytes=batch_size_bytes,
    ):
        engine.clear_data()
        grouped = groupby_datatype(batch)
        for data in grouped:
            if data["type"] in data_client_ids:
                # Generic data - manually re-add client_id as it gets lost in the streaming join
                data.update({"client_id": ClientId(data_client_ids[data["type"]])})
                data["data"] = [
                    GenericData(data_type=DataType(data["type"]), data=d) for d in data["data"]
                ]
            _load_engine_data(engine=engine, data=data)
        engine.run_streaming(run_config_id=run_config_id)
    engine.end_streaming()
