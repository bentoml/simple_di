'''
A simple dependency injection framework
'''
import functools
import inspect
import typing


class _SentinelClass:
    pass


sentinel = _SentinelClass()


VT = typing.TypeVar("VT")


class Provider(typing.Generic[VT]):
    '''
    The base class for Provider implementations. Could be used as the type annotations
    of all the implementations.
    '''

    def __init__(self):
        self._override: typing.Union[_SentinelClass, VT] = sentinel
        self._cache: typing.Union[_SentinelClass, VT] = sentinel

    def _provide(self) -> VT:
        raise NotImplementedError

    def set(self, value: VT):
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
        if not isinstance(self._cache, _SentinelClass):
            return self._cache
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


def _ensure_injected(maybe_provider: typing.Union[Provider, VT]) -> VT:
    if isinstance(maybe_provider, Provider):
        return maybe_provider.get()
    return maybe_provider


def inject(func):
    '''
    Used with `Provide`, inject values to provided defaults of the decorated
    function/method when gets called.
    '''
    sig = inspect.signature(func)

    @functools.wraps(func)
    def _(*args, **kwargs):
        filtered_args = tuple(a for a in args if a is not sentinel)
        filtered_kwargs = {k: v for k, v in kwargs.items() if v is not sentinel}
        bind = sig.bind_partial(*filtered_args, **filtered_kwargs)
        bind.apply_defaults()

        injected_args = tuple(_ensure_injected(v) for v in bind.args)
        injected_kwargs = {k: _ensure_injected(v) for k, v in bind.kwargs.items()}
        return func(*injected_args, **injected_kwargs)

    return _


class Container:
    '''
    The base class of containers
    '''


not_passed = sentinel

__all__ = ["Container", "Provider", "Provide", "inject", "not_passed"]
