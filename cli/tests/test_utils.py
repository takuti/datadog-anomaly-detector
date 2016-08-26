from unittest import TestCase

import os
import sys
import pytz

try:
    import utils
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
    import utils


class Str2TimestampTestCase(TestCase):

    def test_different_timezone(self):
        s = '2016-08-10 12:00'
        utc = utils.str2timestamp(s, 'UTC')
        jst = utils.str2timestamp(s, 'Asia/Tokyo')

        # converted timestamp from the same date-time string
        # => UTC = JST + 9h
        self.assertEqual(utc - jst, 60 * 60 * 9)

    def test_invalid_dateformat(self):
        with self.assertRaises(ValueError):
            utils.str2timestamp('2016-08-10 12:00:00', 'UTC')

    def test_invalid_timezone(self):
        with self.assertRaises(pytz.exceptions.UnknownTimeZoneError):
            utils.str2timestamp('2016-08-10 12:00', 'XXX')
