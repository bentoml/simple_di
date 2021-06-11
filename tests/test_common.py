'''
common tests
'''
import typing

VT = typing.TypeVar("VT")


class Provider(typing.Generic[VT]):
    def provide(self) -> VT:
        pass


class Callback(Provider, typing.Generic[VT]):
    def __init__(self, func: typing.Callable[[], VT]):
        self.func = func

    def provide(self) -> VT:
        return self.func()


def _ensure_injected(maybe_provider: typing.Union[Provider[VT], VT]) -> VT:
    if isinstance(maybe_provider, Provider):
        return maybe_provider.provide()
    return maybe_provider


def inject(func):
    def _(*args, **kwargs):
        injected_args = [_ensure_injected(a) for a in args]
        injected_kwargs = {k: _ensure_injected(v) for k, v in kwargs.items()}
        return func(*injected_args, **injected_kwargs)

    return _


class Config:
    a = Callback(lambda: 1)


def test_inject():
    @inject
    def func(a: Provider[int] = Config.a):
        return a

    assert func() == 1
