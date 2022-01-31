import asyncio
import difflib
from enum import Enum
import html
import logging
import re
import json
import httpx
import datefinder
import itertools as it
from functools import reduce
from bs4 import BeautifulSoup
from datetime import datetime
from typing import AsyncGenerator,Coroutine, Iterable, List
from dataclasses import dataclass
from collections import Counter


current_dir = "/".join(__file__.split("/")[:-1])


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


def notification_message_builder(notification: Announcement,custom_message=None):
        attrs = ("subject", "message", "deadline")
        strings = [getattr(notification, attr)
                for attr in attrs]
        prefixes = (i.capitalize() for i in attrs)
        strings[0] = f"{notification.subject} ({notification.subject_code})"
        if custom_message:
            strings[1] = custom_message

        return f"""
    ---------------------------------------
        {string_builder(strings,prefixes)}
    ---------------------------------------
    
    """


class PostponedHandler:

    def __init__(self, notifications) -> None:
        postponed = ("postponed", "new date", "delayed")
        self.notifications = notifications
        self.postponed_type_notifications = tuple(filter(lambda x: re.findall(
            "|".join(postponed), x.title.lower()), self.notifications))

    def __call__(self):
        return self.find_matching()

    @staticmethod
    def sentence_difference(s1, s2):
        return is_similar(s1, s2, 0.7)

    def get_needed_types(self):
        counts = Counter((i.subject_code for i in self.notifications))
        unneeded = counts.items()
        for i in unneeded:
            if i[1] != 1:
                yield i[0]

    def generate_from_codes(self, t):
        for i in self.notifications:
            if i.subject_code == t.subject_code:
                yield i

    def compare_to_notification(self, postponed_type_notification):
        def possible_duplicate(announcement):
            if announcement.title.lower() == postponed_type_notification.title.lower():
                return False
            return is_similar(announcement.title.lower(),
                              postponed_type_notification.title.lower(), 0.7)

        req = list(filter(possible_duplicate, self.generate_from_codes(
            postponed_type_notification)))

        if req:
            if len(req) > 1:
                req = req[1:]
            gen_exec(setattr(i, "subject_type", None) for i in req)

    def find_matching(self):
        for i in self.postponed_type_notifications:
            self.compare_to_notification(i)
        return self.notifications


FORMAT = "%(levelname)s %(asctime)s - %(message)s"
logging.basicConfig(
    filename="logs.log",
    level=logging.DEBUG,
    format=FORMAT,
    filemode="w")
logger = logging.getLogger()


def run(x: Coroutine): return asyncio.run(x)


def is_similar(first, second, ratio):
    return difflib.SequenceMatcher(None, first, second).quick_ratio() >= ratio


def gen_exec(gen):
    """
    Executes a collection of functions on demand
    because using a list comprehension takes up memory unnecessarily, so a generator is a better choice.
    """
    for i in gen:
        pass


def soup_bowl(html): return BeautifulSoup(html, "lxml")


def my_format(item, description=None, level=logging.info):
    if description != None:
        return level(f"{description}: {item}")
    return level(f"{item}")


def file_handler(file, mode="r", text=None):
    try:
        if file != None:
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


def url_encode(vals):
    vals = list(zip(vals, vals.values()))
    for i, j in enumerate(vals):
        vals[i] = "=".join(j)
    return "&".join(vals)


def insert_into_dict(dictionary, index, pair) -> dict:
    keys, values = list(dictionary.keys()), list(dictionary.values())
    keys.insert(index, pair[0])
    values.insert(index, pair[1])
    dictionary = dict(zip(keys, values))
    return dictionary


def replace_substrings(substr_tuple_iter, text):
    if hasattr(substr_tuple_iter, "__iter__"):
        result = reduce(lambda s, v: s.replace(*v), substr_tuple_iter, text)
        return result


def search_case_insensitive(query: str, text: str):
    query = query.lower()
    found = [(q, f"[{q}]") for q in (
        query, query.capitalize(), query.upper()) if q in text]
    # *v here prevents another loop; semantically equivalent to for item in found: reduce(lambda s,v : s.replace(v), found , text where text is the default in case no results were found )
    result = reduce(lambda s, v: s.replace(*v), found, text)
    if result != text:
        return result


