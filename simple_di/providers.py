'''
Provider implementations
'''

from typing import Any, Callable as CallableType, Dict, Optional, Tuple, Union

from simple_di import (
    Provider,
    VT,
    _SentinelClass,
    _inject_args,
    _inject_kwargs,
    inject,
    sentinel,
)


__all__ = [
    "Static",
    "Callable",
    "MemoizedCallable",
    "Factory",
    "SingletonFactory",
    "Configuration",
]


class Static(Provider[VT]):
    '''
    provider that returns static values
    '''

    def __init__(self, value: VT):
        super().__init__()
        self._value = value

    def _provide(self) -> VT:
        return self._value


class Callable(Provider[VT]):
    '''
    provider that returns the result of a callable
    '''

    def __init__(self, func: CallableType[..., VT], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self._args = args
        self._kwargs = kwargs
        self._func: CallableType[..., VT] = func

    def _provide(self) -> VT:
        return self._func(*_inject_args(self._args), **_inject_kwargs(self._kwargs))

    def __get__(self, obj: Any, objtype: Any = None) -> "Callable[VT]":
        self._func = inject(self._func.__get__(obj, objtype))  # type: ignore
        return self


class MemoizedCallable(Callable[VT]):
    '''
    provider that returns the result of a callable, but memorize the returns.
    '''

    def __init__(self, func: CallableType[..., VT], *args: Any, **kwargs: Any) -> None:
        super().__init__(func, *args, **kwargs)
        self._cache: Union[_SentinelClass, VT] = sentinel

    def _provide(self) -> VT:
        if not isinstance(self._cache, _SentinelClass):
            return self._cache
        value = self._func(*_inject_args(self._args), **_inject_kwargs(self._kwargs))
        self._cache = value
        return value


Factory = Callable
SingletonFactory = MemoizedCallable


class Configuration(Provider[Dict[str, Any]]):
    '''
    special provider that reflects the structure of a configuration dictionary.
    '''

    def __init__(
        self, data: Optional[Dict[str, Any]] = None, fallback: Any = sentinel
    ) -> None:
        super().__init__()
        self._data = data
        self.fallback = fallback

    def set(self, value: Dict[str, Any]) -> None:
        self._data = value

    def get(self) -> Union[Dict[str, Any], Any]:
        if self._data is None:
            if isinstance(self.fallback, _SentinelClass):
                raise ValueError("Configuration Provider not initialized")
            return self.fallback
        return self._data

    def reset(self) -> None:
        raise NotImplementedError()

    def __getattr__(self, name: str) -> "_ConfigurationItem":
        if name in ("_data", "_override", "fallback"):
            raise AttributeError()
        return _ConfigurationItem(config=self, path=(name,))

    def __repr__(self) -> str:
        return f"Configuration(data={self._data}, fallback={self.fallback})"


class _ConfigurationItem(Provider[Any]):
    def __init__(self, config: Configuration, path: Tuple[str, ...],) -> None:
        super().__init__()
        self._config = config
        self._path = path

    def set(self, value: Any) -> None:
        _cursor = self._config.get()
        for i in self._path[:-1]:
            _cursor = _cursor[i]
        _cursor[self._path[-1]] = value

    def get(self) -> Any:
        _cursor = self._config.get()
        if self._config.fallback is not sentinel and _cursor is self._config.fallback:
            return self._config.fallback
        for i in self._path:
            _cursor = _cursor[i]
        return _cursor

    def reset(self) -> None:
        raise NotImplementedError()

    def __getattr__(self, name: str) -> "_ConfigurationItem":
        if name in ("_config", "_path", "_override"):
            raise AttributeError()
        return type(self)(config=self._config, path=self._path + (name,))

    def __repr__(self) -> str:
        return f"_ConfigurationItem(_config={self._config._data}, _path={self._path})"
