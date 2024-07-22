import asyncio


async def worker(
    n: int,
    task_queue: asyncio.Queue,
):
    worker_name = f"worker-{n+1}"
    worker_name += " " if n + 1 < 10 else ""
    responses = []
    i = 0

    while not task_queue.empty():
        # get the next task
        func, args = await task_queue.get()
        response = await func(*args)

        responses.append(response)
        i += 1
        task_queue.task_done()

    # collate results
    results = []
    for r in responses:
        results.append(r)

    return results
