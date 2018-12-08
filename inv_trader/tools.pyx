#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
# <copyright file="tools.pyx" company="Invariance Pte">
#  Copyright (C) 2018 Invariance Pte. All rights reserved.
#  The use of this source code is governed by the license as found in the LICENSE.md file.
#  http://www.invariance.com
# </copyright>
# -------------------------------------------------------------------------------------------------

import cython
import inspect

from typing import Callable, List
from pandas.core.frame import Series, DataFrame
from inv_trader.model.objects import DataBar


POINT = 'point'
PRICE = 'price'
MID = 'mid'
OPEN = 'open'
HIGH = 'high'
LOW = 'low'
CLOSE = 'close'
VOLUME = 'volume'
TIMESTAMP = 'timestamp'

cdef class BarBuilder:
    """
    Provides a means of building lists of bars from a given Pandas DataFrame of
    the correct specification.
    """
    cdef object _data
    cdef int _volume_multiple

    def __init__(self, data: DataFrame, volume_multiple: int):
        """
        Initializes a new instance of the BarBuilder class.

        :param volume_multiple: The volume multiple for the builder.
        """
        self._data = data
        self._volume_multiple = volume_multiple

    @cython.boundscheck(False)
    @cython.wraparound(False)
    @cython.binding(True)
    cdef object deconstruct_row(self, object row):
        return DataBar(row[1][0],
                       row[1][1],
                       row[1][2],
                       row[1][3],
                       row[1][4] * self._volume_multiple,
                       row[0])

    cpdef object build_bars_apply(self):
        """
        Build a bar from the held Pandas DataFrame.
        
        :return: The bars.
        """
        return self._data.apply(self.deconstruct_row, axis=1)

    @cython.boundscheck(False)
    @cython.wraparound(False)
    @cython.binding(True)
    cpdef object build_bars_iter(self):
        """
        Build a bar from the held Pandas DataFrame.
        
        :return: The bars.
        """
        bars = []
        for row in self._data.iterrows():
            bars.append(self.deconstruct_row(row))

        return bars


cdef class IndicatorUpdater:
    """
    Provides an adapter for updating an indicator with a bar. When instantiated
    with a live indicator update method, the updater will inspect the method and
    construct the required parameter list for updates.
    """
    cdef object _indicator
    cdef object _input_method
    cdef list _input_params
    cdef list _outputs

    cdef readonly list _output_values

    def __init__(self,
                 indicator: object,
                 input_method: Callable or None=None,
                 outputs: List[str] or None=None):
        """
        Initializes a new instance of the IndicatorUpdater class.

        :param indicator: The indicator for updating.
        :param input_method: The indicators input method.
        :param outputs: The list of the indicators output properties.
        """
        self._indicator = indicator
        if input_method is None:
            self._input_method = indicator.input
        else:
            self._input_method = input_method

        self._input_params = []

        param_map = {
            POINT: CLOSE,
            PRICE: CLOSE,
            MID: CLOSE,
            OPEN: OPEN,
            HIGH: HIGH,
            LOW: LOW,
            CLOSE: CLOSE,
            TIMESTAMP: TIMESTAMP
        }

        for param in inspect.signature(self._input_method).parameters:
            self._input_params.append(param_map[param])

        if outputs is None or len(outputs) == 0:
            self._outputs = ['value']
        else:
            self._outputs = outputs

        self._output_values = self._get_outputs()

    cpdef update_bar(self, object bar):
        """
        Update the indicator with the given Bar object.

        :param bar: The update bar.
        """
        self._input_method(*[bar.__getattribute__(param) for param in self._input_params])
        self._output_values = self._get_outputs()

    cpdef update_row(self, object row: Series):
        """
        Update the indicator with the given Pandas Series row.
        
        :param row: The update row.
        """
        self._input_method(*row[param] for param in self._input_params)
        self._output_values = self._get_outputs()

    cdef object _get_outputs(self):
        """
        Create a list of the current indicator outputs.
        
        :return: The list of indicator outputs.
        """
        return [self._indicator.__getattribute__(output) for output in self._outputs]