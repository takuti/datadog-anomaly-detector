# -*- coding: utf-8 -*-
import numpy as np
import math


def LevinsonDurbin(r, lpcOrder):
    """
    from http://aidiary.hatenablog.com/entry/20120415/1334458954
    """
    a = np.zeros(lpcOrder + 1, dtype=np.float64)
    e = np.zeros(lpcOrder + 1, dtype=np.float64)

    a[0] = 1.0
    a[1] = - r[1] / r[0]
    e[1] = r[0] + r[1] * a[1]
    lam = - r[1] / r[0]

    for k in range(1, lpcOrder):
        lam = 0.0
        for j in range(k + 1):
            lam -= a[j] * r[k + 1 - j]
        lam /= e[k]

        U = [1]
        U.extend([a[i] for i in range(1, k + 1)])
        U.append(0)

        V = [0]
        V.extend([a[i] for i in range(k, 0, -1)])
        V.append(1)

        a = np.array(U) + lam * np.array(V)
        e[k + 1] = e[k] * (1.0 - lam * lam)

    return a, e[-1]


class _SDAR_1Dim(object):
    def __init__(self, r, order):
        self._r = r
        self._mu = np.random.random()
        self._sigma = np.random.random()
        self._order = order
        self._c = np.zeros(self._order + 1)

    def update(self, x, term):
        assert len(term) >= self._order, "term must be order or more"
        term = np.array(term)
        self._mu = (1 - self._r) * self._mu + self._r * x
        for i in range(1, self._order):
            self._c[i] = (1 - self._r) * self._c[i] + self._r * (x - self._mu) * (term[-i] - self._mu)
        self._c[0] = (1 - self._r) * self._c[0] + self._r * (x - self._mu) * (x - self._mu)
        what, e = LevinsonDurbin(self._c, self._order)
        xhat = np.dot(-what[1:], (term[::-1] - self._mu)) + self._mu
        self._sigma = (1 - self._r) * self._sigma + self._r * (x - xhat) * (x - xhat)
        return -math.log(math.exp(-0.5 * (x - xhat)**2 / self._sigma) / ((2 * math.pi)**0.5 * self._sigma**0.5)), xhat


class ChangeFinder:

    def __init__(self, r=0.5, order=1, smooth=7):
        """ChangeFinder.

        Args:
            r (float): Forgetting parameter.
            order (int): Order of the AR model (i.e. k in the paper).
            smooth (int): Window size for the simple moving average (i.e. T).

        """

        assert order > 0, 'order must be 1 or more.'
        assert smooth > 2, 'term must be 3 or more.'

        self.r = r
        self.order = order
        self.smooth = smooth

        self.xs = np.array([])
        self.scores_outlier = np.array([])
        self.sdar_outlier = _SDAR_1Dim(r, self.order)

        self.ys = np.array([])
        self.scores_change = np.array([])
        self.sdar_change = _SDAR_1Dim(r, self.order)

    def update(self, x):
        """Update AR models based on 1d input x.

        Args:
            x (float): 1d input value.

        Returns:
            float: (Smoothed) change point score for the input value.

        """

        # Stage 1: Outlier Detection (SDAR #1)
        # need to wait until at least `order` (k) points are arrived
        if self.xs.size == self.order:
            score, predict = self.sdar_outlier.update(x, self.xs)
            self.scores_outlier = self.add_one(score, self.scores_outlier, self.smooth)

        self.xs = self.add_one(x, self.xs, self.order)

        # Smoothing when we have enough (>T) first scores
        if self.scores_outlier.size == self.smooth:
            y = self.smoothing(self.scores_outlier)

            # Stage 2: Change Point Detection (SDAR #2)
            # need to wait until at least `order` (k) points are arrived
            if self.ys.size == self.order:
                score, predict = self.sdar_change.update(y, self.ys)
                self.scores_change = self.add_one(score, self.scores_change, self.smooth)

            self.ys = self.add_one(y, self.ys, self.order)

        # Smoothing when we have enough (>T) second scores
        if self.scores_change.size == self.smooth:
            return self.smoothing(self.scores_change)
        else:
            return 0.0

    def add_one(self, x, window, window_size):
        """Insert a sample x into a fix-sized window.

        Args:
            x (float): A sample value.
            window (numpy array): Fixed sized window.
            window_size (int): Maximum size of the window.

        Returns:
            numpy array: An updated window.

        """
        window = np.append(window, x)

        # delete oldest point
        if window.size > window_size:
            window = np.delete(window, 0)

        return window

    def smoothing(self, window):
        """Return a smoothed value of the current window.

        Args:
            window (numpy array): Fixed sized window.

        Returns:
            float: A smoothed value of the given window.

        """
        return np.sum(window) / window.size
