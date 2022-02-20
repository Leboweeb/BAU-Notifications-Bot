import asyncio
import difflib
from functools import reduce
import itertools as it
from dataclasses import dataclass
import json
import logging
from bs4 import BeautifulSoup
from typing import Coroutine, Iterable, List

FORMAT = "%(levelname)s %(asctime)s - %(message)s"
logging.basicConfig(
    filename="logs.log",
    level=logging.DEBUG,
    format=FORMAT,
    filemode="w")
logger = logging.getLogger()


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
    timedelta = None


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

    def __init__(self, message, custom_object) -> None:
        self.message = self.failed_function_hook(message, custom_object)
        super().__init__(message=self.message)

    def failed_function_hook(self, message, custom_object):
        if custom_object:
            self.message = f" function : {custom_object.__name__} failed \n message : {message}"


class WebsiteMeta:
    file = file_handler("creds.txt")
    file = file.split("\n")
    username, password, api_key, public_context, testing_chat_context = file
    blacklist = {}


class NullValueError(Exception):
    def __init__(self, message=None, *args: List[tuple]) -> None:
        self.args = args
        default_message = "\n".join(
            f"{name} -> {value}" for name, value in self.args)
        self.message = bool_return(message, default=default_message)
        super().__init__(message=self.message)


def matches(T, item) -> bool:
    for i in T:
        if i == item:
            return True


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


def is_similar(first, second, ratio):
    return difflib.SequenceMatcher(None, first, second).quick_ratio() >= ratio


def flatten_iter(T, out_iter=tuple) -> Iterable:
    try:
        if out_iter:
            return out_iter(it.chain.from_iterable(T))
        elif out_iter is None:
            return it.chain.from_iterable(T)
    except TypeError:
        return T


def gen_exec(gen):
    """
    Executes a collection of functions on demand
    because using a list comprehension takes up memory unnecessarily, so a generator is a better choice.
    """
    for i in gen:
        pass


def clean_iter(T: Iterable, out_iter=list):
    cleaned = filter(None, T)
    if out_iter is None:
        return cleaned
    return out_iter(cleaned)


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
        raise UnexpectedBehaviourError("Invalid null safety mode specified")

    if none_args:
        raise UnexpectedBehaviourError(f"None found in {args}")


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


def pad_iter(iterable: Iterable, items: Iterable, amount=None) -> tuple:
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


def map_aliases(name: str):
    if "_" in name:
        aliases = (name, name.split("_")[1], chr(
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


def load_json_file(file): return json.load(open(file))


def notifications_wrapper() -> List[dict]:
    data = load_json_file("results.json")[0]["data"]["notifications"]
    return data


def courses_wrapper() -> List[dict]:
    return load_json_file("courses.json")[0]["data"]["courses"]


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
