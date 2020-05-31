from itertools import product


class SpatialHash:
    def __init__(self):
        self.grid = {}
        self.items = set()

    def rebuild(self):
        self.grid = {}
        for item in self.items:
            self.insert(item)

    def insert(self, entity):
        self.items.add(entity)
        for cell in self._rect_cells(entity.rect):
            items = self.grid.get(cell)
            if items is None:
                self.grid[cell] = [entity]
            else:
                items.append(entity)

    def _rect_cells(s, rect):
        x1, y1 = rect.topleft
        x1 //= 32
        y1 //= 32
        x2, y2 = rect.bottomright
        x2 = x2 // 32 + 1
        y2 = y2 // 32 + 1
        return product(range(x1, x2), range(y1, y2))

    def query(s, rect):
        items = set()
        for cell in s._rect_cells(rect):
            items.update(s.grid.get(cell, ()))
        return items

