import numpy as np
from shapely.geometry import Polygon
from matplotlib.patches import Ellipse
from shapely.ops import unary_union

MIN_START = 30
MAX_START = 80


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


class classOV:
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


class OV:
    def __init__(self, s_time, duration, ov):
        self.s_time = s_time
        self.duration = duration
        self.e_time = s_time + duration
        self.ov = Polygon(ov)


class Airspace:
    def __init__(self, bounds, bracket_size: int = 30):
        self.airspace = {}
        self.bracket_size = bracket_size
        self.total_ovs = 0
        self.bounds = np.asarray(list(zip(*bounds.exterior.coords.xy)))

    def load_airspace(self, paths, times, duration=60):
        print(f"There are {len(paths)} existing contracts")

        for i, path in enumerate(paths):
            ovs = np.load(path, allow_pickle=True)

            for ov in ovs:
                ov_class = classOV()
                for seg in ov:
                    cov = seg[:4].reshape(2, 2)
                    mu = seg[4:6]
                    z = seg[6]

                    ov_class.insert(Segment(mu, cov, z))

                s_time = times[i]
                self.add_ov(s_time, duration, OV(s_time, duration, ov_class.shape))

    def time_index(self, time):
        return time // self.bracket_size

    def get_ovs(self, bracket):
        return set(bracket) if (bracket := self.airspace.get(bracket)) else None

    def get_ovs_by_time(self, time):
        return self.get_ovs(self.time_index(time))

    def add_ov(self, start_time, duration, ov):
        self.total_ovs += 1
        start_index = self.time_index(start_time)
        end_index = self.time_index(start_time + duration)

        for idx in range(start_index, end_index + 1):
            if idx not in self.airspace:
                self.airspace[idx] = [ov]
            else:
                self.airspace[idx].append(ov)

    def add_contract(self, contract, start_time, ov_duration=60):
        for ov in contract:
            ov = OV(start_time, ov_duration, ov.shape)
            self.add_ov(start_time, ov_duration, ov)
            start_time += ov_duration

    def print(self):
        for _id, val in self.airspace.items():
            print(_id, ((_id * 120), (_id * 120) + 119), len(val), [(ov.s_time, ov.e_time) for ov in val])
        print(f"Total OVs:{self.total_ovs}")

    def get_all_ovs(self):
        ovs = set()

        for ov_list in self.airspace.values():
            for ov in ov_list:
                ovs.add(ov)

        return ovs

    def get_all_ov_polys(self):
        ovs = self.get_all_ovs()

        return [ov.ov for ov in ovs]


# A = Airspace()
# A.load_airspace(['out\\15-03-2023 11-47-28-Route (7-9)\\Operational Volumes.npy',
#                  'out\\15-03-2023 11-49-39-Route (9-6)\\Operational Volumes.npy',
#                  'out\\15-03-2023 11-55-33-Route (8-7)\\Operational Volumes.npy',
#                  'out\\15-03-2023 11-57-13-Route (8-1)\\Operational Volumes.npy',
#                  'out\\15-03-2023 11-58-58-Route (0-2)\\Operational Volumes.npy'])
# A.print()

# B = A.get_ovs(2)
# C = A.get_ovs(3)

# print(len(B), len(C))
# D = B.union(C)
# print(len(D))
