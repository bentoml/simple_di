"""
state loading & saving tests
"""
import pickle
import uuid
from typing import NoReturn, Tuple

from simple_di import VT, Provide, Provider, container, inject, sync_container
from simple_di.providers import Configuration, Factory, SingletonFactory, Static


class NotPicklable:
    def __getstate__(self) -> NoReturn:
        raise TypeError("Not picklable")  # will raise once try to pickle it


@container
class OptionsClass:
    status: Provider[int] = Static(1)

    @SingletonFactory
    @staticmethod
    def uid() -> str:
        return uuid.uuid4().hex

    uid2: Provider[str] = SingletonFactory(lambda: uuid.uuid4().hex)
    no_picklable: Provider[NotPicklable] = Factory(NotPicklable)
    config: Configuration = Configuration()


Options = OptionsClass()


def test_factory_state() -> None:
    RestoredUID = pickle.loads(pickle.dumps(Options.uid))
    uid = Options.uid.get()

    assert uid != RestoredUID.get()  # restore state of SingletonFactory

    RestoredUID = pickle.loads(pickle.dumps(Options.uid))
    assert uid == RestoredUID.get()  # restore state of SingletonFactory

    RestoredOptions = pickle.loads(pickle.dumps(Options))
    assert uid == RestoredOptions.uid.get()  # restore state of SingletonFactory


def test_lambda_factory_state() -> None:
    uid = Options.uid2.get()
    RestoredUID = pickle.loads(pickle.dumps(Options.uid2))
    assert uid == RestoredUID.get()  # restore state of SingletonFactory

    RestoredOptions = pickle.loads(pickle.dumps(Options))
    assert uid == RestoredOptions.uid2.get()  # restore state of SingletonFactory


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


def _assert_options(options: OptionsClass) -> None:
    assert options.status.get() == 2, options.status.get()


def test_spawn_process() -> None:

    Options.status.reset()
    assert Options.status.get() == 1
    Options.status.set(2)

    import multiprocessing

    ctx = multiprocessing.get_context("spawn")

    p = ctx.Process(target=_assert_options, args=(Options,), daemon=True)
    p.start()
    p.join()
    assert p.exitcode == 0


def _assert_synced_options(options: OptionsClass) -> None:
    sync_container(from_=options, to_=Options)
    assert Options.status.get() == 2, Options.status.get()


def test_sync_container() -> None:
    Options.status.reset()
    assert Options.status.get() == 1
    Options.status.set(2)

    import multiprocessing

    ctx = multiprocessing.get_context("spawn")

    p = ctx.Process(target=_assert_synced_options, args=(Options,), daemon=True)
    p.start()
    p.join()
    assert p.exitcode == 0


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


class Point(Provider[Tuple[int, int]]):

    STATE_FIELDS = Provider.STATE_FIELDS + (
        "x",
        "y",
    )

    def __init__(self, x: int, y: int):
        super().__init__()
        self.x = x
        self.y = y
        self.z = 233

    def _provide(self) -> Tuple[int, int]:
        return self.x, self.y


def test_state_fields() -> None:

    point = Point(1, 2)
    assert point.get() == (1, 2)
    assert hasattr(point, "z")

    new_point = pickle.loads(pickle.dumps(point))
    assert new_point.get() == (1, 2)
    assert not hasattr(new_point, "z")
