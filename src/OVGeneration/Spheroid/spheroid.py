"""This generates OVs for a given set of traces
"""

# Imports
import numpy as np
from matplotlib.patches import Ellipse
from shapely.ops import unary_union
from shapely.geometry import Polygon, Point
import shapely
from tqdm import trange


# Dunders
__author__ = "Ellis Thompson"


def spheroidConcurr(*args):
    args = args[0]
    return spheroidMain(args[0], args[1])


def spheroidMain(
    traces: np.ndarray,
    n_traces: int = 20,
):
    if traces.shape[0] < 15:
        raise ValueError("The system requires a minimum of 15 traces")

    if 15 <= traces.shape[0] < n_traces:
        print(
            f"[WARNING]: Running the generation with {traces.shape[0]} which is above the"
            + f" minimum 15 but less than specified {n_traces} traces!"
        )

    if traces.shape[0] <= n_traces:
        training_traces = traces
    else:
        idxs = np.random.choice(traces.shape[0], n_traces, replace=False)
        training_traces = traces[idxs]

    training_traces = training_traces[:, :, 1:3]

    center = (training_traces.max(axis=0) + training_traces.min(axis=0)) / 2

    training_traces = np.append([center], training_traces, axis=0)

    return spheroidRun(training_traces)


def spheroidRun(traces):
    polys = []

    for i in trange(traces.shape[1], desc="Building OV"):
        points = traces[:, i, :]
        center = np.mean(points, axis=0)
        cov = np.cov(points.T)
        eigenvals, eigenvecs = np.linalg.eig(cov)
        width, height = 2 * np.sqrt(eigenvals)
        angle = np.degrees(np.arctan2(*eigenvecs[:, 0][::-1]))

        # Create the ellipse object
        ellipse = Ellipse(xy=center, width=width, height=height, angle=angle, fill=False)

        # Extract the vertices of the ellipse
        ellipse = (center, width, height, angle) = (
            ellipse.get_center(),
            ellipse.get_width(),
            ellipse.get_height(),
            ellipse.get_angle(),
        )

        circ = Point(ellipse[0]).buffer(1)
        ell = shapely.affinity.scale(circ, ellipse[2], ellipse[1])
        elrv = shapely.affinity.rotate(ell, 90 + ellipse[3])

        coords = np.array(list(zip(*elrv.exterior.xy)))
        # polys
        polys.append(Polygon(coords))

        boundary = unary_union(polys).simplify(1e-5)

        total, _in = 0, 0

    for ac in traces:
        for t in ac:
            total += 1
            p = Point([t[0], t[1]])
            if boundary.contains(p):
                _in += 1

    assert _in / total >= 0.8

    return np.array(list(zip(*boundary.exterior.xy)))
