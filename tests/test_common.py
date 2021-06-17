'''
common tests
'''
from simple_di import Container, Provide, Provider, inject
from simple_di.providers import Callable, Configuration, Static

# Usage


class MetricsOptions(Container):
    pass


class Options(Container):
    cpu: Provider[int] = Static(2)
    worker: Provider[int] = Callable(lambda c: 2 * c + 1, c=cpu)
    worker_config = Configuration()
    worker_instance: Provider = Callable(lambda w: {"c": w}, worker_config.b.c)
    metrics = MetricsOptions


def test_inject_function():
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


def test_config():
    @inject
    def func(c: int = Provide[Options.worker_config.b.c]):
        return c

    Options.worker_config.set(dict(a=1, b=dict(c=1)))
    assert func() == 1
    assert Options.worker_instance.get()["c"] == 1

    Options.worker_config.b.c.set(2)
    assert func() == 2
    assert Options.worker_instance.get()["c"] == 2


def test_inject_method():
    class A:
        @inject
        def __init__(self, worker: int = Provide[Options.worker], **kwargs):
            self.worker = worker
            self.kwargs = kwargs

    assert A().worker == 5
    assert A(1).worker == 1

    Options.worker.set(2)
    assert A().worker == 2

    Options.worker.reset()
    assert A().worker == 5

    Options.cpu.set(1)
    assert A().worker == 3
    Options.cpu.reset()
