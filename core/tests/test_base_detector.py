from unittest import TestCase

import os
import sys
import time

try:
    from core.base_detector import Detector
except ImportError:
    sys.path.append(os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 os.pardir), os.pardir))
    from core.base_detector import Detector


class TestDetector(Detector):

    def __init__(self):
        super().__init__('changefinder', 'config/datadog.ini')


class BaseDetectorTestCase(TestCase):

    def setUp(self):
        self.detector = TestDetector()

    def test_select_k(self):
        k = self.detector.select_k('system.cpu.idle{*}by{host}')
        self.assertTrue((type(k) is int) and (1 <= k and k <= 50))

    def test_dd_load_config(self):
        keys_init = list(self.detector.dd_sections.keys())
        self.detector.load_dd_config()
        self.assertListEqual(sorted(list(self.detector.dd_sections.keys())),
                             sorted(keys_init))

    def test_query(self):
        now = int(time.time())
        self.detector.query(now - 60, now)
