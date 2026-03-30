import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class WorkerPool:
    def __init__(self, max_workers: int = 1):
        self.max_workers = max(1, max_workers)

    def map(
        self,
        func: Callable[[T], R],
        items: list[T],
        progress_callback: Callable[[int, int, T | None, R | None, Exception | None], None] | None = None,
    ) -> list[tuple[T, R | None, Exception | None]]:
        """
        Execute func on each item, respecting max_workers concurrency.
        progress_callback(completed_count, total, item, result, error)
        Returns list of (item, result, error) tuples.
        """
        results = []
        total = len(items)

        if total == 0:
            return results

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_item = {executor.submit(func, item): item for item in items}
            completed = 0

            for future in as_completed(future_to_item):
                item = future_to_item[future]
                completed += 1
                try:
                    result = future.result()
                    results.append((item, result, None))
                    if progress_callback:
                        progress_callback(completed, total, item, result, None)
                except Exception as e:
                    logger.error(f"Error processing {item}: {e}")
                    results.append((item, None, e))
                    if progress_callback:
                        progress_callback(completed, total, item, None, e)

        return results
