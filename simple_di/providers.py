'''
Provider implementations
'''

from typing import Any, Callable as CallableType, Generic, Optional, Tuple

from simple_di import Provider, VT, _SentinelClass, _ensure_injected, sentinel


class Static(Provider, Generic[VT]):
    '''
    provider that returns static values
    '''

    def __init__(self, value: VT):
        super().__init__()
        self._value = value

    def _provide(self) -> VT:
        return self._value


class Callable(Provider, Generic[VT]):
    '''
    provider that returns the result of a callable
    '''

    def __init__(self, func: CallableType[..., VT], *args, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def _provide(self) -> VT:
        args = [_ensure_injected(a) for a in self._args]
        kwargs = {k: _ensure_injected(v) for k, v in self._kwargs.items()}
        return self._func(*args, **kwargs)


class MemoizedCallable(Callable, Generic[VT]):
    '''
    provider that returns the result of a callable, but memorize the returns.
    '''

    def _provide(self) -> VT:
        args = [_ensure_injected(a) for a in self._args]
        kwargs = {k: _ensure_injected(v) for k, v in self._kwargs.items()}
        value = self._func(*args, **kwargs)
        self._cache = value
        return value


class Configuration(Provider):
    '''
    special provider that reflects the structure of a configuration dictionary.
    '''

    def __init__(self, data: Optional[dict] = None, fallback: Any = sentinel):
        super().__init__()
        self._data = data
        self.fallback = fallback

    def set(self, value: dict):
        self._data = value

    def get(self) -> dict:
        if self._data is None:
            if isinstance(self.fallback, _SentinelClass):
                raise ValueError("Configuration Provider not initialized")
            return self.fallback
        return self._data

    def reset(self):
        raise NotImplementedError()

    def __getattr__(self, name) -> "_ConfigurationItem":
        if name in ("_data", "_override", "fallback"):
            raise AttributeError()
        return _ConfigurationItem(config=self, path=(name,))

    def __repr__(self):
        return f"Configuration(data={self._data})"


class _ConfigurationItem(Provider):
    def __init__(
        self, config: Configuration, path: Tuple[str, ...],
    ):
        super().__init__()
        self._config = config
        self._path = path

    def set(self, value):
        _cursor = self._config.get()
        for i in self._path[:-1]:
            _cursor = _cursor[i]
        _cursor[self._path[-1]] = value

    def get(self):
        _cursor = self._config.get()
        if self._config.fallback is not sentinel and _cursor is self._config.fallback:
            return self._config.fallback
        for i in self._path:
            _cursor = _cursor[i]
        return _cursor

    def reset(self):
        raise NotImplementedError()

    def __getattr__(self, name) -> "_ConfigurationItem":
        if name in ("_config", "_path", "_override"):
            raise AttributeError()
        return type(self)(config=self._config, path=self._path + (name,))

    def __repr__(self):
        return f"_ConfigurationItem(_config={self._config._data}, _path={self._path})"
