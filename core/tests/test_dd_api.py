from unittest import TestCase

import os
import sys
import time

try:
    from core.datadog_api_helper import DatadogAPIHelper
except ImportError:
    sys.path.append(os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 os.pardir), os.pardir))
    from core.datadog_api_helper import DatadogAPIHelper


class DatadogAPIHelperTest(TestCase):

    def setUp(self):
        self.dd = DatadogAPIHelper(os.environ['DD_APP_KEY'], os.environ['DD_API_KEY'])
        self.end = int(time.time())
        self.start = self.end - 300
        self.query = 'system.cpu.idle{*}by{host}'

    def test_get_series(self):
        series = self.dd.get_series(self.start, self.end, self.query)
        self.assertTrue((series[0]['time'] / 1000 >= self.start) and
                        (series[-1]['time'] / 1000 <= self.end))

    def test_get_series_invalid_parameters(self):
        with self.assertRaises(RuntimeError):
            self.dd.get_series(self.start, self.end, 'xxx')
