"""
Provider implementations
"""
import importlib
from types import LambdaType, ModuleType
from typing import Any
from typing import Callable as CallableType
from typing import Dict, NoReturn, Tuple, Union

from simple_di import (
    VT,
    Provider,
    _inject_args,
    _inject_kwargs,
    _SentinelClass,
    inject,
    sentinel,
)

__all__ = [
    "Placeholder",
    "Static",
    "Callable",
    "MemoizedCallable",
    "Factory",
    "SingletonFactory",
    "Configuration",
]


class Placeholder(Provider[VT]):
    """
    provider that must be set before get
    """

    def _provide(self) -> NoReturn:
        raise RuntimeError("Placeholder cannot be get before set")


class Static(Provider[VT]):
    """
    provider that returns static values
    """

    STATE_FIELDS: Tuple[str, ...] = Provider.STATE_FIELDS + ("_value",)

    def __init__(self, value: VT):
        super().__init__()
        self._value = value

    def _provide(self) -> VT:
        return self._value


def _probe_unique_name(module: ModuleType, origin_name: str) -> str:
    name = "__simple_di_" + origin_name.replace(".", "_").replace("<lambda>", "lambda")
    num = 0
    while hasattr(module, f"{name}{num or ''}"):
        num += 1
    return f"{name}{num or ''}"


def _patch_anonymous(func: Any) -> None:
    module_name = func.__module__
    origin_name = func.__qualname__

    module = importlib.import_module(module_name)
    name = _probe_unique_name(module, origin_name)
    func.__qualname__ = name
    func.__name__ = name
    setattr(module, name, func)


class Factory(Provider[VT]):
    """
    provider that returns the result of a callable
    """

    STATE_FIELDS: Tuple[str, ...] = Provider.STATE_FIELDS + (
        "_args",
        "_kwargs",
        "_func",
        "_chain_inject",
    )

    def __init__(self, func: CallableType[..., VT], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self._args = args
        self._kwargs = kwargs
        self._chain_inject = False
        if isinstance(func, classmethod):
            raise TypeError("Factory as decorator only supports static methods")
        if isinstance(func, LambdaType):
            _patch_anonymous(func)
        if isinstance(func, staticmethod):
            self._chain_inject = True
            func = func.__func__
            _patch_anonymous(func)
        self._func = func

    def _provide(self) -> VT:
        if self._chain_inject:
            return inject(self._func)(
                *_inject_args(self._args), **_inject_kwargs(self._kwargs)
            )
        else:
            return self._func(*_inject_args(self._args), **_inject_kwargs(self._kwargs))


class SingletonFactory(Factory[VT]):
    """
    provider that returns the result of a callable, but memorize the returns.
    """

    STATE_FIELDS: Tuple[str, ...] = Factory.STATE_FIELDS + ("_cache",)

    def __init__(self, func: CallableType[..., VT], *args: Any, **kwargs: Any) -> None:
        super().__init__(func, *args, **kwargs)
        self._cache: Union[_SentinelClass, VT] = sentinel

    def _provide(self) -> VT:
        if not isinstance(self._cache, _SentinelClass):
            return self._cache
        value = super()._provide()
        self._cache = value
        return value


Callable = Factory
MemoizedCallable = SingletonFactory

ConfigDictType = Dict[Union[str, int], Any]
PathItemType = Union[int, str, Provider[int], Provider[str]]


class Configuration(Provider[ConfigDictType]):
    """
    special provider that reflects the structure of a configuration dictionary.
    """

    STATE_FIELDS: Tuple[str, ...] = Provider.STATE_FIELDS + ("_data", "fallback")

    def __init__(
        self,
        data: Union[_SentinelClass, ConfigDictType] = sentinel,
        fallback: Any = sentinel,
    ) -> None:
        super().__init__()
        self._data = data
        self.fallback = fallback

    def set(self, value: Union[_SentinelClass, ConfigDictType]) -> None:
        if isinstance(value, _SentinelClass):
            return
        self._data = value

    def get(self) -> Union[ConfigDictType, Any]:
        if isinstance(self._data, _SentinelClass):
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

    def __getitem__(self, key: PathItemType) -> "_ConfigurationItem":
        return _ConfigurationItem(config=self, path=(key,))

    def __repr__(self) -> str:
        return f"Configuration(data={self._data}, fallback={self.fallback})"


class _ConfigurationItem(Provider[Any]):

    STATE_FIELDS: Tuple[str, ...] = Provider.STATE_FIELDS + ("_config", "_path")

    def __init__(
        self,
        config: Configuration,
        path: Tuple[PathItemType, ...],
    ) -> None:
        super().__init__()
        self._config = config
        self._path = path

    def set(self, value: Any) -> None:
        if isinstance(value, _SentinelClass):
            return
        _cursor = self._config.get()
        for i in self._path[:-1]:
            if isinstance(i, Provider):
                i = i.get()
            _next: Union[_SentinelClass, Dict[Any, Any]] = _cursor.get(i, sentinel)
            if isinstance(_next, _SentinelClass):
                _next = dict()
                _cursor[i] = _next
            _cursor = _next
        last_i = self._path[-1]
        if isinstance(last_i, Provider):
            last_i = last_i.get()
        _cursor[last_i] = value

    def get(self) -> Any:
        _cursor = self._config.get()
        if (
            not isinstance(self._config.fallback, _SentinelClass)
            and _cursor is self._config.fallback
        ):
            return self._config.fallback
        for i in self._path:
            if isinstance(i, Provider):
                i = i.get()
            _cursor = _cursor[i]
        return _cursor

    def reset(self) -> None:
        raise NotImplementedError()

    def __getattr__(self, name: str) -> "_ConfigurationItem":
        if name in ("_config", "_path", "_override"):
            raise AttributeError()
        return type(self)(config=self._config, path=self._path + (name,))

    def __getitem__(self, key: PathItemType) -> "_ConfigurationItem":
        return type(self)(config=self._config, path=self._path + (key,))

    def __repr__(self) -> str:
        return f"_ConfigurationItem(_config={self._config._data}, _path={self._path})"
