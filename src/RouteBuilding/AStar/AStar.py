import numpy as np
from shapely.geometry import LineString, Point
from tqdm import trange
from math import radians, cos, sin, sqrt, atan2, degrees

from .Node import Node
from .PriorityDictionary import PriorityDictionary


# Precompute Earth's radius in meters and degrees-to-radians conversion factor
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


def haversine_array(lon1_arr, lat1_arr, lon2_arr, lat2_arr):
    """
    Calculate the distance between pairs of points on the Earth's surface
    (specified in decimal degrees) using the Haversine formula.
    """
    lat1_rad = np.radians(lat1_arr)
    lon1_rad = np.radians(lon1_arr)
    lat2_rad = np.radians(lat2_arr)
    lon2_rad = np.radians(lon2_arr)

    dlat = lat2_rad[:, np.newaxis] - lat1_rad
    dlon = lon2_rad[:, np.newaxis] - lon1_rad

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2

    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c


def get_heading(lon1, lat1, lon2, lat2):
    """
    Calculate the heading (in degrees) from one point to another point given their latitudes and longitudes.
    """
    # convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # calculate the difference between the longitudes
    dlon = lon2 - lon1

    # calculate the heading
    y = sin(dlon) * cos(lat2)
    x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
    heading = atan2(y, x)

    # convert heading from radians to degrees
    heading = degrees(heading)

    # normalize to range [0, 360)
    if heading < 0:
        heading += 360

    return heading


def get_destination(lon, lat, distance, heading):
    lat1, lon1 = np.radians(lat), np.radians(lon)
    bearing = np.radians(heading)

    # Calculate the destination latitude using the haversine formula
    lat2 = np.arcsin(np.sin(lat1) * np.cos(distance / R) + np.cos(lat1) * np.sin(distance / R) * np.cos(bearing))

    # Calculate the destination longitude using the haversine formula
    lon2 = lon1 + np.arctan2(
        np.sin(bearing) * np.sin(distance / R) * np.cos(lat1), np.cos(distance / R) - np.sin(lat1) * np.sin(lat2)
    )

    return [np.degrees(lon2), np.degrees(lat2)]


def get_destinations(lon, lat, distance, headings):
    lat1, lon1 = np.radians(lat), np.radians(lon)
    bearings = np.radians(headings)

    # Calculate the destination latitudes using the haversine formula
    lat2 = np.arcsin(np.sin(lat1) * np.cos(distance / R) + np.cos(lat1) * np.sin(distance / R) * np.cos(bearings))

    # Calculate the destination longitudes using the haversine formula
    lon2 = lon1 + np.arctan2(
        np.sin(bearings) * np.sin(distance / R) * np.cos(lat1), np.cos(distance / R) - np.sin(lat1) * np.sin(lat2)
    )
    return np.vstack((np.degrees(lon2), np.degrees(lat2))).T


def get_arrival_bounds(min_speed, max_speed, dist, prev_times, offset):
    early = (dist / max_speed) + prev_times[0]
    late = (dist / min_speed) + prev_times[1]

    return (early + offset, late + offset)


