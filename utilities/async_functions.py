from dataclasses import dataclass
import logging
import itertools as it
from datetime import datetime
import asyncio
import re
from typing import AsyncGenerator, List, Tuple
import httpx
import datefinder
from utilities.common import Announcement, Assignment, WebsiteMeta, add_cookies_to_header, clean_iter, coerce_to_none, courses_wrapper, css_selector, get_regex_group, has_required_format, my_format, safe_next, soup_bowl, url_encode
from utilities.time_parsing_lib import to_natural_str


@dataclass(frozen=True)
class Course:
    name: str
    link: str


async def collect_tasks(pred=None, collection=None):
    if all((pred, collection)):
        result = await asyncio.gather(*(asyncio.ensure_future(pred(item)) for item in collection))
    else:
        result = await asyncio.gather(*(asyncio.ensure_future(item) for item in collection))

    return result


async def async_filter(async_pred, iterable) -> AsyncGenerator:
    for item in iterable:
        should_yield = await async_pred(item)
        if should_yield:
            yield item


async def get_data(dicts: list[dict]):
    objects = [i for i in dicts]
    keys = ("subject",
            "fullmessage", "timecreated")

    async def _make_announcement(obj):
        announcement = Announcement(
            *[obj[key] for key in keys])
        return announcement

    objects = await collect_tasks(_make_announcement, objects)

    async def _time_delta_worker(announcement: Announcement):
        fuzzy_date : datetime
        DELETE_TZINFO_REGEX = re.compile(r"\d+:\d+", re.MULTILINE)
        fuzzy_date  , _ = safe_next(
            filter(has_required_format,  datefinder.find_dates(announcement.message, source=True)))
        announcement.deadline = to_natural_str(fuzzy_date)
        if fuzzy_date.tzinfo:
            fuzzy_date = next(
                datefinder.find_dates(
                    announcement.message.replace(str(get_regex_group(compiled=DELETE_TZINFO_REGEX)))))
            # TODO : Add more robust announcement object timedelta api
            dt = (fuzzy_date - datetime.fromtimestamp(announcement.time_created)).days
            announcement.time_delta = dt
    await collect_tasks(_time_delta_worker, objects)
    return objects


def authenticate(func):
    """
Authenticates an http request to the uni website before attempting to scrape data
useful for making arbitrary requests to it.

:returns: the session cookies and the session itself.
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
            username, password = WebsiteMeta.username, WebsiteMeta.password
            encoded = url_encode(
                {"username": username, "password": password,
                 "execution": fr"{execution}", "_eventId": "submit",
                 "geolocation": ""})
            await Client.post(LOGIN_URL, data=encoded,
                              headers=login_headers, params=querystring)
            cookies = Client.cookies
            my_format(cookies, "Cookies in async api")
            await func(cookies, Client)
    return wrapper_func


async def prep_courses():
    courses = courses_wrapper()

    async def course_generator(T: List[dict[str:str]]):
        def testing_predicate(
            i): return 0 < i["progress"] < 100 or i["fullname"] == "Electricity and Magnetism"
        for i in T:
            if testing_predicate(i):
                yield Course(i["fullname"], i["viewurl"])
    return {i async for i in course_generator(courses)}


@ authenticate
async def find_assignments(cookies, Client: httpx.AsyncClient) -> Tuple[Assignment]:
    ASSIGNMENT_SELECTOR = r'li[class="activity assign modtype_assign "]'

    courses = await prep_courses()
    shared_header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.7113.93 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/jxl,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://icas.bau.edu.lb:8443",
        "DNT": "1",
        "Connection": "keep-alive",
        "Referer": r"https://moodle.bau.edu.lb/my/",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Sec-GPC": "1"
    }
    shared_header = add_cookies_to_header(shared_header, cookies)

    async def goto_link(link):
        r = await Client.get(
            link, headers=shared_header, cookies=cookies)
        level = logging.warning if r.status_code != 200 else logging.info
        my_format(r.status_code, "Status code", level)

    async def create_assignments(course: Course):
        r = await goto_link(course.link)
        links = clean_iter(soup_bowl(r.text).select(
            ASSIGNMENT_SELECTOR), out_iter=tuple)
        for link in links:
            return Assignment(course.name, link)

    async def find_from_link(link, assignment: Assignment):
        """
        selectors for each attribute:

        reference_material : div > h2
        deadline : div[class='submissionstatustable'] tr[class='']
        submission_link : div[id='intro'] > div > p >a  (If any)
        """

        r = await Client.get(link, headers=shared_header, cookies=cookies)
        bowl = soup_bowl(r.text)
        refrence_material, submission_link = tuple(map(
            bowl.select_one, ("div div > h2", "div[id='intro'] > div > p >a")))
        submission_table = bowl.select(
            "[class='submissionstatustable'] tr[class=']")

        async def find_deadline(table_list):
            async def _search_children(tag, query):
                for child in set(tag.children):
                    if query.lower() in child.text.lower():
                        return tag
            if table_list:
                deadline = (_search_children(i, "time remaining")
                            for i in table_list)
                deadline = collect_tasks(collection=deadline)
                deadline = next(filter(None, deadline), None).select_one("td")
                return deadline.text.strip()
        deadline = await find_deadline(submission_table)
        refrence_material, submission_link, deadline = tuple(
            coerce_to_none(refrence_material, submission_link, deadline))
        for i, j in zip(("submission_link", "refrence_material", "deadline"), (refrence_material, submission_link, deadline)):
            setattr(assignment, i, j)

    assignments = await collect_tasks(create_assignments, courses)
    await collect_tasks(find_from_link, assignments)
    return assignments


def all_notifications(res): return asyncio.run(get_data(res))
