"""This holds the code for a Node for RRT*-FN.
The Node holds specific information used by the Graph
"""

# Imports

from shapely.geometry import Point


class Node:
    def __init__(self, pos: Point, parent: object, cost: float):
        self.pos = pos
        self.parent = parent
        self.cost = cost

        self.children = set()

        if parent is not None:
            self.parent.addChild(self)

    @property
    def x(self) -> float:
        return self.pos.x

    @property
    def y(self) -> float:
        return self.pos.y

    def delChild(self, child: object):
        self.children.remove(child)

    def addChild(self, child: object):
        self.children.add(child)

    def changeParent(self, new_parent: object, new_cost: float):
        if new_cost > self.cost:
            return

        if self.parent is not None:
            self.parent.delChild(self)

        self.parent = new_parent
        self.cost = new_cost

        self.parent.addChild(self)

    def distance(self, __o: object):
        if isinstance(__o, Point):
            return self.pos.distance(__o)
        else:
            return self.pos.distance(__o.pos)
