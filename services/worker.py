from multiprocessing import Process
from typing import Optional


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

