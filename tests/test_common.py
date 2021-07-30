"""
common tests
"""
import random
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, Tuple
from unittest import TestCase
from unittest.mock import patch

from simple_di import Provide, Provider, container, inject
from simple_di.providers import Configuration, Factory, SingletonFactory, Static, ThreadLocalSingletonFactory

from tests.utils import ThreadWithReturnValue

# Usage


def test_inject_function() -> None:
    @container
    class Options:
        cpu: Provider[int] = Static(2)
        worker: Provider[int] = Factory(lambda c: 2 * int(c) + 1, c=cpu)

    OPTIONS = Options()

    @inject
    def func(worker: int = Provide[OPTIONS.worker]) -> int:
        return worker

    assert func() == 5
    assert func(1) == 1

    OPTIONS.worker.set(2)
    assert func() == 2

    OPTIONS.worker.reset()
    assert func() == 5

    OPTIONS.cpu.set(1)
    assert func() == 3
    OPTIONS.cpu.reset()


def test_inject_method() -> None:
    @container
    class Options:
        cpu: Provider[int] = Static(2)
        worker: Provider[int] = Factory(lambda c: 2 * int(c) + 1, c=cpu)

    OPTIONS = Options()

    class A:
        @inject
        def __init__(self, worker: int = Provide[OPTIONS.worker]):
            self.worker = worker

        @classmethod
        @inject
        def create(cls, worker: int = Provide[OPTIONS.worker]) -> "A":
            return cls(worker)

    assert A().worker == A.create().worker == 5
    assert A(1).worker == A.create(1).worker == 1

    OPTIONS.worker.set(2)
    assert A().worker == A.create().worker == 2

    OPTIONS.worker.reset()
    assert A().worker == A.create().worker == 5

    OPTIONS.cpu.set(1)
    assert A().worker == A.create().worker == 3
    OPTIONS.cpu.reset()


def test_squeeze_none() -> None:
    @container
    class Options:
        cpu: Provider[int] = Static(5)

    OPTIONS = Options()

    @inject
    def func1(cpu: Optional[int] = Provide[OPTIONS.cpu]) -> Optional[int]:
        return cpu

    assert func1() == 5
    assert func1(None) is None
    assert func1(1) == 1

    @inject(squeeze_none=True)
    def func2(cpu: Optional[int] = Provide[OPTIONS.cpu]) -> Optional[int]:
        return cpu

    assert func2() == 5
    assert func2(None) == 5
    assert func2(1) == 1


def test_memoized_callable() -> None:
    @container
    class Options:
        port = SingletonFactory(lambda: random.randint(1, 65535))

    OPTIONS = Options()

    @inject
    def func(port: int = Provide[OPTIONS.port]) -> int:
        return port

    first_value = func()
    assert func() == first_value


def test_config() -> None:
    @container
    class Options:
        worker_config = Configuration()

    OPTIONS = Options()

    @inject
    def func(c: int = Provide[OPTIONS.worker_config.b.c]) -> int:
        return c

    OPTIONS.worker_config.set(dict())

    assert func(0) == 0

    OPTIONS.worker_config.b.c.set(2)
    assert func() == 2

    OPTIONS.worker_config.set({"a": 1, "b": {"c": 1}})
    assert func() == 1


def test_complex_config() -> None:
    @container
    class Options:
        config = Configuration()
        default_remote = config.remotes[config.default_remote]
        default_local = config.locals[0]

    OPTIONS = Options()
    OPTIONS.config.set(
        {
            "remotes": {
                "a": {"workers": 1},
                "b": {"workers": 2},
                "c": {"workers": 3},
                "d": {"workers": 4},
            },
            "default_remote": "a",
            "locals": ["a", "b"],
        }
    )

    assert OPTIONS.default_remote.workers.get() == 1
    OPTIONS.config.default_remote.set("b")
    assert OPTIONS.default_remote.workers.get() == 2

    assert OPTIONS.config.remotes["c"].workers.get() == 3
    assert OPTIONS.default_local.get() == "a"


