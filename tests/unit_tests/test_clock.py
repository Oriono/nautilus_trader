#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
# <copyright file="test_clock.py" company="Invariance Pte">
#  Copyright (C) 2018-2019 Invariance Pte. All rights reserved.
#  The use of this source code is governed by the license as found in the LICENSE.md file.
#  http://www.invariance.com
# </copyright>
# -------------------------------------------------------------------------------------------------

import unittest

from datetime import datetime, timezone, timedelta

from inv_trader.common.clock import Clock, LiveClock, TestClock, TestTimer
from inv_trader.model.identifiers import Label


class ClockTests(unittest.TestCase):

    def setUp(self):
        # Fixture Setup
        self.clock = Clock()

    def test_timezone(self):
        # Arrange
        # Act
        result = self.clock.timezone

        # Assert
        self.assertEqual(timezone.utc, result)

    def test_unix_epoch(self):
        # Arrange
        # Act
        result = self.clock.unix_epoch()
        # Assert
        self.assertEqual(datetime(1970, 1, 1, 0, 0, 0, 0, timezone.utc), result)


class LiveClockTests(unittest.TestCase):

    def setUp(self):
        # Fixture Setup
        self.clock = LiveClock()

    def tearDown(self):
        self.clock.stop_all_timers()

    def test_time_now(self):
        # Arrange
        # Act
        result = self.clock.time_now()

        # Assert
        self.assertEqual(timezone.utc, result.tzinfo)


class TestClockTests(unittest.TestCase):

    def setUp(self):
        # Fixture Setup
        self.clock = TestClock()

    def tearDown(self):
        self.clock.stop_all_timers()

    def test_time_now(self):
        # Arrange
        # Act
        result = self.clock.time_now()

        # Assert
        self.assertEqual(datetime(1970, 1, 1, 0, 0, 0, 0, timezone.utc), result)

    def test_set_time(self):
        # Arrange
        new_time = datetime(1970, 2, 1, 0, 0, 1, 0, timezone.utc)

        # Act
        self.clock.set_time(new_time)
        result = self.clock.time_now()

        # Assert
        self.assertEqual(new_time, result)

    def test_iterate_time(self):
        # Arrange
        new_time = datetime(1970, 2, 1, 0, 0, 1, 0, timezone.utc)

        # Act
        self.clock.iterate_time(new_time)
        result = self.clock.time_now()

        # Assert
        self.assertEqual(new_time, result)

    def test_can_set_time_alert(self):
        # Arrange
        receiver = []
        alert_time = self.clock.unix_epoch() + timedelta(minutes=1)

        # Act
        self.clock.set_time_alert(Label("test_alert1"), alert_time, receiver.append)

        # Assert
        self.assertEqual(1, len(self.clock.get_labels()))

    def test_cancel_time_alert(self):
        # Arrange
        receiver = []
        alert_time = self.clock.unix_epoch() + timedelta(minutes=1)
        self.clock.set_time_alert(Label("test_alert1"), alert_time, receiver.append)

        # Act
        self.clock.cancel_time_alert(Label("test_alert1"))

        # Assert
        self.assertEqual(0, len(self.clock.get_labels()))

    def test_raises_time_alert(self):
        # Arrange
        receiver = []
        alert_time = self.clock.unix_epoch() + timedelta(minutes=1)
        self.clock.set_time_alert(Label("test_alert1"), alert_time, receiver.append)

        # Act
        self.clock.iterate_time(self.clock.unix_epoch() + timedelta(minutes=1))

        # Assert
        self.assertEqual(1, len(receiver))
        self.assertEqual(0, len(self.clock.get_labels()))

    def test_raises_time_alerts(self):
        # Arrange
        receiver = []
        alert_time1 = self.clock.unix_epoch() + timedelta(minutes=1)
        alert_time2 = self.clock.unix_epoch() + timedelta(minutes=1, seconds=30)
        self.clock.set_time_alert(Label("test_alert1"), alert_time1, receiver.append)
        self.clock.set_time_alert(Label("test_alert2"), alert_time2, receiver.append)

        # Act
        self.clock.iterate_time(self.clock.unix_epoch() + timedelta(minutes=1))

        # Assert
        self.assertEqual(2, len(receiver))
        self.assertEqual(0, len(self.clock.get_labels()))

    def test_can_set_timer(self):
        # Arrange
        receiver = []
        start_time = self.clock.unix_epoch()
        stop_time = self.clock.unix_epoch() + timedelta(minutes=5)
        interval = timedelta(minutes=1)

        # Act
        self.clock.set_timer(
            Label("test_timer1"),
            interval,
            start_time,
            stop_time,
            True,
            receiver.append)

        # Assert
        self.assertEqual(1, len(self.clock.get_labels()))

    def test_timer(self):
        # Arrange
        receiver = []
        start_time = self.clock.unix_epoch()
        stop_time = self.clock.unix_epoch() + timedelta(minutes=5)
        interval = timedelta(minutes=1)

        test_timer = TestTimer(
            Label("test_timer1"),
            interval,
            start_time,
            stop_time,
            True,
            receiver.append)

        # Act
        test_timer.advance(stop_time)

        # Assert
        self.assertEqual(1, len(receiver))
        self.assertEqual(0, len(self.clock.get_labels()))

    def test_timer_raises_multiple_time_alerts(self):
        # Arrange
        receiver = []
        start_time = self.clock.unix_epoch()
        stop_time = self.clock.unix_epoch() + timedelta(minutes=5)
        interval = timedelta(minutes=1)

        self.clock.set_timer(
            Label("test_timer1"),
            interval,
            start_time,
            stop_time,
            True,
            receiver.append)

        # Act
        self.clock.iterate_time(stop_time)

        # Assert
        self.assertEqual(5, len(receiver))
        self.assertEqual(0, len(self.clock.get_labels()))