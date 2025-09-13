from multiprocessing import Process
from typing import Optional
from threading import Thread


def _worker_entrypoint() -> None:
    import asyncio
    import receive

    asyncio.run(receive.main())


def start_receive_worker() -> Process:
    """Start the receive.py worker in a background process."""
    proc = Process(target=_worker_entrypoint, name="yolo-receive-worker", daemon=True)
    proc.start()
    print(" [*] Started receive.py worker process (pid=", proc.pid, ")")
    return proc


def stop_receive_worker(proc: Optional[Process]) -> None:
    """Stop the worker process if it's running."""
    if proc and proc.is_alive():
        proc.terminate()
        proc.join(timeout=5)


def _thread_entrypoint(async_main) -> None:
    import asyncio
    asyncio.run(async_main())


def start_billing_consumer_thread() -> Thread:
    from billing_consumer import main as billing_main

    t = Thread(target=_thread_entrypoint, args=(billing_main,), name="billing-consumer", daemon=True)
    t.start()
    print(" [*] Started billing consumer thread")
    return t


def start_analytics_consumer_thread() -> Thread:
    from analytics_consumer import main as analytics_main

    t = Thread(target=_thread_entrypoint, args=(analytics_main,), name="analytics-consumer", daemon=True)
    t.start()
    print(" [*] Started analytics consumer thread")
    return t