def test_config_callable() -> None:
    @container
    class Options:
        worker_config = Configuration()
        worker_instance: Provider[Dict[str, int]] = Factory(
            lambda w: {"c": w}, worker_config.b.c
        )

    OPTIONS = Options()

    @inject
    def func(c: Dict[str, int] = Provide[OPTIONS.worker_instance]) -> Dict[str, int]:
        return c

    assert func({"c": 0}) == {"c": 0}

    OPTIONS.worker_config.set({"a": 1, "b": dict(c=1)})
    assert func() == {"c": 1}

    OPTIONS.worker_config.b.c.set(2)
    assert func() == {"c": 2}


def test_config_fallback() -> None:
    @container
    class Options:
        worker_config = Configuration(fallback=None)

    OPTIONS = Options()

    @inject
    def func(c: int = Provide[OPTIONS.worker_config.b.c]) -> int:
        return c

    assert func() is None


def singleton_dummy_func() -> None:
    pass


def thread_local_singleton_dummy_func() -> None:
    pass


class TestSingletonFactories(TestCase):
    def test_single_thread(self) -> None:
        @container
        class Options:
            config = Configuration()

            @SingletonFactory
            @staticmethod
            def metrics(
                address: str = Provide[config.address], port: int = Provide[config.port]
            ) -> Tuple[str, int]:
                singleton_dummy_func()
                return address, port

        OPTIONS = Options()

        @container
        class Runtime:
            @SingletonFactory
            @staticmethod
            def metrics(
                address: str = Provide[OPTIONS.config.address],
                port: int = Provide[OPTIONS.config.port],
            ) -> Tuple[str, int]:
                singleton_dummy_func()
                return address, port

        RUNTIME = Runtime()

        OPTIONS.config.set(dict(address="a.com", port=100))

        with patch('tests.test_common.singleton_dummy_func') as dummy_func:
            self.assertEqual(OPTIONS.metrics.get(), ("a.com", 100))
            self.assertEqual(dummy_func.call_count, 1)
            self.assertEqual(OPTIONS.metrics.get(), ("a.com", 100))
            self.assertEqual(dummy_func.call_count, 1)

            self.assertEqual(RUNTIME.metrics.get(), ("a.com", 100))
            self.assertEqual(dummy_func.call_count, 2)
            self.assertEqual(RUNTIME.metrics.get(), ("a.com", 100))
            self.assertEqual(dummy_func.call_count, 2)

    def test_multi_thread(self) -> None:
        @container
        class Options:
            config = Configuration()

            @SingletonFactory
            @staticmethod
            def metrics(
                    address: str = Provide[config.address], port: int = Provide[config.port]
            ) -> Tuple[str, int]:
                singleton_dummy_func()
                return address, port

            @ThreadLocalSingletonFactory
            @staticmethod
            def thread_local_metrics(
                    address: str = Provide[config.address], port: int = Provide[config.port]
            ) -> Tuple[str, int]:
                thread_local_singleton_dummy_func()
                return address, port

        OPTIONS = Options()

        OPTIONS.config.set(dict(address="a.com", port=100))

        with patch('tests.test_common.singleton_dummy_func') as dummy_func:
            thread = ThreadWithReturnValue(target=OPTIONS.metrics.get)
            thread.start()
            self.assertEqual(thread.join(), ("a.com", 100))
            self.assertEqual(dummy_func.call_count, 1)

            thread = ThreadWithReturnValue(target=OPTIONS.metrics.get)
            thread.start()
            self.assertEqual(thread.join(), ("a.com", 100))
            self.assertEqual(dummy_func.call_count, 1)

        with patch('tests.test_common.thread_local_singleton_dummy_func') as dummy_func:
            thread = ThreadWithReturnValue(target=lambda: (OPTIONS.thread_local_metrics.get(),
                                                           OPTIONS.thread_local_metrics.get()))
            thread.start()
            self.assertEqual(thread.join(), (("a.com", 100), ("a.com", 100)))
            self.assertEqual(dummy_func.call_count, 1)

            thread = ThreadWithReturnValue(target=OPTIONS.thread_local_metrics.get)
            thread.start()
            self.assertEqual(thread.join(), ("a.com", 100))
            self.assertEqual(dummy_func.call_count, 2)
