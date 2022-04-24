from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
import difflib
from functools import reduce
import itertools as it
from dataclasses import dataclass
import json
import logging
import pathlib
import re
from types import FunctionType
from bs4 import BeautifulSoup
from typing import Any, AnyStr, Coroutine, Iterable, Iterator, List, Generator, Sequence, TypeVar

DATA_DIR = pathlib.Path("./bot_data_stuff").resolve()


FORMAT = "%(levelname)s %(asctime)s - %(message)s"
logging.basicConfig(
    filename=fr"{DATA_DIR}/logs.log",
    level=logging.DEBUG,
    format=FORMAT,
    filemode="w")
logger = logging.getLogger()

REQUIRED_DATE_FORMAT = r"%A %B %d %Y"

NOT_STRING = TypeVar("NOT_STRING", list, dict, set, tuple)


def file_handler(relative_path: pathlib.Path | None = None):
    def read_write_handler(file: str, mode="r", text: str | bytes | None = None):
        try:
            if relative_path:
                file = str(relative_path.joinpath(file).resolve())
            elif file is None:
                raise UnexpectedBehaviourError(
                    "expected a file argument", file_handler)

            def _read_file():
                with open(file) as f:
                    res = f.read()
                return res

            def _write_to_file():
                with open(file, mode) as f:
                    f.write(text)
            mode_dict = {"r": _read_file,
                         "w": _write_to_file, "x": _write_to_file, "wb" : _write_to_file}
            return mode_dict[mode]()
        except KeyError:
            raise NotImplementedError(
                "This function only accepts reading and writing modes as of now.")
    return read_write_handler

IO_DATA_DIR = file_handler(DATA_DIR)


@dataclass
class Announcement:
    title: str
    message: str
    time_created: str
    subject = ""
    subject_code = ""
    subject_type = None
    deadline = None
    links = None
    time_delta = None


@dataclass
class Assignment:
    subject: str
    assignment_link: str
    reference_material_link = None
    deadline = None
    submission_link = None


class UnexpectedBehaviourError(Exception):
    """
    A custom error class to show which function failed at runtime.
    """

    @staticmethod
    def color_message(message):
        return f"\x1B[38;5;214m{message}\x1b[0m"

    def __init__(self, message, custom_object) -> None:
        self.message = self.color_message(
            f" function : {custom_object.__name__} failed ; error message : {message}")
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class WebsiteMeta:
    file = IO_DATA_DIR("creds.txt")
    file = file.split("\n")
    username, password, api_key, public_context, testing_chat_context = file


class NullValueError(Exception):
    def __init__(self, message=None, *args: Iterable[Any]) -> None:
        self.args = args
        default_message = "\n".join(
            f"{name} -> {value}" for name, value in self.args)
        self.message = bool_return(message, default=default_message)
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


def iterate_over_iterable(T: Iterable):
    for i in T:
        print(i)




def flattening_iterator(*args: Iterable[Any]) -> Generator[Any, None, None]:
    for i in args:
        try:
            yield from i
        
        except TypeError:
            yield i


def repeat(obj: Any, n: int):
    for _ in range(n):
        yield obj


def func_chainer(funcs: tuple[FunctionType], *args: Iterable[Any]) -> Any:
    # chain a bunch of functions, assuming they all have the same argument(s).
    try:
        funcs[0]
    except TypeError:
        raise UnexpectedBehaviourError(
            "Need more than one function to chain", func_chainer)
    result = args[0]

    def caller(func: FunctionType, *function_args):
        return func(*function_args)
    for i in funcs:
        result = caller(i, result)

    return result


def get_sequence_or_item(sequence: Sequence):
    if sequence:
        is_item = len(sequence) == 1
        if is_item:
            return sequence[0]
        return sequence


def string_builder(strings: Iterable, prefixes: Iterable,
                   separator: str = "\n") -> str:
    """
    Builds a string incrementally until it reaches a breakpoint (a field is missing)
    """
    def built_strings():
        for string, prefix in zip(strings, prefixes):
            if string and prefix:
                yield f"{prefix} : {string}"
    return separator.join(filter(None, built_strings()))


def not_singleton(T: Iterable):
    if not hasattr(T, "__iter__"):
        return False
    iterator = iter(T)
    _, second = (next(iterator, None), next(iterator, None))
    if not second:
        return False
    return True


def safe_next(iterator_or_gen: Iterator | Generator):
        return next(iterator_or_gen, None)


def safe_next_chaining(iterator_or_gen, attr):
    return null_safe_chaining(safe_next(iterator_or_gen), attr)


def value_verifier(func):

    def wrapper(*args):
        value = None
        if all(args):
            value = func(args)
        return value
    return wrapper


def my_format(item, description=None, level=logging.info):
    if description is not None:
        return level(f"{description}: {item}")
    return level(f"{item}")


def humanize_date(dt: datetime) -> str:
    return dt.strftime(REQUIRED_DATE_FORMAT)


def is_similar(first, second, ratio):
    return difflib.SequenceMatcher(None, first, second).quick_ratio() >= ratio


