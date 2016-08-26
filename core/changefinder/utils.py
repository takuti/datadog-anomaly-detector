import numpy as np
import numpy.linalg as ln
from scipy.linalg import toeplitz


def aryule(c, k):
    """Solve Yule-Walker equation.

    Args:
        c (numpy array): Coefficients (i.e. autocorrelation)
        k (int): Assuming the AR(k) model

    Returns:
        numpy array: k model parameters
            Some formulations solve: C a = -c,
            but we actually solve C a = c.

    TODO: Must be tested here
    # recursively solve the Yule-Walker equation
    if self.c[0] != 0:
        for i in range(self.k):
            a[i] = self.c[i + 1]

            for j in range(i):
                a[i] -= (a[j] * self.c[i - j])

            a[i] /= self.c[0]

    """
    C = toeplitz(c[:k])
    return np.dot(ln.inv(C), c[1:])
