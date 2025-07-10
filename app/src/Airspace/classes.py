import numpy as np
from matplotlib.patches import Ellipse
from shapely import Polygon
from shapely.ops import unary_union


class Segment:
    def __init__(self, mu, cov, z):
        self.mu = mu
        self.cov = cov
        self.z = z

    @property
    def shape(self):
        eigenvals, eigenvecs = np.linalg.eigh(self.cov)

        idx = eigenvals.argsort()[::-1]
        eigenvals = eigenvals[idx]
        eigenvecs = eigenvecs[:, idx]

        theta = np.degrees(np.arctan2(*eigenvecs[:, 0][::-1]))

        width = 2 * np.sqrt(eigenvals[0]) * self.z
        height = 2 * np.sqrt(eigenvals[1]) * self.z

        points = Ellipse(xy=self.mu, width=width, height=height, angle=theta, fill=False, linewidth=2).get_verts()

        return Polygon(points)

    def as_array(self):
        out = self.cov.flatten()
        out = np.append(out, self.mu)
        out = np.append(out, self.z)
        return out


class OV:
    def __init__(self):
        self.segments = []

    def __len__(self):
        return len(self.segments)

    def as_numpy(self):
        out = np.zeros((len(self), 7))

        for i, seg in enumerate(self.segments):
            out[i, :] = seg.as_array()

        return out

    def insert(self, segment):
        self.segments.append(segment)

    @property
    def shape(self):
        polys = [seg.shape for seg in self.segments]
        boundary = unary_union(polys).simplify(1e-5)

        return np.array(list(zip(*boundary.exterior.xy)))
