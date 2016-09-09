import numpy as np
import numpy.linalg as ln


class SingularSpectrumTransformation:

    def __init__(self, w, r=3):
        """Change-point detection based on Singular Spectrum Transformation (SST),

        Args:
            w (int): Window size.
            r (int): Number of singular vectors spanning past/current subspaces.

        """
        self.w = w
        self.r = r

        # number of columns for the trajectory matrices:
        # usually set to `w`
        self.n = self.m = w

        # starting point of the test interval:
        # equal to a point `t` where we want to know a change-point score
        self.g = -w

        self.n_past = w + self.n  # = 2 * w
        self.n_current = w + self.m

        q = np.random.normal(size=self.m)
        self.q = q / ln.norm(q)

    def score(self, xs_past, xs_current):
        """Compute a change-point score for given past/current patterns.

        Args:
            xs_past (numpy array): Array of points for the `past` widows.
            xs_current (numpy array): Array of points for the `current` windows.

            The past/current points are stored as:
                old <--> new:
                t-(n+w), ..., t-n, ..., t-w, ..., t-1

            [Sample code snippet]
            | sst = SingularSpectrumTransformation(30, 2)
            |
            | for t in range(sst.n_past + 1, xs.size - sst.g - sst.n_current):
            |     xs_past = xs[(t - sst.n_past - 1):(t - 1)]
            |     xs_current = xs[(t + sst.g):(t + sst.g + sst.n_current)]
            |     yield sst.score(xs_past, xs_current)

        Returns:
            float: Change-point score based on SST.

        """
        assert xs_past.size == self.n_past, 'lack of past samples'
        assert xs_current.size == self.n_current, 'lack of current samples'

        # Create past trajectory matrix and find its left singular vectors
        H = np.zeros((self.w, self.n))
        for i in range(self.n):
            H[:, i] = xs_past[i:(i + self.w)]
        U, _, _ = ln.svd(H, full_matrices=False)

        # Create current trajectory matrix and find its left singular vectors
        G = np.zeros((self.w, self.m))
        for i in range(self.m):
            G[:, i] = xs_current[i:(i + self.w)]
        Q, _, _ = ln.svd(G, full_matrices=False)

        # find the largest singular value for `r` principal component
        s = ln.svd(np.dot(U[:, :self.r].T, Q[:, :self.r]),
                   full_matrices=False, compute_uv=False)

        return 1 - s[0]

    def score_lanczos(self, xs_past, xs_current):
        assert xs_past.size == self.n_past, 'lack of past samples'
        assert xs_current.size == self.n_current, 'lack of current samples'

        # Create past trajectory matrix and find its left singular vectors
        H = np.zeros((self.w, self.n))
        for i in range(self.n):
            H[:, i] = xs_past[i:(i + self.w)]

        # Create current trajectory matrix and find its left singular vectors
        G = np.zeros((self.w, self.m))
        for i in range(self.m):
            G[:, i] = xs_current[i:(i + self.w)]

        # Power method
        GG = np.dot(G.T, G)
        for i in range(1):  # fixed number of iteration may lead failure depending on r
            self.q = np.dot(GG, self.q)
        v = self.q / ln.norm(self.q)
        Gv = np.dot(G, v)
        self.q = Gv / ln.norm(Gv)  # assuming m = w

        k = 2 * self.r if self.r % 2 == 0 else 2 * self.r - 1
        T = self.lanczos(np.dot(H, H.T), self.q, k)
        eigvals, eigvecs = ln.eig(T)

        # `eig()` returns unordered eigenvalues,
        # so the top-r eigenvectors should be picked carefully
        return 1 - np.sqrt(np.sum(eigvecs[0, np.argsort(eigvals)[::-1][:self.r]] ** 2))

    def lanczos(self, C, a, s):
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
