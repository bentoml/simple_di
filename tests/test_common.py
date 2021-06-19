'''
common tests
'''
import random
from typing import Optional

from simple_di import Container, Provide, Provider, inject
from simple_di.providers import Callable, Configuration, MemoizedCallable, Static

# Usage


def test_inject_function():
    class Options(Container):
        cpu: Provider[int] = Static(2)
        worker: Provider[int] = Callable(lambda c: 2 * c + 1, c=cpu)

    @inject
    def func(worker: int = Provide[Options.worker]):
        return worker

    assert func() == 5
    assert func(1) == 1

    Options.worker.set(2)
    assert func() == 2

    Options.worker.reset()
    assert func() == 5

    Options.cpu.set(1)
    assert func() == 3
    Options.cpu.reset()


def test_inject_method():
    class Options(Container):
        cpu: Provider[int] = Static(2)
        worker: Provider[int] = Callable(lambda c: 2 * c + 1, c=cpu)

    class A:
        @inject
        def __init__(self, worker: int = Provide[Options.worker]):
            self.worker = worker

        @classmethod
        @inject
        def create(cls, worker: int = Provide[Options.worker]):
            return cls(worker)

    assert A().worker == A.create().worker == 5
    assert A(1).worker == A.create(1).worker == 1

    Options.worker.set(2)
    assert A().worker == A.create().worker == 2

    Options.worker.reset()
    assert A().worker == A.create().worker == 5

    Options.cpu.set(1)
    assert A().worker == A.create().worker == 3
    Options.cpu.reset()


def test_respect_none():
    class Options(Container):
        cpu: Provider[int] = Static(5)

    @inject
    def func1(cpu: Optional[int] = Provide[Options.cpu]):
        return cpu

    assert func1() == 5
    assert func1(None) is None
    assert func1(1) == 1

    @inject(respect_none=False)
    def func2(cpu: Optional[int] = Provide[Options.cpu]):
        return cpu

    assert func2() == 5
    assert func2(None) == 5
    assert func2(1) == 1


def test_memoized_callable():
    class Options(Container):
        port = MemoizedCallable(lambda: random.randint(1, 65535))

    @inject
    def func(port: int = Provide[Options.port]):
        return port

    first_value = func()
    assert func() == first_value


def test_config():
    class Options(Container):
        worker_config = Configuration()

    @inject
    def func(c: int = Provide[Options.worker_config.b.c]):
        return c

    assert func(0) == 0

    Options.worker_config.set(dict(a=1, b=dict(c=1)))
    assert func() == 1

    Options.worker_config.b.c.set(2)
    assert func() == 2


def test_config_callable():
    class Options(Container):
        worker_config = Configuration()
        worker_instance: Provider = Callable(lambda w: {"c": w}, worker_config.b.c)

    @inject
    def func(c: dict = Provide[Options.worker_instance]):
        return c

    assert func({"c": 0}) == {"c": 0}

    Options.worker_config.set(dict(a=1, b=dict(c=1)))
    assert func() == {"c": 1}

    Options.worker_config.b.c.set(2)
    assert func() == {"c": 2}


def test_config_fallback():
    class Options(Container):
        worker_config = Configuration(fallback=None)

    @inject
    def func(c: int = Provide[Options.worker_config.b.c]):
        return c

    assert func() is None
