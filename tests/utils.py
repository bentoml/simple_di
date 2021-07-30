from threading import Thread
from typing import Optional, Any, Iterable, Mapping, Callable


class ThreadWithReturnValue(Thread):
    _target: Optional[Callable[..., Any]]
    _args: Iterable[Any]
    _kwargs: Mapping[str, Any]

    def __init__(
            self,
            group: None = None,
            target: Optional[Callable[..., Any]] = None,
            name: Optional[str] = None,
            args: Iterable[Any] = (),
            kwargs: Optional[Mapping[str, Any]] = None,
            *,
            daemon: Optional[bool] = None,
    ) -> None:
        super().__init__(group=group, target=target, name=name, args=args, kwargs=kwargs, daemon=daemon)
        self._return = None

    def run(self) -> None:
        if self._target is None:
            return None
        self._return = self._target(*self._args, **self._kwargs)

    def join(self, timeout: Optional[float] = None) -> Any:
        super().join(timeout=timeout)
        return self._return
