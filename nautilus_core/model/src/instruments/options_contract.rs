// -------------------------------------------------------------------------------------------------
//  Copyright (C) 2015-2024 Nautech Systems Pty Ltd. All rights reserved.
//  https://nautechsystems.io
//
//  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
//  You may not use this file except in compliance with the License.
//  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
// -------------------------------------------------------------------------------------------------

use std::{
    any::Any,
    hash::{Hash, Hasher},
};

use anyhow::Result;
use nautilus_core::time::UnixNanos;
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use ustr::Ustr;

use super::Instrument;
use crate::{
    enums::{AssetClass, InstrumentClass, OptionKind},
    identifiers::{instrument_id::InstrumentId, symbol::Symbol},
    types::{currency::Currency, price::Price, quantity::Quantity},
};

#[repr(C)]
#[derive(Clone, Debug, Serialize, Deserialize)]
#[cfg_attr(
    feature = "python",
    pyclass(module = "nautilus_trader.core.nautilus_pyo3.model")
)]
#[cfg_attr(feature = "trivial_copy", derive(Copy))]
pub struct OptionsContract {
    #[pyo3(get)]
    pub id: InstrumentId,
    #[pyo3(get)]
    pub raw_symbol: Symbol,
    #[pyo3(get)]
    pub asset_class: AssetClass,
    pub underlying: Ustr,
    #[pyo3(get)]
    pub option_kind: OptionKind,
    #[pyo3(get)]
    pub activation_ns: UnixNanos,
    #[pyo3(get)]
    pub expiration_ns: UnixNanos,
    #[pyo3(get)]
    pub strike_price: Price,
    #[pyo3(get)]
    pub currency: Currency,
    #[pyo3(get)]
    pub price_precision: u8,
    #[pyo3(get)]
    pub price_increment: Price,
    #[pyo3(get)]
    pub multiplier: Quantity,
    #[pyo3(get)]
    pub lot_size: Quantity,
    #[pyo3(get)]
    pub max_quantity: Option<Quantity>,
    #[pyo3(get)]
    pub min_quantity: Option<Quantity>,
    #[pyo3(get)]
    pub max_price: Option<Price>,
    #[pyo3(get)]
    pub min_price: Option<Price>,
    #[pyo3(get)]
    pub ts_event: UnixNanos,
    #[pyo3(get)]
    pub ts_init: UnixNanos,
}

impl OptionsContract {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        id: InstrumentId,
        raw_symbol: Symbol,
        asset_class: AssetClass,
        underlying: Ustr,
        option_kind: OptionKind,
        activation_ns: UnixNanos,
        expiration_ns: UnixNanos,
        strike_price: Price,
        currency: Currency,
        price_precision: u8,
        price_increment: Price,
        multiplier: Quantity,
        lot_size: Quantity,
        max_quantity: Option<Quantity>,
        min_quantity: Option<Quantity>,
        max_price: Option<Price>,
        min_price: Option<Price>,
        ts_event: UnixNanos,
        ts_init: UnixNanos,
    ) -> Result<Self> {
        Ok(Self {
            id,
            raw_symbol,
            asset_class,
            underlying,
            option_kind,
            activation_ns,
            expiration_ns,
            strike_price,
            currency,
            price_precision,
            price_increment,
            multiplier,
            lot_size,
            max_quantity,
            min_quantity,
            max_price,
            min_price,
            ts_event,
            ts_init,
        })
    }
}

impl PartialEq<Self> for OptionsContract {
    fn eq(&self, other: &Self) -> bool {
        self.id == other.id
    }
}

impl Eq for OptionsContract {}

impl Hash for OptionsContract {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.id.hash(state);
    }
}

impl Instrument for OptionsContract {
    fn id(&self) -> &InstrumentId {
        &self.id
    }

    fn raw_symbol(&self) -> &Symbol {
        &self.raw_symbol
    }

    fn asset_class(&self) -> AssetClass {
        self.asset_class
    }

    fn instrument_class(&self) -> InstrumentClass {
        InstrumentClass::Option
    }

    fn quote_currency(&self) -> &Currency {
        &self.currency
    }

    fn base_currency(&self) -> Option<&Currency> {
        None
    }

    fn settlement_currency(&self) -> &Currency {
        &self.currency
    }

    fn is_inverse(&self) -> bool {
        false
    }

    fn price_precision(&self) -> u8 {
        self.price_precision
    }

    fn size_precision(&self) -> u8 {
        0
    }

    fn price_increment(&self) -> Price {
        self.price_increment
    }

    fn size_increment(&self) -> Quantity {
        Quantity::from(1)
    }

    fn multiplier(&self) -> Quantity {
        self.multiplier
    }

    fn lot_size(&self) -> Option<Quantity> {
        Some(self.lot_size)
    }

    fn max_quantity(&self) -> Option<Quantity> {
        self.max_quantity
    }

    fn min_quantity(&self) -> Option<Quantity> {
        self.min_quantity
    }

    fn max_price(&self) -> Option<Price> {
        self.max_price
    }

    fn min_price(&self) -> Option<Price> {
        self.min_price
    }

    fn ts_event(&self) -> UnixNanos {
        self.ts_event
    }

    fn ts_init(&self) -> UnixNanos {
        self.ts_init
    }

    fn as_any(&self) -> &dyn Any {
        self
    }
}

////////////////////////////////////////////////////////////////////////////////
// Tests
////////////////////////////////////////////////////////////////////////////////
#[cfg(test)]
mod tests {
    use rstest::rstest;

    use crate::instruments::{options_contract::OptionsContract, stubs::*};

    #[rstest]
    fn test_equality(options_contract_appl: OptionsContract) {
        let options_contract_appl2 = options_contract_appl.clone();
        assert_eq!(options_contract_appl, options_contract_appl2);
    }
}