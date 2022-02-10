import asyncio
import re
import datefinder
import itertools as it
from datetime import datetime
from utilities.common import Announcement, file_handler, json
from typing import AsyncGenerator, List


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
            "fullmessage", "timecreatedpretty")

    non_exam_types, exam_types = (
        "lab", "project","session"), ("quiz", "test", "exam", "grades")

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
                    non_exam_types, exam_types)), announcement.subject_type.lower(), re.MULTILINE)[0]
                announcement.subject_type = type_dict[announcement.subject_type]

        except (KeyError, IndexError):
            announcement.subject_type = None

        try:
            fuzzy_date = tuple(
                datefinder.find_dates(announcement.message))[0]
        except IndexError:
            fuzzy_date = None
        if fuzzy_date:
            announcement.deadline = fuzzy_date.strftime(r"%A %B %d %Y")
            if fuzzy_date.tzinfo:
                fuzzy_date = next(
                    datefinder.find_dates(
                        announcement.message.replace(
                            re.findall(
                                r"\d+:\d+",
                                announcement.message)[1],
                            "")))
            dt = (fuzzy_date - datetime.now()).days
            announcement.timedelta = dt

        async def _course_links(Notification: Announcement):
            """
            An internal function to return zoom meeting links in each announcement object
            """
            link_regex = "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"

            async def meetings_filter(link): return re.findall(
                "teams|zoom|meeting", link, flags=re.IGNORECASE) is not None
            links = re.findall(link_regex, Notification.message, re.MULTILINE)
            links = [i async for i in
                     async_filter(meetings_filter, links)]
            Notification.links = links if links else None

        await _course_links(announcement)
    await collect_tasks(_attr_worker, objects)
    return objects


def all_notifications(res): return asyncio.run(get_data(res))
