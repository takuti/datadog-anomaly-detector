import numpy as np

from .utils import aryule_levinson

from logging import getLogger
logger = getLogger('ChangeFinder')


class SDAR_1D:

    def __init__(self, r, k):
        """Train a AR(k) model by using the SDAR algorithm (1d points only).

        Args:
            r (float): Discounting parameter.
            k (int): Order of the AR model.

        """

        self.r = r
        self.k = k

        # initialize the parameters
        self.mu = self.sigma = 0.0
        self.c = np.zeros(self.k + 1)

    def update(self, x, xs):
        """Update the current AR model.

        Args:
            x (float): A new 1d point (t).
            xs (numpy array): `k` past points (..., t-k, ..., t-1).

        Returns:
            float: Logloss for x.

        """
        assert xs.size >= self.k, 'size of xs must be greater or equal to the order of the AR model.'

        # estimate mu
        self.mu = (1 - self.r) * self.mu + self.r * x

        # update c (coefficients of the Yule-Walker equation)
        self.c[0] = (1 - self.r) * self.c[0] + self.r * (x - self.mu) * (x - self.mu)  # c_0: x_t = x_{t-j}
        self.c[1:] = (1 - self.r) * self.c[1:] + self.r * (x - self.mu) * (xs[::-1][:self.k] - self.mu)

        # a_1, ..., a_k
        a = aryule_levinson(self.c, self.k)

        # estimate x
        x_hat = np.dot(a, (xs[::-1][:self.k] - self.mu)) + self.mu

        # estimate sigma
        self.sigma = (1 - self.r) * self.sigma + self.r * (x - x_hat) ** 2

        # compute the probability density function
        p = np.exp(-0.5 * (x - x_hat) ** 2 / self.sigma) / ((2 * np.pi) ** 0.5 * (self.sigma) ** 0.5)

        return -np.log(p)


class ChangeFinder:

    def __init__(self, r=0.5, k=1, T1=7, T2=7):
        """ChangeFinder.

        Args:
            r (float): Discounting parameter.
            k (int): Order of the AR model (i.e. consider a AR(k) process).
            T1 (int): Window size for the simple moving average of outlier scores.
            T2 (int): Window size to compute a change point score.

        """

        assert k > 0, 'k must be 1 or more.'

        self.r = r
        self.k = k
        self.T1 = T1
        self.T2 = T2

        self.xs = np.zeros(k)
        self.outliers = np.zeros(T1)
        self.sdar_outlier = SDAR_1D(r, k)

        self.ys = np.zeros(k)
        self.changes = np.zeros(T2)
        self.sdar_change = SDAR_1D(r, k)

    def update(self, x):
        """Update AR models based on 1d input x.

        Args:
            x (float): 1d input value.

        Returns:
            (float, float): (Outlier score, Change point score).

        """

        # Stage 1: Outlier Detection (SDAR #1)
        outlier = self.sdar_outlier.update(x, self.xs)
        self.outliers = self.__append(self.outliers, outlier, self.T1)

        self.xs = self.__append(self.xs, x, self.k)

        # Smoothing when we have enough (>T) first scores
        y = self.__smooth(self.outliers)

        # Stage 2: Change Point Detection (SDAR #2)
        change = self.sdar_change.update(y, self.ys)
        self.changes = self.__append(self.changes, change, self.T2)

        self.ys = self.__append(self.ys, y, self.k)

        # Return outlier and change point scores
        return outlier, self.__smooth(self.changes)

    def __append(self, window, x, window_size):
        """Insert a sample x into a fix-sized window.

        Args:
            window (numpy array): Fixed sized window.
            x (float): A sample value.
            window_size (int): Maximum size of the window.

        Returns:
            numpy array: An updated window.

        """
        window = np.append(window, x)

        # delete oldest point
        if window.size > window_size:
            window = np.delete(window, 0)

        return window

    def __smooth(self, window):
        """Return a smoothed value of the current window.

        Args:
            window (numpy array): Fixed sized window.

        Returns:
            float: A smoothed value of the given window.

        """
        return np.mean(window)
