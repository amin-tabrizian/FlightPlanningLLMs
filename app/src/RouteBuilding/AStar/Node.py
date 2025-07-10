class Node:
    def __init__(self, pos, parent, g, h, times):
        self.parent = parent
        self.pos = pos
        self.g = g
        self.h = h
        self.times = times

    @property
    def f(self):
        return self.g + self.h

    def __lt__(self, __o: object):
        return self.f < __o.f

    def __gt__(self, __o: object):
        return self.f > __o.f

    def __le__(self, __o: object):
        return self.f <= __o.f

    def __ge__(self, __o: object):
        return self.f >= __o.f
