import numpy as np

from .utils import aryule_levinson

from logging import getLogger
logger = getLogger('ChangeFinder')


class AR_1D:

    def __init__(self, k):
        """AR(k): k-th order AR model.
        cf. https://www.computer.org/cms/dl/trans/tk/2006/04/extras/k0482s.pdf

        Args:
            k (int): Order of the AR model.

        """

        self.k = k

        # initialize the parameters
        self.mu = self.sigma = 0.0
        self.c = np.zeros(self.k + 1)

    def estimate(self, x):
        """Estimate the parameters of the AR model.
        Estimation is done by a batch algorithm for the given t data points.
        That is, the algorithm assumes that the data source is stationary.

        Args:
            x (numpy array): all t data points (1, ..., t).

        """
        t = x.size

        # estimate mu
        self.mu = 0
        for i in range(self.k, t):
            self.mu += x[i]
        self.mu /= (t - self.k)

        # create c (coefficients of the Yule-Walker equation)
        self.c = np.zeros(self.k + 1)
        for j in range(self.k + 1):
            for i in range(self.k, t):
                self.c[j] += ((x[i] - self.mu) * (x[i - j] - self.mu))
            self.c[j] /= (t - self.k)

        # solve the Yule-Walker equation
        a = aryule_levinson(self.c, self.k)

        # estimate sigma
        self.sigma = self.c[0]
        for i in range(self.k):
            self.sigma -= (a[i] * self.c[i + 1])


class ModelSelection:

    def __init__(self, max_k=50):
        """Model selection of the AR model.

        Args:
            max_k (int): Max number of possible k for the AR(k) model.

        """
        self.max_k = max_k

    def select(self, x):
        """For the given data points, select the best model based on AIC.

        Args:
            x (numpy array): all t data points (1, ..., t).

        """
        selected_k = 1
        min_aic = np.inf

        for k in range(1, min(x.size, self.max_k + 1)):
            ar = AR_1D(k)
            ar.estimate(x)

            # sigma could be negative/zero
            v = max(2 * np.pi * ar.sigma, 1e-100)
            aic = x.size * (np.log(v) + 1) + 2 * (k + 1)

            if aic < min_aic:
                selected_k = k
                min_aic = aic

        return selected_k, min_aic
