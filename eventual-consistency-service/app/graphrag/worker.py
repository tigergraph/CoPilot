import asyncio


# class Channel(asyncio.Queue):
#     def __init__(self, maxsize=0):
#         self.is_open = True
#         super().__init__(maxsize)
#
#     def close(self):
#         self.is_open = False


async def worker(
    n: int,
    task_queue: asyncio.Queue,
):
    # init worker logging/reporting (TODO)
    worker_name = f"worker-{n+1}"
    worker_name += " " if n + 1 < 10 else ""

    while task_queue.empty():
        print(f"{worker_name} waiting")
        await asyncio.sleep(1)

    # consume task queue
    print(f"{worker_name} started")
    responses = []
    while not task_queue.empty():
        # get the next task
        func, args = await task_queue.get()

        # execute the task
        response = await func(*args)

        # append task results to worker results/response
        responses.append(response)

        # mark task as done
        task_queue.task_done()

    print(f"{worker_name} done")
    return responses
