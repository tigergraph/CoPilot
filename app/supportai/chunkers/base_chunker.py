class BaseChunker:
    def __init__(self):
        pass

    def chunk(self, *args, **kwargs):
        raise NotImplementedError("chunk method must be implemented")

    def __call__(self, *args, **kwargs):
        return self.chunk(*args, **kwargs)
