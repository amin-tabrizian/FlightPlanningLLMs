import json
from pathlib import Path
from typing import List

import numpy as np
from shapely.geometry import Point, Polygon


def prepareSpace(path: Path) -> dict:
    paths = discoverFiles(path)
    print("Converting Files...", end="\r")

    airspace = {"airspace": None}

    for path in paths:
        with open(path) as file:
            features = json.load(file)["features"]
            for feature in features:
                if feature["properties"]["Name"] == "Airspace":
                    if airspace["airspace"] is None:
                        airspace = loadAirspace(feature["geometry"])
                    else:
                        raise ValueError("Duplicate enteries found for Airspace")
                elif feature["geometry"]["type"] == "Polygon":
                    airspace = addNFZ(feature["geometry"], airspace, feature["properties"]["Name"])
                elif feature["geometry"]["type"] == "Point":
                    if "points" in airspace:
                        airspace["points"].append(Point(feature["geometry"]["coordinates"]))
                    else:
                        airspace["points"] = [Point(feature["geometry"]["coordinates"])]

    print("Files Converted...", end="\n")
    return airspace


def loadAirspace(geom: dict) -> dict:
    return {"airspace": Polygon(np.array(geom["coordinates"])[0])}


def addNFZ(geom: dict, airspace: dict, name: str) -> dict:
    if "nfzs" in airspace:
        airspace["nfzs"][name] = Polygon(np.array(geom["coordinates"])[0])

    else:
        airspace["nfzs"] = {name: Polygon(np.array(geom["coordinates"])[0])}

    return airspace


def discoverFiles(path: Path) -> List:
    folders = list(path.glob("*.geojson"))

    if not folders:
        path = Path(str(path).replace("\\", "/"))

    folders = list(path.glob("*.geojson"))

    print(f"\nDiscovered {len(folders)} .geojson files in `{path}`:")
    for file in folders:
        print(f"\t-- {file}")

    print("\n")

    return folders
