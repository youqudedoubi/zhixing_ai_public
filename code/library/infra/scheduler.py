"""任务调度器。

主要职责：
- 控制并发度
- 管理任务进度
- 保证结果与输入样本的顺序一致

当前实现为简化版同步/线程池调度器，后续可扩展为 asyncio 版本。
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Iterable, List, Sequence, Tuple, TypeVar
from tqdm import tqdm

T = TypeVar("T")
R = TypeVar("R")


class Scheduler:
    """简单的并发调度器骨架。"""

    def __init__(self, max_workers: int = 8) -> None:
        self.max_workers = max_workers

    def map_ordered(
        self,
        fn: Callable[[T], R],
        items: Sequence[T],
        desc: str = "Processing",
        **tqdm_kwargs,
    ) -> List[R]:
        """对 items 进行并发调度，并保证返回结果与输入顺序一致。

        Args:
            fn: 单个元素的处理函数。
            items: 待处理元素序列（必须支持 __len__）。
            desc: tqdm 进度条描述文字。
            **tqdm_kwargs: 其他传递给 tqdm 的参数。
        """
        if not items:
            return []

        total = len(items)
        results: List[Any] = [None] * total

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(fn, item): idx for idx, item in enumerate(items)
            }

            # 使用 tqdm 包装 as_completed，显示进度
            for future in tqdm(
                as_completed(futures),
                total=total,
                desc=desc,
                **tqdm_kwargs,
            ):
                idx = futures[future]
                try:
                    results[idx] = future.result()
                except Exception as exc:
                    raise RuntimeError(f"Task {idx} failed: {exc!r}") from exc

        return results

    def map_unordered(
        self,
        fn: Callable[[T], R],
        items: Iterable[T],
    ) -> Iterable[Tuple[T, R]]:
        """对 items 进行并发调度，不保证结果顺序。

        返回 (item, result) 的迭代器。
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_item = {executor.submit(fn, item): item for item in items}

            for future in as_completed(future_to_item):
                item = future_to_item[future]
                yield item, future.result()
