# -*- coding: utf-8 -*-
import numpy as np
import numpy.linalg as ln
from scipy.linalg import toeplitz


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
            float: Logloss for x.

        """
        assert xs.size >= self.order, 'size of xs must be greater or equal to `order`'

        # estimate mu
        self.mu = (1 - self.r) * self.mu + self.r * x

        # update c (coefficients of the Yule-Walker equation)
        self.c[0] = (1 - self.r) * self.c[0] + self.r * (x - self.mu) * (x - self.mu)  # c_0: x_t = x_{t-j}
        self.c[1:] = (1 - self.r) * self.c[1:] + self.r * (x - self.mu) * (xs[::-1][:self.order] - self.mu)

        # solve the Yule-Walker equation
        # TODO: replace here with 1d computation
        C = toeplitz(self.c[:self.order])
        a = np.dot(ln.inv(C), self.c[1:])  # a_1, ..., a_k

        # estimate x
        x_hat = np.dot(a, (xs[::-1][:self.order] - self.mu)) + self.mu

        # estimate sigma
        self.sigma = (1 - self.r) * self.sigma + self.r * (x - x_hat) ** 2

        # compute the probability density function
        p = np.exp(-0.5 * (x - x_hat) ** 2 / self.sigma) / ((2 * np.pi) ** (self.order / 2) * (self.sigma) ** 0.5)

        return -np.log(p)


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
        self.sdar_outlier = SDAR_1D(r, order)

        self.ys = np.array([])
        self.logloss_ys = np.array([])
        self.sdar_change = SDAR_1D(r, order)

    def update(self, x):
        """Update AR models based on 1d input x.

        Args:
            x (float): 1d input value.

        Returns:
            (float, float): (Outlier score, Change point score).

        """

        logloss_x = 0.0

        # Stage 1: Outlier Detection (SDAR #1)
        # need to wait until at least `order` (k) points are arrived
        if self.xs.size == self.order:
            logloss_x = self.sdar_outlier.update(x, self.xs)
            self.scores_outlier = self.add_one(logloss_x, self.scores_outlier, self.smooth)

        self.xs = self.add_one(x, self.xs, self.order)

        # Smoothing when we have enough (>T) first scores
        if self.scores_outlier.size == self.smooth:
            y = self.smoothing(self.scores_outlier)

            # Stage 2: Change Point Detection (SDAR #2)
            # need to wait until at least `order` (k) points are arrived
            if self.ys.size == self.order:
                logloss_y = self.sdar_change.update(y, self.ys)
                self.logloss_ys = self.add_one(logloss_y, self.logloss_ys, self.smooth)

            self.ys = self.add_one(y, self.ys, self.order)

        # Return outlier and change point scores
        return logloss_x, self.smoothing(self.logloss_ys)

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
