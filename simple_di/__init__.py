'''
A simple dependency injection framework
'''
import functools
import inspect
from typing import Dict, Generic, Tuple, TypeVar, Union


class _SentinelClass:
    pass


sentinel = _SentinelClass()


VT = TypeVar("VT")


class Provider(Generic[VT]):
    '''
    The base class for Provider implementations. Could be used as the type annotations
    of all the implementations.
    '''

    def __init__(self) -> None:
        self._override: Union[_SentinelClass, VT] = sentinel

    def _provide(self) -> VT:
        raise NotImplementedError

    def set(self, value: VT) -> None:
        '''
        set the value to this provider, overriding the original values
        '''
        self._override = value

    def get(self) -> VT:
        '''
        get the value of this provider
        '''
        if not isinstance(self._override, _SentinelClass):
            return self._override
        return self._provide()

    def reset(self) -> None:
        '''
        remove the overriding and restore the original value
        '''
        self._override = sentinel


class _ProvideClass:
    '''
    Used as the default value of a injected functool/method. Would be replaced by the
    final value of the provider when this function/method gets called.
    '''

    def __getitem__(self, provider: Provider[VT]) -> VT:
        return provider  # type: ignore


Provide = _ProvideClass()


def _inject_args(args: Tuple) -> Tuple:
    return tuple(a.get() if isinstance(a, Provider) else a for a in args)


def _inject_kwargs(kwargs: Dict) -> Dict:
    return {k: v.get() if isinstance(v, Provider) else v for k, v in kwargs.items()}


def _inject(func, respect_none: bool):
    '''
    Used with `Provide`, inject values to provided defaults of the decorated
    function/method when gets called.
    '''
    sig = inspect.signature(func)

    @functools.wraps(func)
    def _(*args, **kwargs):
        if respect_none:
            filtered_args = tuple(a for a in args if a is not sentinel)
            filtered_kwargs = {k: v for k, v in kwargs.items() if v is not sentinel}
        else:
            filtered_args = tuple(a for a in args if a is not None)
            filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}

        bind = sig.bind_partial(*filtered_args, **filtered_kwargs)
        bind.apply_defaults()

        return func(*_inject_args(bind.args), **_inject_kwargs(bind.kwargs))

    return _


def inject(func=None, respect_none=True):
    if func is None:
        return functools.partial(_inject, respect_none=respect_none)

    if callable(func):
        return _inject(func, respect_none=respect_none)

    raise ValueError('You must pass either int or str')


class Container:
    '''
    The base class of containers
    '''


not_passed = sentinel

__all__ = ["Container", "Provider", "Provide", "inject", "not_passed"]
