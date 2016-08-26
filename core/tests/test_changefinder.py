from unittest import TestCase

import os
import sys

import numpy as np
from numpy.testing import assert_almost_equal

try:
    from core.changefinder.utils import aryule
except ImportError:
    sys.path.append(os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 os.pardir), os.pardir))
    from core.changefinder.utils import aryule


class ChangeFinderUtilsTest(TestCase):

    def test_aryule(self):
        c = np.array([1, 2, 3])
        k = 2
        a = aryule(c, k)
        assert_almost_equal(np.array([1.33333333, 0.33333333]), a)

        c = np.array([143.85, 141.95, 141.45, 142.30, 140.60,
                      140.00, 138.40, 137.10, 138.90, 139.85])
        k = 9
        a = aryule(c, k)
        assert_almost_equal(np.array([2.90380682, 0.31235631, 1.26463104,
                                      -3.30187384, -1.61653593, -2.10367317,
                                      1.37563117, 2.18139823, 0.02314717]), a)
