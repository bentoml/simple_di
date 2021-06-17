'''
Provider implementations
'''

import typing

from simple_di import Provider, VT, _ensure_injected


class Static(Provider, typing.Generic[VT]):
    '''
    provider that returns static values
    '''

    def __init__(self, value: VT):
        super().__init__()
        self._value = value

    def _provide(self) -> VT:
        return self._value


class Callable(Provider, typing.Generic[VT]):
    '''
    provider that returns the result of a callable
    '''

    def __init__(self, func: typing.Callable[..., VT], *args, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def _provide(self) -> VT:
        args = [_ensure_injected(a) for a in self._args]
        kwargs = {k: _ensure_injected(v) for k, v in self._kwargs.items()}
        return self._func(*args, **kwargs)


class Configuration(Provider):
    '''
    special provider that reflects the structure of a configuration dictionary.
    '''

    def __init__(
        self, data: typing.Optional[dict] = None,
    ):
        super().__init__()
        self._data = data

    def set(self, value):
        self._data = value

    def get(self):
        if self._data is None:
            raise ValueError("Configuration Provider not initialized")
        return self._data

    def reset(self):
        raise NotImplementedError()

    def __getattr__(self, name) -> "_ConfigurationItem":
        if name in ("_data", "_override"):
            raise AttributeError()
        return _ConfigurationItem(config=self, path=(name,))

    def __repr__(self):
        return f"Configuration(data={self._data})"


class _ConfigurationItem(Provider):
    def __init__(
        self, config: Configuration, path: typing.Tuple[str, ...],
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
        if _cursor is None:
            raise ValueError("Configuration Provider not initialized")
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
