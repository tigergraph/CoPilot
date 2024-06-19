from threading import Lock

DONE = "DONE"


class Q:
    def __init__(self):
        self.q = []
        self.l = Lock()

    def put(self, item):
        # print("put waiting")
        with self.l:
            # print("putting")
            self.q.append(item)

    def pop(self):
        if len(self.q) > 0:
            # print("pop waiting")
            with self.l:
                # print("popping")
                item = self.q[0]
                self.q = self.q[1:]
                return item

        return None
