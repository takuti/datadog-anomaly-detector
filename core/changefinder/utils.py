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

    """
    a = np.zeros(k)

    # ignore a singular matrix
    C = toeplitz(c[:k])
    if not np.all(C == 0.0) and np.isfinite(ln.cond(C)):
        a = np.dot(ln.inv(C), c[1:])

    return a


def aryule_levinson(c, k):
    """MATLAB implementation of Levinson-Durbin recursion.

    cf. https://searchcode.com/file/64213289/inst/levinson.m

    """
    if c[0] == 0:
        return np.zeros(k)

    # recursively solve the Yule-Walker equation
    g = -c[1] / c[0]
    a = np.array([g])
    v = c[0] * (1 - g * g)

    for t in range(1, k):
        g = 0 if v == 0 else -(c[t + 1] + np.dot(a, c[1:(t + 1)][::-1])) / v
        a = np.append(a + g * a[:t][::-1], g)
        v = v * (1 - np.dot(g, g))

    return -a


def arburg(x, k):
    """MATLAB implementation of the Burg's method.

    cf. https://searchcode.com/codesearch/view/9503568/

    """

    def sumsq(x):
        return np.sum(x * x)

    n = x.size
    # v = sumsq(x)

    # f and b are the forward and backward error sequences
    f = x[1:n]
    b = x[:(n - 1)]

    a = np.array([])

    # remaining stages i=2 to p
    for i in range(k):

        # get the i-th reflection coefficient
        denominator = sumsq(f) + sumsq(b)
        g = 0 if denominator == 0 else 2 * np.sum(f * b) / denominator

        # generate next filter order
        if i == 0:
            a = np.array([g])
        else:
            a = np.append(g, a - g * a[:(i)][::-1])

        # keep track of the error
        # v = v * (1 - g * g)

        # update the prediction error sequences
        old_f = np.empty_like(f)
        old_f[:] = f
        f = old_f[1:(n - i - 1)] - g * b[1:(n - i - 1)]
        b = b[:(n - i - 2)] - g * old_f[:(n - i - 2)]

    return -a[:k][::-1]
