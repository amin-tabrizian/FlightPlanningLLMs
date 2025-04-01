import matplotlib.pyplot as plt
import numpy as np
import shapely.geometry as geom
from matplotlib.patches import Polygon
from shapely.ops import cascaded_union

from src.OVGeneration.classes import OV


def displayAirspace(airspace: dict, vis: bool = True):
    coords = np.array(list(map(list, zip(*airspace["airspace"].exterior.coords.xy))))
    plt.plot(coords[:, 0], coords[:, 1], c=(0, 0.5, 0))
    # p = Polygon(coords, alpha=0.1, color=(0, 0.75, 0))
    # plt.gca().add_patch(p)

    for nfz in airspace["nfzs"].values():
        coords = list(map(list, zip(*nfz.exterior.coords.xy)))
        p = Polygon(coords, alpha=0.5, color="gray")
        plt.gca().add_patch(p)

    for point in airspace["points"]:
        plt.scatter(point.x, point.y, c="blue", s=10, marker="+")

    if vis:
        plt.autoscale()
        plt.show()


def displayRoute(route, c="magenta", s=5):
    if route == []:
        return

    try:
        list_route = np.array([[point.x, point.y] for point in route])
    except Exception:
        list_route = route

    plt.plot(list_route[:, 0], list_route[:, 1], c=c)

    for i, point in enumerate(list_route):
        if i == 0:
            plt.scatter(point[0], point[1], c="green", s=s)
        elif i == len(list_route) - 1:
            plt.scatter(point[0], point[1], c="orange", s=s)
        else:
            plt.scatter(point[0], point[1], c="black", s=s)


def displayRouteAirspace(airspace: dict, route, optimised_route, start, end, ovs):
    coords = np.array(list(map(list, zip(*airspace["airspace"].exterior.coords.xy))))
    plt.plot(coords[:, 0], coords[:, 1], c=(0, 0.5, 0))

    # p = Polygon(coords, alpha=0.1, color=(0, 0.75, 0))
    # plt.gca().add_patch(p)

    if ovs is not None:
        for ov in ovs.get_all_ov_polys():
            plt.plot(*ov.exterior.coords.xy, c="red")

    for nfz in airspace["nfzs"].values():
        coords = list(map(list, zip(*nfz.exterior.coords.xy)))
        p = Polygon(coords, alpha=0.75, color="gray")
        plt.gca().add_patch(p)

    for point in airspace["points"]:
        plt.scatter(point.x, point.y, c="blue", s=3)

    plt.autoscale()

    displayRoute(route, s=3, c="black")
    displayRoute(optimised_route)

    plt.scatter(start.x, start.y, c="green")
    plt.scatter(end.x, end.y, c="orange")

    plt.xlabel("Longitude")
    plt.ylabel("Latitude")

    plt.show()


def drawDryvrOVs(airspace: dict, operational_volumes: np.ndarray, route, traces):
    displayAirspace(airspace, False)
    displayRoute(route)

    boundaries = []

    for ov in operational_volumes:
        ov_poly = []
        for ov_section in ov:
            _min = ov_section[0, 1:3]
            _max = ov_section[1, 1:3]

            ov_poly.append(
                geom.Polygon([(_min[0], _min[1]), (_min[0], _max[1]), (_max[0], _max[1]), (_max[0], _min[1])])
            )

        boundaries.append(np.array(list(map(list, zip(*cascaded_union(ov_poly).exterior.xy)))))

    for boundary in boundaries:
        p = Polygon(boundary, alpha=0.75, color=np.random.uniform(0, 1, 3))
        plt.gca().add_patch(p)

    plt.autoscale()
    plt.show()


def drawArrayOVs(airspace: dict, operational_volumes: np.ndarray, route, traces, draw_airspace=True, show=True):

    if draw_airspace:
        displayAirspace(airspace, False)

    c = ["cyan", "blue"]
    length = 0

    for ov in operational_volumes:
        if isinstance(ov, OV):
            ov = ov.shape

        p = Polygon(ov, alpha=0.75, color=c[length])
        plt.gca().add_patch(p)

        length = (length + length) % 2

    displayRoute(route, s=3, c="black")

    plt.xlabel("Longitude")
    plt.ylabel("Latitude")

    # plt.axis('off')

    if show:
        plt.autoscale()
        plt.show()
