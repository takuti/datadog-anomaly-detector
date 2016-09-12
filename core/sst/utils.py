import numpy as np
import numpy.linalg as ln


def lanczos(C, a, s):
    """Lanczos method: tridiagonalize a symmetric matrix C to s * s matrix T.

    Args:
        C (numpy array): Target matrix applied tridiagonalization.
        a (numpy array): Initial vector (r).
        s (int): Size of the returned tridiagonal matrix T.

    Returns:
        (numpy array): s * s tridiagonal matrix.

    """
    a0 = np.zeros_like(a)
    beta0 = 1
    r = np.empty_like(a)
    r[:] = a

    T = np.zeros((s, s))

    for j in range(s):
        a1 = r / beta0
        Ca1 = np.dot(C, a1)
        alpha1 = np.dot(a1, Ca1)
        r = Ca1 - alpha1 * a1 - beta0 * a0
        beta1 = ln.norm(r)

        T[j, j] = alpha1
        if j - 1 >= 0:
            T[j, j - 1] = beta0
        if j + 1 < s:
            T[j, j + 1] = beta1

        a0[:] = a1
        beta0 = beta1

    return T


def is_diag(A, tol):
    """Check whether A is a diagonal matrix.

    Args:
        A (numpy array): Target matrix.
        tol (float): `A` is diagonal if all off-diagonal elements are less than `tol`.

    Returns:
        boolean

    """
    return np.all((A - np.diag(np.diag(A)) < tol))


def tridiag_eig(T, n_iter=1, tol=1e-3):
    """Find eigenvalues and eigenvectors of given symmetric (tridiagonal) matrix T.

    http://web.csulb.edu/~tgao/math423/s94.pdf
    http://stats.stackexchange.com/questions/20643/finding-matrix-eigenvectors-using-qr-decomposition

    Args:
        T (numpy array): Target tridiagonal matrix.
        n_iter (int): Repeat QR decomposition `n_iter` times.
        tol (float): Stop iteration if the target matrix converges to a diagonal matrix with acceptable tolerance `tol`.

    Returns:
        (numpy array) Estimated eigenvalues of T.
        (numpy array) Estimated eigenvectors of T.

    """
    eigvecs = np.identity(T.shape[0])

    for i in range(n_iter):
        Q, R = tridiag_qr(T)
        T = np.dot(R, Q)
        eigvecs = np.dot(eigvecs, Q)

        if is_diag(T, tol):
            break

    return np.diag(T), eigvecs


def householder(x):
    """Householder projection for a vector x.

    https://en.wikipedia.org/wiki/Householder_transformation

    """
    x[0] = x[0] + np.sign(x[0]) * ln.norm(x)
    x /= ln.norm(x)
    return x


def tridiag_qr(T):
    """QR decomposition for a tridiagonal matrix T.

    https://gist.github.com/lightcatcher/8118181
    http://www.ericmart.in/blog/optimizing_julia_tridiag_qr

    """
    R = np.empty_like(T)
    R[:] = T
    Qt = np.eye(T.shape[0])

    for i in range(T.shape[0] - 1):
        u = householder(T[i:i + 2, i])

        R[i:i + 2, :] = R[i:i + 2, :] - 2 * np.outer(u, np.dot(u, R[i:i + 2, :]))
        Qt[i:i + 2, :] = Qt[i:i + 2, :] - 2 * np.outer(u, np.dot(u, Qt[i:i + 2, :]))

    return Qt.T, R


def power1(A, x0, n_iter=1):
    """Find the first singular vectors/value of a matrix A based on the Power method.

    http://www.cs.yale.edu/homes/el327/datamining2013aFiles/07_singular_value_decomposition.pdf

    Args:
        A (numpy array): Target matrix.
        x0 (numpy array): Initial vector.
        n_iter (int): Number of iterations.
            - too small values may lead failure
            - lager values are time-consuming

    Returns:
        (numpy array): 1st left singular vector of A.
        (float): 1st singular value of A.
        (numpy array): 1st right singular vector of A.

    """
    AtA = np.dot(A.T, A)

    for i in range(n_iter):
        x0 = np.dot(AtA, x0)

    v = x0 / ln.norm(x0)
    Av = np.dot(A, v)
    s = ln.norm(Av)
    u = Av / s

    return u, s, v