def flatten_iter(T: Iterable, out_iter=tuple) -> Iterable:
    generator = flattening_iterator(T)
    if not out_iter:
        return generator
    return out_iter(generator)


def gen_exec(gen):
    """
    Executes a collection of functions on demand
    because using a list comprehension takes up memory unnecessarily, so a generator is a better choice.
    """
    for i in gen:
        pass


def clean_iter(T: Iterable, out_iter=list):
    cleaned: filter = filter(None, T)
    if out_iter is None:
        return cleaned
    return out_iter(cleaned)


def combine(*iterables: Iterable, out_iter=tuple) -> Iterable:
    return flatten_iter(it.chain(iterables), out_iter=out_iter)


def has_required_format(collection: tuple[datetime, str]) -> bool:
    def abbreviate(x): return x[:3]
    DAYS, MONTHS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"), ("January",
                                                                                                    "February", "March", "April", "June", "July", "August", "September", "October", "November", "December")
    day_abbr, mon_abbr = (map(abbreviate, i) for i in (DAYS, MONTHS))
    _, string = collection
    DATE_WORDS = combine(DAYS, MONTHS, day_abbr, mon_abbr)
    cond = re.search("|".join(DATE_WORDS), string, re.IGNORECASE)
    return bool(cond)


def bool_return(thing, default=None):
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
        raise UnexpectedBehaviourError(
            "Invalid null safety mode specified", null_safe)

    if none_args:
        raise UnexpectedBehaviourError(f"None found in {args}", null_safe)


def null_safe_chaining(_object, attribute, default=None):
    try:
        return getattr(_object, attribute)

    except AttributeError:
        return default


def coerce_to_none(*args):
    if args:
        for arg in args:
            yield bool_return(arg)


def replace_substrings(substr_tuple_iter, text):
    if hasattr(substr_tuple_iter, "__iter__"):
        result = reduce(lambda s, v: s.replace(*v), substr_tuple_iter, text)
        return result


def matches_attribute(T, attr, value, get_back=False):
    for i in T:
        if getattr(i, attr) == value:
            return i if get_back else T
    return False


def pad_iter(iterable: Iterable, items: Any, amount=None) -> tuple:
    padding = [items] * amount if amount else items
    if not hasattr(iterable, "__iter__") or isinstance(iterable, str):
        iterable = (iterable,)
    iterable = iter(iterable)

    def _gen():
        for i in padding:
            yield next(iterable or i, i)

    return tuple(_gen())


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


def checker_factory(lower: int, upper: int):
    def _inner(item):
        try:
            if lower <= item <= upper:
                return True
            return False
        except TypeError:
            return False
    return _inner


def map_aliases(name: str):
    if "_" in name:
        aliases: tuple[str, ...] = (name, name.split("_")[1], chr(
            min(ord(name.split("_")[1][0]), ord(name[0]))))
    else:
        aliases = (name, name[0])

    return {alias: name for alias in aliases}


def css_selector(html: str, selector="", value=None):
    soup = BeautifulSoup(html, "lxml").select(selector)
    soup = soup[0][value] if value else soup
    return soup


def url_encode(vals):
    vals = list(zip(vals, vals.values()))
    for i, j in enumerate(vals):
        vals[i] = "=".join(j)
    return "&".join(vals)


def add_cookies_to_header(header: dict, cookies_dict: dict) -> dict:
    moodle_session, bnes_moodle_session = tuple(cookies_dict.get(
        i, None) for i in ('MoodleSession', 'BNES_MoodleSession'))
    if moodle_session and bnes_moodle_session:
        return insert_into_dict(header, 10, ("Cookie",
                                             fr"MoodleSession={moodle_session}; BNES_MoodleSession={bnes_moodle_session}"))
    else:
        raise NullValueError(("moodle_session", moodle_session),
                             ("bnes_moodle_session", bnes_moodle_session))


def run(x: Coroutine): return asyncio.run(x)


def soup_bowl(html): return BeautifulSoup(html, "lxml")



def links_and_meetings_wrapper() -> dict[str, list[str]]:
    return json.loads(IO_DATA_DIR("links_and_meetings.json"))


def notifications_wrapper() -> List[dict]:
    data = IO_DATA_DIR("results.json")
    return json.loads(data)[0]["data"]["notifications"]


def courses_wrapper() -> List[dict]:
    return json.loads(IO_DATA_DIR("courses.json"))[0]["data"]["courses"]

def mappings_wrapper() -> dict[str,str]:
    return json.loads(IO_DATA_DIR("mappings.json"))

def insert_into_dict(dictionary, index, pair) -> dict:
    keys, values = list(dictionary.keys()), list(dictionary.values())
    keys.insert(index, pair[0])
    values.insert(index, pair[1])
    dictionary = dict(zip(keys, values))
    return dictionary


def autocorrect(container: Iterable, msg: str, ratio=0.7):
    msg = msg.lower()
    corrected = next(
        filter(lambda x: is_similar(msg, x, ratio), container), None)
    return corrected
