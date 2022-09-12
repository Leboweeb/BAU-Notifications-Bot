from dataclasses import dataclass
import logging
from datetime import datetime
import asyncio
import re
from typing import AsyncGenerator, List, Optional, Tuple
import httpx
import datefinder
from utilities.common import Announcement, Assignment, WebsiteMeta, add_cookies_to_header, clean_iter, coerce_to_none, courses_wrapper, css_selector, flattening_iterator, get_group, my_format, null_safe_index, safe_next, soup_bowl, url_encode, to_natural_str
from utilities.semester_utils import find_week_of_datetime
from utilities.time_parsing_lib import RelativeDate


@dataclass(frozen=True)
class Course:
    name: str
    link: str


FIND_ABSOLUTE_DATE = r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(\s\d+)?(\s(January|February|March|April|June|July|August|September|October|November|December))?(\s\d+)?"
abs_re = re.compile(FIND_ABSOLUTE_DATE, re.MULTILINE)


def found_explicit_date(collection: tuple[datetime, str]) -> bool:
    def abbreviate(x): return x[:3]
    DAYS, MONTHS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"), ("January",
                                                                                                    "February", "March", "April", "June", "July", "August", "September", "October", "November", "December")
    day_abbr, mon_abbr = (map(abbreviate, i) for i in (DAYS, MONTHS))
    _, string = collection
    DATE_WORDS = tuple(flattening_iterator(DAYS, MONTHS, day_abbr, mon_abbr))
    cond = re.search("|".join(DATE_WORDS), string, re.IGNORECASE)
    return bool(cond)


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
        explicit_date: Optional[datetime]
        DELETE_TZINFO_REGEX = re.compile(r"\d+:\d+", re.MULTILINE)
        finder = datefinder.DateFinder(
            base_date=announcement.date_created, first="day")
        explicit_date = null_safe_index(safe_next(
            filter(found_explicit_date, finder.find_dates(DELETE_TZINFO_REGEX.sub("", announcement.message), source=True))), 0)
        now = datetime.now()
        def subtract_from_today(ref: datetime): return (ref - now).days
        announcement.time_delta, announcement.deadline = None, None
        if "exam" in announcement.subject_type or "project" in announcement.subject_type:
            if explicit_date:
                dt = subtract_from_today(explicit_date)
                announcement.deadline = to_natural_str(explicit_date)
                announcement.time_delta = dt
                # If one or more explicit date is found, bypass implicit date checking and get the minimum
                # since the minumum date is usually always the first result, getting the minimum is not needed
            else:
                # if no explicit date is found, generate a relative date from the time created and subtract it from now
                make_relative_date = RelativeDate(
                    string=announcement.message, anchor=announcement.date_created)
                _dt = safe_next(make_relative_date.generate_results())
                if _dt:
                    _date = subtract_from_today(_dt)
                    announcement.time_delta = _date
                    announcement.deadline = to_natural_str(_dt)
                else:
                    week_number = get_group(
                        re.search("week\s+\d+", announcement.message.lower(), re.MULTILINE))
                    announcement.time_delta, announcement.deadline = (subtract_from_today((_week := find_week_of_datetime(
                        week=int(re.split("\s+", week_number)[1])))), to_natural_str(_week)) if week_number else None, None
    await collect_tasks(_time_delta_worker, objects)
    return objects


def authenticate(func):
    """
Authenticates an http request to the moodle website before attempting to scrape data
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
        for i in T:
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
