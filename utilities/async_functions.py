from dataclasses import dataclass
import logging
import itertools as it
from datetime import datetime
import asyncio
import re
from typing import AsyncGenerator, Generator, List, Tuple
import httpx
import datefinder
from utilities.common import REQUIRED_DATE_FORMAT, Announcement, Assignment, WebsiteMeta, add_cookies_to_header, clean_iter, coerce_to_none, courses_wrapper, css_selector, has_required_format, mappings_wrapper, not_singleton, my_format, get_sequence_or_item, safe_next, soup_bowl, url_encode


@dataclass(frozen=True)
class Course:
    name: str
    link: str


async def collect_tasks(pred=None, collection=None):
    if all((pred, collection)):
        result = await asyncio.gather(*[asyncio.ensure_future(pred(item)) for item in collection])
    else:
        result = await asyncio.gather(*[asyncio.ensure_future(item) for item in collection])

    return result


async def async_filter(async_pred, iterable) -> AsyncGenerator:
    for item in iterable:
        should_yield = await async_pred(item)
        if should_yield:
            yield item


async def relative_time_dt(gen : Generator) -> int:
    found_explicit_date, found_implicit_date = False, False
    for i in gen:
        pass
    return 0

        

async def get_data(dicts: list[dict]) -> List[Announcement]:
    objects = [i for i in dicts]
    mappings = mappings_wrapper()
    keys = ("subject",
            "fullmessage", "timecreatedpretty")
    CURRENT_DAY = datetime.now().day
    non_exam_types, exam_types = (
        "lab", "project", "session"), ("quiz", "test", "exam", "grades", "midterm")

    async def _make_announcement(obj):
        announcement = Announcement(
            *[obj[key] for key in keys])
        return announcement

    objects = await collect_tasks(_make_announcement, objects)

    async def _attr_worker(announcement: Announcement):
        try:
            announcement.subject_code, announcement.subject_type = announcement.title.split(
                ":")
        except ValueError:
            announcement.subject_code, announcement.subject_type = announcement.title.split(":")[
                0], None
        announcement.subject = mappings[announcement.subject_code]
        # I love the union syntax so much, I'm legit crying. WHY WAS IT SO
        # HARD IN PYTHON 2? WHYYYYYY ??
        type_dict = {name: "exam" for name in exam_types} | {
            name: name for name in non_exam_types}

        split = announcement.message.split(
            "---------------------------------------------------------------------")
        announcement.message = split[1]
        try:
            if announcement.subject_type:
                announcement.subject_type = re.findall("|".join(it.chain(
                    non_exam_types, exam_types)), announcement.subject_type.lower(), re.MULTILINE)
                temp = get_sequence_or_item(announcement.subject_type)
                announcement.subject_type = temp
                if not_singleton(announcement.subject_type) is False:
                    announcement.subject_type = type_dict[temp]

        except (KeyError, IndexError):
            announcement.subject_type = None

        try:
            fuzzy_date = safe_next(
                filter(has_required_format,  datefinder.find_dates(announcement.message, True)))
        except IndexError:
            fuzzy_date = None
        if fuzzy_date:
            fuzzy_date = fuzzy_date[0]
            announcement.deadline = fuzzy_date.strftime(REQUIRED_DATE_FORMAT)
            if fuzzy_date.tzinfo:
                fuzzy_date = next(
                    datefinder.find_dates(
                        announcement.message.replace(
                            re.findall(
                                r"\d+:\d+",
                                announcement.message)[1],
                            "")))
            dt = (fuzzy_date - datetime.now()).days
            announcement.time_delta = dt

        async def _course_links(Notification: Announcement):
            """
            An internal function to return zoom meeting links in each announcement object
            """
            link_regex = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"

            async def meetings_filter(link): return re.findall(
                "teams|zoom|meeting", link, flags=re.IGNORECASE) is not None
            links = re.findall(link_regex, Notification.message, re.MULTILINE)
            links = [i async for i in
                     async_filter(meetings_filter, links)]
            Notification.links = links if links else None

        await _course_links(announcement)
    await collect_tasks(_attr_worker, objects)
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
