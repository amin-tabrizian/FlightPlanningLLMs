"""This holds the code for the Graph for RRT*-FN.100
The Graph contains the bulk of the route generation code for selecting new waypoints, verifying validity, connecting the graph etc.
"""  # noqa: 501

# Imports
import random
from typing import List


import numpy as np
from shapely.geometry import Point, LineString

from .Node import Node

MIN_DIST = 50


class Graph:
    def __init__(
        self,
        start: Point,
        goal: Point,
        airspace: dict,
        min_step: float = 50.0,
        min_end_dist=100,
    ):
        self.start = Node(start, None, 0)
        self.goal = Node(goal, None, float("inf"))

        self.min_step = min_step
        self.min_end_dist = min_end_dist

        self.airspace = airspace

        self.vertices = {self.start}
        self.last_added = self.start
        self.min_distance = self.start.pos.distance(self.goal.pos)

        print(
            min(
                min(self.start.pos.distance(nfz) for nfz in self.airspace["nfzs"].values()),
                min(self.goal.pos.distance(nfz) for nfz in self.airspace["nfzs"].values()),
            )
        )

    @property
    def success(self) -> bool:
        return self.goal in self.vertices

    def addVertex(self, vertex: Node) -> None:
        self.vertices.add(vertex)
        self.last_added = vertex

        self.min_distance = min(self.min_distance, vertex.pos.distance(self.goal.pos))

    def randomPosition(self, rand) -> Point:

        if rand:
            minx, miny, maxx, maxy = self.airspace["airspace"].bounds
            minx -= 1000
            miny -= 1000
            maxx += 1000
            maxy += 1000
        else:
            minx = self.goal.x - (self.min_end_dist * 2)
            miny = self.goal.y - (self.min_end_dist * 2)

            maxx = self.goal.x + (self.min_end_dist * 2)
            maxy = self.goal.y + (self.min_end_dist * 2)

        posx = np.random.uniform(minx, maxx)
        posy = np.random.uniform(miny, maxy)

        return Point(posx, posy)

    def checkCollision(self, p1: Point, p2: Point) -> bool:
        line = LineString([p1, p2])

        if min(line.distance(nfz) for nfz in self.airspace["nfzs"].values()) < MIN_DIST:
            return True

        # if any(line.intersects(nfz) for nfz in self.airspace["nfzs"].values()):
        #     return True

        return any(line.distance(nfz) < MIN_DIST for nfz in self.airspace["nfzs"].values()) or line.intersects(
            LineString(list(self.airspace["airspace"].exterior.coords))
        )

    def newVertex(self) -> Node:
        near_vertex = None

        rand = np.random.randn() > 0.2

        c = 0

        while near_vertex is None:
            c += 1
            if not rand and c > 5:
                rand = True

            random_position = self.randomPosition(rand)

            min_vex_dist = float("inf")

            for vex in self.vertices:
                d = vex.distance(random_position)

                if d < min_vex_dist:
                    min_vex_dist = d
                    near_vertex = vex

            if near_vertex is None:
                continue

            dirn = np.array(random_position.xy).reshape(-1) - np.array(near_vertex.pos.xy).reshape(-1)
            length = np.linalg.norm(dirn)

            dirn = (dirn / length) * min(self.min_step, length)

            new_point = Point([near_vertex.x + dirn[0], near_vertex.y + dirn[1]])

            if (
                self.checkCollision(near_vertex.pos, new_point)
                or (not self.airspace["airspace"].contains(new_point))
                or any(nfz.contains(new_point) for nfz in self.airspace["nfzs"].values())
            ):
                near_vertex = None
                continue

            if self.goal.distance(new_point) < self.min_end_dist and (
                not self.checkCollision(self.goal.pos, near_vertex.pos)
            ):

                self.goal.changeParent(near_vertex, near_vertex.cost + near_vertex.distance(self.goal))
                return self.goal

        return Node(new_point, near_vertex, near_vertex.cost + near_vertex.distance(new_point))

    def updateGraph(self) -> None:
        for vex in self.vertices:
            dist = vex.distance(self.last_added)

            if vex == self.last_added or dist > self.min_step or vex == self.last_added.parent:
                continue

            if (self.last_added.cost + dist < vex.cost) and (not self.checkCollision(self.last_added.pos, vex.pos)):
                vex.changeParent(self.last_added, self.last_added.cost + dist)

    def repairLength(self) -> None:
        childless = [
            vex
            for vex in self.vertices
            if (
                vex is not self.last_added and len(vex.children) == 0 and vex is not self.goal and vex is not self.start
            )
        ]

        if not childless:
            return

        c = random.choice(childless)

        c.parent.delChild(c)
        self.vertices.remove(c)

    def shortenOnPath(self, path):
        path = LineString(path)
        distances = np.arange(0, path.length, 10)

        points = [path.interpolate(d) for d in distances] + [Point(path.coords[-1])]

        path = points

        optimised = [points[-1]]

        i = len(path) - 1

        while i > 0:
            j = 0
            while j < i - 1:
                ls = LineString((path[i], path[j]))

                # if any(
                #     ls.intersects(nfz) for nfz in self.airspace['nfzs'].values()
                # ):
                #     print(i, j, 'intersection')

                # if min(ls.distance(nfz) for nfz in self.airspace['nfzs'].values()) < MIN_DIST:
                #     print(i, j, 'distance')

                if not self.checkCollision(path[i], path[j]):
                    # print(i, j, "Here")
                    break
                else:
                    j += 1

            optimised.append(path[j])
            i = j

        ls = LineString(optimised)

        path = LineString([Point(c[0], c[1]) for c in list(ls.coords)])
        distances = np.arange(0, path.length, 10)

        points = [path.interpolate(d) for d in distances] + [Point(path.coords[-1])]

        path = points

        optimised = [points[0]]

        i = 0

        while i < len(path) - 1:
            j = len(path) - 1
            while j > i + 1:
                ls = LineString((path[i], path[j]))

                # if any(
                #     ls.intersects(nfz) for nfz in self.airspace['nfzs'].values()
                # ):
                #     print(i, j, 'intersection')

                # if min(ls.distance(nfz) for nfz in self.airspace['nfzs'].values()) < MIN_DIST:
                #     print(i, j, 'distance')

                if not self.checkCollision(path[i], path[j]):
                    # print(i, j, "Here")
                    break
                else:
                    j -= 1

            optimised.append(path[j])
            i = j

        ls = LineString(optimised)

        path = [Point(c[0], c[1]) for c in list(ls.coords)]

        return path

    def shortenRoute(self, iterations=1):
        path = self.getRoute()

        for _ in range(iterations):
            path = self.shortenOnPath(path)

        print(min(LineString(path).distance(nfz) for nfz in self.airspace["nfzs"].values()))

        return path
        # return path

    def step(self) -> None:
        self.addVertex(self.newVertex())
        self.updateGraph()

    def getRoute(self) -> List[List[Point]]:
        route = []

        if self.goal.parent is None:
            return route

        node = self.goal

        while node is not None:
            route.insert(0, node.pos)

            node = node.parent

        return route
