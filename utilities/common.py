import asyncio
import difflib
from functools import reduce
import itertools as it
from dataclasses import dataclass
import json
import logging
from typing import Coroutine, Iterable, List

FORMAT = "%(levelname)s %(asctime)s - %(message)s"
logging.basicConfig(
    filename="logs.log",
    level=logging.DEBUG,
    format=FORMAT,
    filemode="w")
logger = logging.getLogger()


def my_format(item, description=None, level=logging.info):
    if description is not None:
        return level(f"{description}: {item}")
    return level(f"{item}")

def file_handler(file, mode="r", text=None, relative=False):
    try:
        if file is not None:
            def _read_file():
                with open(file) as f:
                    res = f.read()
                return res

            def _write_to_file():
                with open(file, mode) as f:
                    f.write(text)
        mode_dict = {"r": _read_file, "w": _write_to_file, "x": _write_to_file}
        return mode_dict[mode]()
    except KeyError:
        raise NotImplementedError(
            "This function only accepts reading and writing modes as of now.")


def is_similar(first, second, ratio):
    return difflib.SequenceMatcher(None, first, second).quick_ratio() >= ratio


def flatten_iter(T, out_iter=tuple) -> Iterable:
    try:
        return out_iter(it.chain.from_iterable(T))
    except TypeError:
        return T

def gen_exec(gen):
    """
    Executes a collection of functions on demand
    because using a list comprehension takes up memory unnecessarily, so a generator is a better choice.
    """
    for i in gen:
        pass


def clean_list(T: Iterable):
    return list(filter(None, T))


def bool_return(thing, condition=None, default=None):
    if condition:
        return thing if condition else default
    return thing if thing else default


def limit(iterable, limit=5):
    def _gen():
        if limit is not None:
            for i in it.islice(iterable, 0, limit):
                yield i

        else:
            yield from iterable

    return list(_gen())


def null_safe(*args: Iterable, mode="list"):
    modes = {"list": lambda it: None in it,
             "dict": lambda it: None in it.values()}
    none_args = False
    try:
        none_args = modes[mode](*args)

    except KeyError:
        raise ValueError("Invalid null safety mode specified")

    if none_args:
        raise ValueError(f"None found in {args}")


def coerce_to_none(*args):
    if args:
        return list(None for arg in args if not arg)


def replace_substrings(substr_tuple_iter, text):
    if hasattr(substr_tuple_iter, "__iter__"):
        result = reduce(lambda s, v: s.replace(*v), substr_tuple_iter, text)
        return result


def bool_return(thing, condition=None, default=None):
    if condition:
        return thing if condition else default
    return thing if thing else default


def infinite_conditional(*args):
    """
    A scalable way to implement callbacks based on many (or even infinite) conditionals, the best way to do this is to declare
    a main (or) container function which has delegates or closures to handle (use a plate object to containerize arguments) calls based on
    their associated condition(s).
    """
    def augmented_all(item):
        try:
            return all(item)
        except TypeError:
            return bool(item)
    if args:
        for arg in args:
            if augmented_all(arg[0:-1]):
                return arg[-1]()

def map_aliases(name: str):
    if "_" in name:
        aliases = (name, name.split("_")[1], chr(
            min(ord(name.split("_")[1][0]), ord(name[0]))))
    else:
        aliases = (name, name[0])

    return {alias: name for alias in aliases}

@dataclass
class Announcement:
    title: str
    message: str
    ID: str
    subject = ""
    subject_code = ""
    subject_type = None
    deadline = None
    links = None
    timedelta = None


def run(x: Coroutine): return asyncio.run(x)

def notifications_wrapper() -> List[dict]:
    res = file_handler("results.json")
    data = json.loads(res)[0]["data"]["notifications"]
    return data
