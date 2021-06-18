'''
common tests
'''
from simple_di import Container, Provide, Provider, inject
from simple_di.providers import Callable, Configuration, Static

# Usage


def test_inject_function():
    class Options(Container):
        cpu: Provider[int] = Static(2)
        worker: Provider[int] = Callable(lambda c: 2 * c + 1, c=cpu)

    @inject
    def func(arg, worker: int = Provide[Options.worker]):
        assert arg
        return worker

    assert func(1) == 5
    assert func(1, 1) == 1

    Options.worker.set(2)
    assert func(1) == 2

    Options.worker.reset()
    assert func(1) == 5

    Options.cpu.set(1)
    assert func(1) == 3
    Options.cpu.reset()


def test_inject_method():
    class Options(Container):
        cpu: Provider[int] = Static(2)
        worker: Provider[int] = Callable(lambda c: 2 * c + 1, c=cpu)

    class A:
        @inject
        def __init__(self, worker: int = Provide[Options.worker]):
            self.worker = worker

    assert A().worker == 5
    assert A(1).worker == 1

    Options.worker.set(2)
    assert A().worker == 2

    Options.worker.reset()
    assert A().worker == 5

    Options.cpu.set(1)
    assert A().worker == 3
    Options.cpu.reset()


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