def css_selector(html=None, selector="", value=None):
    soup = BeautifulSoup(html, "lxml").select(selector)
    soup = soup[0][value] if value else soup
    return soup


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


def bool_return(thing, condition=None, default=None):
    if condition:
        return thing if condition else default
    return thing if thing else default


def clean_list(T: Iterable):
    return list(filter(None, T))


def limit(iterable, limit=5):
    def _gen():
        if limit != None:
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


def string_builder(strings: Iterable, prefixes: Iterable, separator: str = "\n") -> str:
    """
    Builds a string incrementally until it reaches a breakpoint (a field is missing)
    """
    def built_strings():
        for string, prefix in zip(strings, prefixes):
            if string and prefix:
                yield f"{prefix} : {string}"
    return separator.join(filter(None, built_strings()))


def hilight_word(string: str, query) -> str:
    if all(string, query):
        words = string.lower().split(" ")
        words[words.index(query)] = f"**{query}**"
        return " ".join(words)


def flatten_iter(T, out_iter=tuple) -> Iterable:
    try:
        return out_iter(it.chain.from_iterable(T))
    except TypeError:
        return T


def authenticate(func):
    """
Authenticates an http request to the uni website before attempting to scrape data
useful for making arbitrary requests to it.
"""

    async def wrapper_func():
        async with httpx.AsyncClient(timeout=None, follow_redirects=True) as Client:
            querystring = {
                "service": "https://moodle.bau.edu.lb/login/index.php"}
            LOGIN_URL = r"https://icas.bau.edu.lb:8443/cas/login?service=https%3A%2F%2Fmoodle.bau.edu.lb%2Flogin%2Findex.php"
            login_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.7113.93 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/jxl,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://icas.bau.edu.lb:8443",
                "DNT": "1",
                "Connection": "keep-alive",
                "Referer": r"https://icas.bau.edu.lb:8443/cas/login?service=https%3A%2F%2Fmoodle.bau.edu.lb%2Flogin%2Findex.php",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Sec-GPC": "1"}
            page = await Client.get(url=LOGIN_URL)
            execution = css_selector(
                page.text, "[name=execution]", "value")
            if (b := file_handler("creds.txt")):
                b = b.split("\n")
                username, password = b[:2]
            encoded = url_encode({"username": username,
                                  "password": password,
                                  "execution": fr"{execution}", "_eventId": "submit",
                                  "geolocation": ""})
            await Client.post(LOGIN_URL, data=encoded,
                              headers=login_headers, params=querystring)

            cookies = [Client.cookies.get(i) for i in (
                'MoodleSession', 'BNES_MoodleSession')]
            my_format(cookies, "Cookies in async api")
            await func(cookies, Client)
    return wrapper_func


def update_links(Announcements: List[Announcement]):
    links_dict = {
        announcement.subject: announcement.links for announcement in Announcements}
    file_handler("links_and_meetings.json", "w", json.dumps(
        links_dict, indent=4)) if links_dict else None


class InputFilters:

    @staticmethod
    def notifications_wrapper() -> List[dict]:
        res = file_handler("results.json")
        data = json.loads(res)[0]["data"]["notifications"]
        return data

    @staticmethod
    def mapping_init():
        with open("mappings.json", "w") as f:
            res = file_handler("courses.json")
            data = json.loads(res)[0]["data"]["courses"]
        data = [i for i in data]
        mappings = {item["shortname"]: html.unescape(
            item["fullname"]) for item in data}
        file_handler("mappings.json", "w", json.dumps(mappings, indent=4))

    @staticmethod
    def lockfile_cleanup(res: dict) -> List[Announcement]:
        important_notifications = InputFilters.hilight(res)
        important_notifications = PostponedHandler(
            important_notifications).find_matching()
        important_notifications = clean_list(
            important_notifications)
        return important_notifications

    @staticmethod
    def hilight(res: dict) -> List[Announcement]:
        objects = asyncio.run(AsyncFunctions.get_data(res))

        def _important_notification(Notification: Announcement):
            if re.findall(r"\blab\b|\btest\b|\bquiz\b|\bfinal\b|\bgrades\b|\bgrade\b|\bmakeup\b|\bincomplete exam\b|\bproject\b", Notification.message.lower(), flags=re.MULTILINE):
                return True
        important_objects = list(filter(_important_notification, objects))
        return important_objects


