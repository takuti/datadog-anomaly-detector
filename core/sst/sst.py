import numpy as np
import numpy.linalg as ln


class SingularSpectrumTransformation:

    def __init__(self, w, r):
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
