from unittest import TestCase

import os
import sys

import numpy as np
from numpy.testing import assert_almost_equal

try:
    from core.changefinder.utils import aryule, aryule_levinson, arburg
except ImportError:
    sys.path.append(os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 os.pardir), os.pardir))
    from core.changefinder.utils import aryule, aryule_levinson, arburg


class ChangeFInderYuleWalkerTest(TestCase):

    def setUp(self):
        self.c1 = np.array([1, 2, 3])
        self.a1 = np.array([1.33333333, 0.33333333])

        self.c2 = np.array([143.85, 141.95, 141.45, 142.30, 140.60,
                            140.00, 138.40, 137.10, 138.90, 139.85])
        self.a2 = np.array([2.90380682, 0.31235631, 1.26463104,
                            -3.30187384, -1.61653593, -2.10367317,
                            1.37563117, 2.18139823, 0.02314717])

        self.c3 = np.array([0, 0, 0])
        self.a3 = np.array([0, 0])

    def test_aryule(self):
        assert_almost_equal(self.a1, aryule(self.c1, 2))
        assert_almost_equal(self.a2, aryule(self.c2, 9))
        assert_almost_equal(self.a3, aryule(self.c3, 2))

    def test_aryule_levinson(self):
        assert_almost_equal(self.a1, aryule_levinson(self.c1, 2))
        assert_almost_equal(self.a2, aryule_levinson(self.c2, 9))
        assert_almost_equal(self.a3, aryule_levinson(self.c3, 2))


class ChangeFinderBurgTest(TestCase):

    def setUp(self):
        # Octave outputs
        self.x1 = np.array([1, 2, 3, 4, 5])
        self.a1 = np.array([-1.86391, 0.95710])

        self.x2 = np.array([143.85, 141.95, 141.45, 142.30, 140.60,
                            140.00, 138.40, 137.10, 138.90, 139.85])
        self.a2 = np.array([-1.31033, 0.58569, -0.56058, 0.63859, -0.35334])

        self.x3 = np.array([0, 0, 0, 0, 0])
        self.a3 = np.array([0, 0])

    def test_arburg(self):
        assert_almost_equal(self.a1, arburg(self.x1, 2), decimal=5)
        assert_almost_equal(self.a2, arburg(self.x2, 5), decimal=5)
        assert_almost_equal(self.a3, arburg(self.x3, 2))
