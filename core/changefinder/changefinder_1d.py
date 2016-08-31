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
            float: Latest PDF for the given series.

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

        # compute and return the value of probability density function
        if self.sigma == 0.0:
            return 0.0

        numerator = np.exp(-0.5 * (x - x_hat) ** 2 / self.sigma)
        denominator = (2 * np.pi) ** 0.5 * (self.sigma) ** 0.5
        return numerator / denominator


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
        self.sdar_change = SDAR_1D(r / 2, k)

    def update(self, x):
        """Update AR models based on 1d input x.

        Args:
            x (float): 1d input value.

        Returns:
            (float, float): (Outlier score, Change point score).

        """

        # Stage 1: Outlier Detection (SDAR #1)
        prev_mu, prev_sigma = self.sdar_outlier.mu, self.sdar_outlier.sigma
        self.sdar_outlier.update(x, self.xs)

        # compute outlier score
        # outlier = self.__logloss(p)
        outlier = self.__hellinger(prev_mu, prev_sigma,
                                   self.sdar_outlier.mu, self.sdar_outlier.sigma)
        self.outliers = self.__append(self.outliers, outlier, self.T1)

        self.xs = self.__append(self.xs, x, self.k)

        # Smoothing when we have enough (>T) first scores
        y = self.__smooth(self.outliers)

        # Stage 2: Change Point Detection (SDAR #2)
        prev_mu, prev_sigma = self.sdar_change.mu, self.sdar_change.sigma
        self.sdar_change.update(y, self.ys)

        # compute change score
        # change = self.__logloss(p)
        change = self.__hellinger(prev_mu, prev_sigma,
                                  self.sdar_change.mu, self.sdar_change.sigma)
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

    def __logloss(self, p):
        """Return LogLoss for a given PDF p.

        Args:
            p (float): PDF.

        Returns:
            float: LogLoss for p.

        """
        if p == 0.0:
            return 0.0

        return -np.log(p)

    def __hellinger(self, mu1, sigma1, mu2, sigma2):
        """Return the Hellinger distance bwtween two PDFs p1 and p2.

        PDF of AR model follows very similar distribution of the multivariate normal distributions.
        - [normal distrubiton] `sigma` indicates std. deviation, and `sigma ** 2` is variance.
        - [multivariate normal distribution] `sigma` itself is variance because
            it corresponds to a 1x1 covarriance matrix in a context of the AR model.

        Args:
            mu1 (float): Mean before update the model.
            sigma1 (float): Variance before update the model.
            mu2 (float): Mean before after the model.
            sigma2 (float): Variance after update the model.

        Returns:
            float: The Hellinger distance between the models {before, after} update.

        """
        if sigma1 + sigma2 == 0:
            return 0

        return 1 - sigma1 ** 0.25 * sigma2 ** 0.25 * np.exp(-0.25 * (mu1 - mu2) ** 2 / (sigma1 + sigma2)) / (((sigma1 + sigma2) / 2) ** 0.5)
