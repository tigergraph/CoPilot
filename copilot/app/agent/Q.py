from threading import Lock


DONE = "DONE"


class Q:
    def __init__(self):
        self.q = []
        self.l = Lock()

    def put(self, item):
        with self.l:
            self.q.append(item)

    def pop(self):
        if len(self.q) > 0:
            with self.l:
                item = self.q[0]
                self.q = self.q[1:]
                return item


    def clear(self):
        self.q.clear()
