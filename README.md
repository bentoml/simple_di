# simple-di

A simple dependency injection library

- [Install](#install)
- [Usage](#usage)
- [API](#api)

[![Python 3.6](https://github.com/bojiang/simple_di/workflows/Python%203.6/badge.svg)](https://github.com/bojiang/simple_di/actions/workflows/py36.yml)
[![Python 3.7](https://github.com/bojiang/simple_di/workflows/Python%203.7/badge.svg)](https://github.com/bojiang/simple_di/actions/workflows/py37.yml)
[![Python 3.8](https://github.com/bojiang/simple_di/workflows/Python%203.8/badge.svg)](https://github.com/bojiang/simple_di/actions/workflows/py38.yml)
[![Python 3.9](https://github.com/bojiang/simple_di/workflows/Python%203.9/badge.svg)](https://github.com/bojiang/simple_di/actions/workflows/py39.yml)

## Install

``` bash
    pip install simple_di
```

## Usage

Examples:

```python
    from simple_di import inject, Provide, Provider
    from simple_di.providers import Static, Callable, Configuration


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
```


## API

- [inject](#inject)
- [Provide](#Provide)
- [providers](#providers)
  - [Static](#Static)
  - [Callable](#Callable)
  - [Configuration](#Configuration)

## Type annotation supported


### inject

Inject values into providers in function/method arguments.