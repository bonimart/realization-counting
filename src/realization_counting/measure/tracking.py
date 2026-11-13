import functools
import typing
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from types import ModuleType
from unittest.mock import patch


@dataclass
class RecursionStats:
    calls: int = 0
    weighted: int = 0
    max_depth: int = 0
    _depth: int = field(default=0, repr=False)

    def reset(self):
        self.calls = self.weighted = self.max_depth = self._depth = 0

    def export(self) -> typing.Self:
        return deepcopy(self)


class TrackedFunction[**P, R](typing.Protocol):
    """Typing helper for functions wrapped inside `track_recursion` decorator."""

    stats: RecursionStats

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...


def track_recursion[**P, R](
    weight: typing.Callable[..., int] = lambda *_, **__: 1,
) -> typing.Callable[[typing.Callable[P, R]], TrackedFunction[P, R]]:
    """Count calls to the decorated function and sum a per-call weight."""

    def decorator(func: typing.Callable[P, R]) -> TrackedFunction[P, R]:
        stats = RecursionStats()

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            stats.calls += 1
            stats.weighted += weight(*args, **kwargs)
            stats._depth += 1
            stats.max_depth = max(stats._depth, stats.max_depth)
            try:
                return func(*args, **kwargs)
            finally:
                stats._depth -= 1

        wrapper.stats = stats  # ty: ignore[missing-attribute]
        return typing.cast(TrackedFunction[P, R], wrapper)

    return decorator


@contextmanager
def patched[F: typing.Callable[..., typing.Any]](
    module: ModuleType, name: str, decorator: typing.Callable[[F], F]
) -> typing.Generator[F]:
    """Replace `module.name` with `decorator(module.name)` so recursive calls go through it too."""
    func = decorator(getattr(module, name))
    with patch.object(module, name, func):
        yield func


@contextmanager
def tracked(
    module: ModuleType,
    name: str,
    weight: typing.Callable[..., int] = lambda *_, **__: 1,
) -> typing.Generator[RecursionStats]:
    with patched(module, name, track_recursion(weight)) as func:
        yield func.stats