class AsyncFunctions:
    """
    Special purpose asynchronous functions, because functions here are assumed to be synchronous
    """

    async def collect_tasks(pred=None, collection=None, tasks=None):
        args = (pred, collection, tasks)
        if all(args):
            raise ValueError(
                "Cannot gather tasks based on a predicate and a list of tasks at the same time !")

        elif all((pred, collection)):
            result = await asyncio.gather(*[asyncio.ensure_future(pred(item)) for item in collection])
        else:
            result = await asyncio.gather(*[asyncio.ensure_future(item) for item in collection])

        return result

    async def async_filter(async_pred, iterable) -> AsyncGenerator:
        for item in iterable:
            should_yield = await async_pred(item)
            if should_yield:
                yield item

    async def get_data(dicts: list[dict]) -> List[Announcement]:
        objects = [i for i in dicts]
        mappings = json.loads(file_handler("mappings.json"))
        keys = ("subject",
                "fullmessage", "id")
        non_exam_types, exam_types = (
            "lab", "project"), ("quiz", "test", "exam", "grades")

        async def _make_announcement(obj):
            announcement = Announcement(
                *[obj[key] for key in keys])
            return announcement

        objects = await AsyncFunctions.collect_tasks(_make_announcement, objects)

        async def _attr_worker(announcement: Announcement):
            announcement.subject_code, announcement.subject_type = announcement.title.split(
                ":")
            announcement.subject = mappings[announcement.subject_code]
            # I love the union syntax so much, I'm legit crying. WHY WAS IT SO HARD IN PYTHON 2? WHYYYYYY ??
            type_dict = {name: "exam" for name in exam_types} | {
                name: name for name in non_exam_types}
            try:
                announcement.subject_type = re.findall("|".join(it.chain(
                    non_exam_types, exam_types)), announcement.subject_type.lower(), re.MULTILINE)[0]
                announcement.subject_type = type_dict[announcement.subject_type]

            except (KeyError,IndexError):
                announcement.subject_type = None

            split = announcement.message.split(
                "---------------------------------------------------------------------")
            announcement.message = split[1]

            try:
                fuzzy_date = tuple(
                    datefinder.find_dates(announcement.message))[0]
            except IndexError:
                fuzzy_date = None
            if fuzzy_date:
                announcement.deadline = fuzzy_date.strftime(r"%A %B %d %Y")
                if fuzzy_date.tzinfo:
                    fuzzy_date = next(datefinder.find_dates(announcement.message.replace(
                        re.findall(r"\d+:\d+", announcement.message)[1], "")))
                dt = (fuzzy_date - datetime.now()).days
                announcement.timedelta = dt

            async def _course_links(Notification: Announcement):
                """
                An internal function to return zoom meeting links in each announcement object
                """
                link_regex = "(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
                async def meetings_filter(
                    link): return re.match("teams|zoom|meeting", link, flags=re.IGNORECASE) != None
                links = [i async for i in
                         AsyncFunctions.async_filter(meetings_filter, re.findall(link_regex, Notification.message.lower(), re.MULTILINE))]
                Notification.links = links[0] if links else None

            await _course_links(announcement)
        await AsyncFunctions.collect_tasks(_attr_worker, objects)
        return objects


class TelegramInterface:
    def __init__(self) -> None:
        self.notifications_dict = InputFilters.notifications_wrapper()
        self.notifications = InputFilters.lockfile_cleanup(
            self.notifications_dict)
        self.unfiltered_notifications = run(
            AsyncFunctions.get_data(self.notifications_dict))
        
        self.urgent_notifications_gen = (i for i in self.notifications if i.timedelta and 1 <= i.timedelta <= 7)
        self.update_links_and_meetings()

    def update_links_and_meetings(self):
        notifications = json.dumps(
            {announcement.subject: announcement.links for announcement in run(AsyncFunctions.get_data(self.notifications_dict)) if announcement.links})
        file_handler("links_and_meetings.json", "w", notifications)
