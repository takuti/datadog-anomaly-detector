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
    a = np.zeros(k)
    a[0] = g
    v = c[0] * (1 - g * g)

    for t in range(1, k):
        if v == 0:
            continue

        g = -c[t + 1]
        for j in range(t):
            g -= (a[j] * c[t - j])
        g /= v

        a_ = np.zeros(t)
        for j in range(t):
            a_[j] = a[t - 1 - j]

        for j in range(t):
            a[j] += (g * a_[j])
        a[t] = g

        v *= (1 - g * g)

    a_ = np.zeros(k)
    for i in range(k):
        a_[i] = -a[i]

    return a_


def arburg(x, k):
    """MATLAB implementation of the Burg's method.

    cf. https://searchcode.com/codesearch/view/9503568/

    """
    n = x.size
    # v = sumsq(x)

    # f and b are the forward and backward error sequences
    current_errseq_size = n - 1
    f = np.zeros(current_errseq_size)  # x[1:n]
    b = np.zeros(current_errseq_size)  # x[:(n - 1)]
    for i in range(current_errseq_size):
        f[i] = x[i + 1]
        b[i] = x[i]

    a = np.zeros(k)

    # remaining stages i=2 to p
    for i in range(k):

        # get the i-th reflection coefficient
        numerator = denominator = 0
        for j in range(current_errseq_size):
            numerator += (f[j] * b[j])
            denominator += (f[j] * f[j] + b[j] * b[j])
        numerator *= 2

        g = 0 if denominator == 0 else numerator / denominator

        # generate next filter order
        a_ = np.array([a[j] for j in range(i)])
        a[0] = g
        for j in range(i):
            a[j + 1] = a_[j] - g * a_[i - 1 - j]

        # keep track of the error
        # v = v * (1 - g * g)

        # update the prediction error sequences
        f_ = np.array([fi for fi in f])
        next_errseq_size = n - i - 2
        for j in range(next_errseq_size):
            f[j] = f_[j + 1] - g * b[j + 1]
            b[j] = b[j] - g * f_[j]

        current_errseq_size = next_errseq_size

    return np.array([-a[k - 1 - i] for i in range(k)])
