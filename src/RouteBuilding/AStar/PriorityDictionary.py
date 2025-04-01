import heapq


class PriorityDictionary:
    def __init__(self):
        self._heap = []
        self._dict = {}

    def __len__(self):
        return len(self._dict)

    def __contains__(self, key):
        return key in self._dict

    def __getitem__(self, key):
        return self._dict[key]

    def __setitem__(self, key, value):
        if key in self._dict:
            if value.g < self._dict[key].g:
                self._dict[key] = value
                heapq.heapify(self._heap)
        else:
            heapq.heappush(self._heap, (value.f, key))
            self._dict[key] = value

    def __delitem__(self, key):
        del self._dict[key]
        self._rebuild_heap()

    def _rebuild_heap(self):
        self._heap = [(value.f, key) for key, value in self._dict.items()]
        heapq.heapify(self._heap)

    def popitem(self):
        _, key = heapq.heappop(self._heap)
        value = self._dict[key]
        del self._dict[key]

        if len(self._heap) != len(self._dict):
            print(len(self._heap), len(self._dict))
            raise KeyError()
        return value

    def peekitem(self):
        (value, key) = self._heap[0]

        if len(self._heap) != len(self._dict):
            print(len(self._heap), len(self._dict))
            raise KeyError()
        return (key, value)
