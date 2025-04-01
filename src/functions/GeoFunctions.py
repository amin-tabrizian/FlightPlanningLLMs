import pymap3d as pm
from pymap3d import enu2geodetic, geodetic2enu
from shapely import Polygon, Point


def polyToList(polygon):
    return list(
        map(
            list,
            zip(
                polygon.exterior.coords.xy[0],
                polygon.exterior.coords.xy[1],
            ),
        )
    )


def polyToXY(polygon, reference):
    print(polygon, reference)

    ell = pm.Ellipsoid(6378137, 6356752.314245)
    # ell = pm.Ellipsoid("wgs84")
    return Polygon(
        [
            list(
                geodetic2enu(
                    *point,
                    0,
                    *reference,
                    ell=ell,
                    deg=True,
                )
            )[:2]
            for point in polyToList(polygon)
        ]
    )


def getAirspaceRef(airspace):
    lat0 = (airspace["airspace"].bounds[0] + airspace["airspace"].bounds[2]) / 2
    lon0 = (airspace["airspace"].bounds[1] + airspace["airspace"].bounds[3]) / 2

    return [lat0, lon0, 0]


def airspaceToXY(airspace: dict):
    reference = getAirspaceRef(airspace)

    new_airspace = {
        "airspace": polyToXY(airspace["airspace"], reference),
        "nfzs": {},
        "points": [],
    }

    for key, val in airspace["nfzs"].items():
        new_airspace["nfzs"][key] = polyToXY(val, reference)

    # ell = pm.Ellipsoid(6378137, 6356752.314245)
    ell = pm.Ellipsoid(6378137, 6356752.314245)

    for point in airspace["points"]:

        new_airspace["points"].append(
            Point(
                list(
                    geodetic2enu(
                        point.x,
                        point.y,
                        0,
                        *reference,
                        ell=ell,
                        deg=True,
                    )
                )[:2]
            )
        )

    return new_airspace


def routeToLL(airspace: dict, route):
    # ell = pm.Ellipsoid(6378137, 6356752.314245)
    ell = pm.Ellipsoid(6378137, 6356752.314245)
    reference = getAirspaceRef(airspace)
    return [
        Point(
            list(
                enu2geodetic(
                    point.x,
                    point.y,
                    0,
                    *reference,
                    ell=ell,
                    deg=True,
                )
            )[:2]
        )
        for point in route
    ]
