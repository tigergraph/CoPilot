from asyncio import Queue


class ReuseableChannel:
    def __init__(self, maxsize=0) -> None:
        self.maxsize = maxsize
        self.q = Queue(maxsize)
        self._closed = False
        self._should_flush = False

    async def put(self, item: any) -> None:
        await self.q.put(item)

    async def get(self) -> any:
        return await self.q.get()

    def closed(self):
        return self._closed

    def should_flush(self):
        return self._should_flush

    async def flush(self, flush_msg=None):
        self._should_flush = True
        await self.put(flush_msg)

    def empty(self):
        return self.q.empty()

    def close(self):
        self._closed = True

    def qsize(self) -> int:
        return self.q.qsize()

    def reopen(self):
        self._closed = False
