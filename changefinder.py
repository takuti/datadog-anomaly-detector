# -*- coding: utf-8 -*-
import numpy as np


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


class SDAR_1D:

    def __init__(self, r, order):
        """Train a AR model by using the SDAR algorithm (1d points only).

        Args:
            r (float): Forgetting parameter.
            order (int): Order of the AR model (i.e. k in the paper).

        """

        self.r = r
        self.order = order

        # initialize the parameters
        self.mu = np.random.random()
        self.sigma = np.random.random()
        self.c = np.zeros(self.order + 1)

    def update(self, x, xs):
        """Update the current AR model.

        Args:
            x (float): A new 1d point (t).
            xs (numpy array): `k` past points (..., t-k, ..., t-1).

        Returns:
            (float, float): (Logloss-based score for x, Estimated value of x)

        """
        assert xs.size >= self.order, 'xs must be order or more'

        # estimate mu
        self.mu = (1 - self.r) * self.mu + self.r * x

        # estimate c (Yule-Walker equation)
        self.c[0] = (1 - self.r) * self.c[0] + self.r * (x - self.mu) * (x - self.mu)  # c_0: x_t = x_{t-j}
        self.c[1:self.order] = (1 - self.r) * self.c[1:self.order] + self.r * (x - self.mu) * (xs[::-1][:(self.order - 1)] - self.mu)

        # solve the Yule-Walker equation
        a, e = LevinsonDurbin(self.c, self.order)

        # estimate x
        x_hat = np.dot(-a[1:], (xs[::-1] - self.mu)) + self.mu

        # estimate sigma
        self.sigma = (1 - self.r) * self.sigma + self.r * (x - x_hat) * (x - x_hat)

        # compute the probability density function
        p = np.exp(-0.5 * (x - x_hat)**2 / self.sigma) / ((2 * np.pi)**0.5 * self.sigma**0.5)

        return -np.log(p), x_hat


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
        self.sdar_outlier = SDAR_1D(r, self.order)

        self.ys = np.array([])
        self.scores_change = np.array([])
        self.sdar_change = SDAR_1D(r, self.order)

    def update(self, x):
        """Update AR models based on 1d input x.

        Args:
            x (float): 1d input value.

        Returns:
            (float, float): (Smoothed) {outlier, change point} score for the input value.

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

        # Return smoothed {outlier, change point} scores
        return self.smoothing(self.scores_outlier), self.smoothing(self.scores_change)

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
        return 0.0 if window.size == 0 else np.sum(window) / window.size
