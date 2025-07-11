"""This package holds the code for running RRT*-FN based path planning
"""

# Imports
from time import perf_counter
import numpy as np
import tqdm
from shapely.geometry import LineString, Point
from src.functions.GeoFunctions import routeToLL
from .Graph import Graph
from math import sin, cos, atan2, sqrt

R = 6371e3
DEG_TO_RAD = np.pi / 180.0


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the distance between two points
    on the earth (specified in decimal degrees)
    """
    phi1, phi2 = lat1 * DEG_TO_RAD, lat2 * DEG_TO_RAD
    dphi = (lat2 - lat1) * DEG_TO_RAD
    dlambda = (lon2 - lon1) * DEG_TO_RAD
    a = sin(dphi / 2.0) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2.0) ** 2
    c = 2.0 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


class RRTStar:
    def __init__(
        self,
        start,
        goal,
        airspace,
        M: int = None,
        n_iter: int = 3000,
        step_size: float = 50,
        end_dist: float = 100.0,
        orig=None,
    ):
        self.graph = Graph(Point(start), Point(goal), airspace, min_step=step_size, min_end_dist=end_dist)

        self.airspace = airspace
        self.orig = orig
        self.n_iter = n_iter
        self.route = []
        self.M = M if M is not None else n_iter

    def step(self) -> bool:
        self.graph.step()

        if len(self.graph.vertices) > self.M:
            self.graph.repairLength()

        return self.graph.success

    def findPath(self):
        print("Finding Shortest Path...")
        print("Settings".center(20, "+"))

        print(f"M:{self.M}\nstep_size:{self.graph.min_step}")
        print("+".center(20, "+"))

        start = perf_counter()

        for _ in tqdm.trange(self.n_iter):
            if self.step():
                break

        self.route = self.graph.getRoute()
        self.optimised_route = self.graph.shortenRoute()

        _route = np.array([[p.x, p.y] for p in routeToLL(self.orig, self.route)])
        _optimised_route = np.array([[p.x, p.y] for p in routeToLL(self.orig, self.optimised_route)])

        optimised_d = 0

        for i in range(len(_optimised_route) - 1):
            h = haversine(
                _optimised_route[i, 0], _optimised_route[i, 1], _optimised_route[i + 1, 0], _optimised_route[i + 1, 1]
            )
            optimised_d += h

        r_d = 0

        for i in range(len(_route) - 1):
            h = haversine(_route[i, 0], _route[i, 1], _route[i + 1, 0], _route[i + 1, 1])
            r_d += h

        print(f"Candidate Route Found in {round(perf_counter()-start,2)}seconds!")

        print("Route Details".center(20, "="))

        print(f"Route Length: {round(LineString(self.route).length/1000, 2)}km")
        print(f"Nodes in Route: {len(self.route)}")
        print(f"Optimised Route Length: {round(optimised_d/1000,2)}km")
        print(f"Nodes in Optimised Route: {len(self.optimised_route)}")
        print("=".center(20, "="))

    def printRoute(self):
        print(self.route)

    def saveRoutes(self, path, airspace):
        print("Saving Routes")
        _route = np.array([[p.x, p.y] for p in self.route])
        _optimised_route = np.array([[p.x, p.y] for p in self.optimised_route])

        np.save(f"{path}-XYZ-route.npy", _route)
        np.save(f"{path}-XYZ-optimised_route.npy", _optimised_route)

        _route = np.array([[p.x, p.y] for p in routeToLL(airspace, self.route)])
        _optimised_route = np.array([[p.x, p.y] for p in routeToLL(airspace, self.optimised_route)])

        print(_optimised_route)

        print(_optimised_route)

        np.save(f"{path}-LLA-route.npy", _route)
        np.save(f"{path}-LLA-optimised_route.npy", _optimised_route)

        print("Routes Saved")
        print(f"\t--> {path}-route.npy")
        print(f"\t--> {path}-optimised_route.npy")
        print(f"\t--> {path}-LLA-route.npy")
        print(f"\t--> {path}-XYZ-optimised_route.npy")

        return _route, _optimised_route