class AStar:
    def __init__(self, bounds, nfzs, cruise_speed=20, offset=0):
        self.active = PriorityDictionary()
        self.closed = {}
        self.nfzs = nfzs
        self.bounds = bounds
        self.min_speed, self.max_speed = round(cruise_speed * 0.8, 2), round(cruise_speed * 1.2, 2)

        self.offset = offset

        self.distance_cache = {}

    def expand_point(self, start, direction: int = 0, radial: int = None, sep: int = 10, dist: float = 500.0):
        if radial is not None:
            semi_radial = radial // 2

            intervals = np.arange(direction - semi_radial, direction + semi_radial, sep)
        else:
            intervals = np.arange(direction - self.semi_radial, direction + self.semi_radial, sep)

        destinations = np.around(get_destinations(*start.pos, dist, intervals), decimals=3)

        for new_point in self.get_new_point(start, destinations):
            self.add_new_point(new_point)

    def get_new_point(self, start, destinations, accuracy: int = 2):
        for destination in destinations:
            # Validation prep
            new_point = tuple(destination)

            new_geom_point = Point(new_point)
            path_segment = LineString([Point(start.pos), new_point])

            # Validate point does not violate any constraint
            if not self.check_airspace_constraints(new_geom_point, path_segment):
                continue

            if new_point in self.active:
                heuristic = self.active[new_point].h
            elif new_point in self.closed:
                heuristic = self.closed[new_point].h
            else:
                heuristic = self.get_heuristic(new_point)

            to_point_dist = haversine(*start.pos, *new_point)

            N = Node(
                new_point,
                start,
                start.g + to_point_dist,
                heuristic,
                times=get_arrival_bounds(self.min_speed, self.max_speed, to_point_dist, start.times, self.offset),
            )

            if self.check_ov_constraints(N):
                yield N

    def add_new_point(self, new_point):
        if new_point.pos in self.closed:
            if new_point.g >= self.closed[new_point.pos].g:
                return self.closed[new_point.pos]
            del self.closed[new_point.pos]
        self.active[new_point.pos] = new_point
        return self.active[new_point.pos]

    def get_route(self, node):
        print(f"Length {round(node.g/1000,2)}km")

        route = [Point(node.pos)]
        while node.parent is not None:
            node = node.parent
            route.insert(0, Point(node.pos))
        return list(route)

    def find_path(
        self,
        start,
        goal,
        ovs=None,
        sep: int = 10,
        dist: float = 500.0,
        radial: int = 120,
        n_iter: int = 5000,
        break_on_found: bool = False,
        reduce_on_found: bool = True,
        return_route: bool = True,
        reduce_factor=0.3,
    ):
        import matplotlib.pyplot as plt
        print("TYPE OF BOUNDS:", type(self.bounds))  # should be Polygon

        plt.plot(*self.bounds.exterior.coords.xy)
        for nfz in self.nfzs:
            plt.plot(*nfz.exterior.coords.xy, c="red")
        plt.scatter(start[0], start[1], c="green")
        plt.scatter(goal[0], goal[1], c="blue")
        plt.show()

        # print(self.bounds, self.nfzs, start, goal)

        self.goal = goal
        self.ovs = ovs
        self.start = Node(start, None, g=0, h=self.get_heuristic(start), times=(0, 0))
        self.active[start] = self.start

        end_node = None

        self.semi_radial = radial // 2

        min_valid_g = float("inf")

        print("Searching for a valid route...")
        for i in trange(n_iter, colour="#3399ff", desc="A* Path finding"):
            # if i % 1000 == 0:
            #     plt.plot(*self.bounds.exterior.coords.xy)
            #     plt.scatter(*self.start.pos, c="green")
            #     plt.scatter(*self.goal, c="red")
            #     print(self.active.peekitem())

            #     for k, n__ in self.closed.items():
            #         plt.scatter(*k, c="black")
            #         if n__.parent is not None:
            #             plt.plot([k[0], n__.parent.pos[0]], [k[1], n__.parent.pos[1]], c="black")

            #     for nfz in self.nfzs:
            #         plt.plot(*nfz.exterior.coords.xy, c="red")
            #     plt.show()

            if len(self.active) <= 0:
                break

            active_node = self.active.popitem()
            # plt.scatter(*active_node.pos, c='blue')

            self.closed[active_node.pos] = active_node

            if active_node.f > min_valid_g:
                continue

            if active_node.pos == self.goal and break_on_found:
                break
            elif active_node.pos == self.goal and reduce_on_found:
                dist = dist * reduce_factor

            if active_node == self.start:
                self.expand_point(active_node, sep=sep, dist=dist, radial=360)
            else:
                heading = get_heading(*active_node.parent.pos, *active_node.pos)
                self.expand_point(active_node, direction=heading, radial=radial, sep=sep, dist=dist)

            if active_node.h <= dist:
                path_segment = LineString([active_node.pos, self.goal])

                if self.check_airspace_constraints(Point(self.goal), path_segment):
                    to_point_dist = haversine(*active_node.pos, *self.goal)
                    new_point = Node(
                        self.goal,
                        active_node,
                        g=active_node.g + to_point_dist,
                        h=0,
                        times=get_arrival_bounds(
                            self.min_speed, self.max_speed, to_point_dist, active_node.times, self.offset
                        ),
                    )

                    if not self.check_ov_constraints(new_point):
                        continue

                    if end_node is None:
                        print("\nValid path found!")
                    elif new_point.g > end_node.g:
                        continue
                    else:
                        print("\nBetter path found!")

                    end_node = self.add_new_point(new_point)

                    min_valid_g = end_node.g

        self.route = None

        if end_node:
            print("A path has been found!")
            self.route = self.get_route(end_node)
        else:
            print("Error no valid route found")

        return self.route if return_route else end_node

    def check_airspace_constraints(self, new_point, path_segment):
        if not self.bounds.contains(new_point):
            return False

        if any(nfz.contains(new_point) for nfz in self.nfzs):
            return False

        if any(path_segment.intersects(nfz) for nfz in self.nfzs):
            return False

        return min(path_segment.distance(nfz) for nfz in self.nfzs) >= 7.5e-4

    def check_ov_constraints(self, node):
        path = LineString([node.pos, node.parent.pos])
        point = Point(node.pos)

        times_0 = self.ovs.get_ovs_by_time(node.times[0])
        times_1 = self.ovs.get_ovs_by_time(node.times[1])

        if times_0 is None and times_1 is None:
            return True
        elif times_0 is None:
            near_ovs = times_1
        elif times_1 is None:
            near_ovs = times_0
        else:
            near_ovs = times_0.union(times_1)

        return not any(
            (
                node.times[0] <= ov.e_time
                and node.times[1] >= ov.s_time
                and (ov.ov.contains(point) or path.intersects(ov.ov))
            )
            for ov in near_ovs
        )

    def get_heuristic(self, start, _min=1000):
        # return 1.1*haversine(*start, *self.goal)
        goal_heading = get_heading(*start, *self.goal)
        direct_path = LineString((start, self.goal))

        nfz_heuristics = [None] * len(self.nfzs)

        for i, nfz in enumerate(self.nfzs):
            if direct_path.intersects(nfz):

                less = (None, None, None)
                more = (None, None, None)
                for point in np.array(nfz.exterior.coords.xy).T:

                    if (point[0], point[1]) in self.distance_cache:
                        d = self.distance_cache[(point[0], point[1])]
                    else:
                        d = haversine(*start, *point)
                        self.distance_cache[(point[0], point[1])] = d

                    if d > _min:
                        continue

                    h = get_heading(*start, *point) - goal_heading

                    if h <= goal_heading and (less[0] is None or h < less[0]):
                        less = (h, d, point)
                    elif h > goal_heading and (more[0] is None or h > more[0]):
                        more = (h, d, point)

                if less[0] is None:
                    nfz_heuristics[i] = more
                elif more[0] is None:
                    nfz_heuristics[i] = less
                else:
                    nfz_heuristics[i] = less if abs(less[0]) <= abs(more[0]) else more

        closest_i = -1

        for i in range(len(nfz_heuristics)):
            if nfz_heuristics[i] is None or nfz_heuristics[i][1] is None:
                continue

            try:
                if closest_i == -1:
                    closest_i = i
                elif nfz_heuristics[i][1] < nfz_heuristics[closest_i][1]:
                    closest_i = i
            except Exception:
                print(i, nfz_heuristics[i][1], nfz_heuristics[closest_i][1])
                raise Exception()

        m = 1.0

        if closest_i == -1:
            return m * haversine(*start, *self.goal)

        # return 1.3*(haversine(*nfz_heuristics[closest_i][2], *self.goal) + nfz_heuristics[closest_i][1])
        return m * (haversine(*nfz_heuristics[closest_i][2], *self.goal) + nfz_heuristics[closest_i][1])
