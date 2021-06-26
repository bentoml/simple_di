'''
state loading & saving tests
'''
import pickle
from typing import NoReturn, Tuple
import uuid

from simple_di import Container, Provide, Provider, inject
from simple_di.providers import Configuration, Factory, SingletonFactory


class NotPicklable:
    def __getstate__(self) -> NoReturn:
        raise TypeError('Not picklable')  # will raise once try to pickle it


class Options(Container):
    uid: Provider[str] = SingletonFactory(lambda: uuid.uuid4().hex)
    no_picklable: Provider[NotPicklable] = Factory(NotPicklable)
    config: Configuration = Configuration()


def test_factory_state() -> None:
    uid = Options.uid.get()
    RestoredOptions = pickle.loads(pickle.dumps(Options))
    assert uid == RestoredOptions.uid.get()  # restore state of SingletonFactory


def test_singleton_state() -> None:
    no_picklable = Options.no_picklable.get()
    RestoredOptions = pickle.loads(pickle.dumps(Options))
    assert no_picklable is not RestoredOptions.no_picklable.get()  # regenerate Factory


def test_config_state() -> None:
    Options.config.set({})
    Options.config.b.a.set(1)

    value = Options.config.b.a.get()
    RestoredOptions = pickle.loads(pickle.dumps(Options))
    assert value == RestoredOptions.config.b.a.get()  # restore config value


def test_integration() -> None:
    @inject
    def func1(
        uid: str = Provide[Options.uid],
        no_picklable: NotPicklable = Provide[Options.no_picklable],
    ) -> Tuple[str, NotPicklable]:
        return uid, no_picklable

    uid1, no_picklable1 = func1()

    bytes_ = pickle.dumps(Options)
    RestoredOptions = pickle.loads(bytes_)

    @inject
    def func2(
        uid: str = Provide[RestoredOptions.uid],
        no_picklable: NotPicklable = Provide[RestoredOptions.no_picklable],
    ) -> Tuple[str, NotPicklable]:
        return uid, no_picklable

    uid2, no_picklable2 = func2()

    assert uid1 == uid2  # restore state of SingletonFactory
    assert no_picklable1 is not no_picklable2  # regenerate Factory
