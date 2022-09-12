import itertools
from typing import Iterable
from functools import reduce
from utilities.common import Announcement, bool_return, checker_factory, clean_iter, flatten_iter, json, autocorrect, string_builder, IO_DATA_DIR, to_natural_str
from utilities.input_filters import notification_cleanup, ALL_NOTIFICATIONS
from utilities.time_parsing_lib import now, datetime


def notification_message_builder(
        notification: Announcement, custom_message=None):
    attrs = ("title", "subject", "message", "deadline")
    strings = [getattr(notification, attr)
               for attr in attrs]
    prefixes = [i.capitalize() for i in attrs]
    strings.append(to_natural_str(notification.date_created))
    if strings[-2]:
        strings[-2] += f"  ({( (datetime.strptime(strings[-2],'%A %B %d %Y')) - now ).days }days left)"
    prefixes.append("Time created")
    if custom_message:
        strings[2] = custom_message

    return f"""
    ---------------------------------------
        {string_builder(strings,prefixes)}
    ---------------------------------------

    """


def search_case_insensitive(query: str, text: str):
    query = query.lower()
    found = [(q, f"[{q}]") for q in (
        query, query.capitalize(), query.upper()) if q in text]
    # *v here prevents another loop; semantically equivalent to for item in found: reduce(lambda s,v : s.replace(v), found , text where text is the default in case no results were found )
    result = reduce(lambda s, v: s.replace(*v), found, text)
    if result != text:
        return result


class TelegramInterface:
    def __init__(self) -> None:
        exam_types: dict[str, str] = dict.fromkeys(
            ("quiz", "test", "exam", "grades", "exams", "quizzes", "tests"), "exam")
        non_exam_types = dict.fromkeys(("lab", "labs"), "lab") | dict.fromkeys(
            ("project", "projects"), "project")
        overall_types = exam_types | non_exam_types
        self.overall_types = overall_types
        self.unfiltered_notifications: tuple[Announcement] = ALL_NOTIFICATIONS
        self.notifications = notification_cleanup(
            self.unfiltered_notifications)
        self.course_mappings_dict: dict[str, str] = json.loads(
            IO_DATA_DIR("mappings.json"))
        self.stripped_course_numbers = list(map(lambda x: x.split(
            "-")[0].lower(), self.course_mappings_dict.values()))
        self.update_links_and_meetings()

    def update_links_and_meetings(self):
        existing_links = IO_DATA_DIR("links_and_meetings.json")
        if existing_links:
            try:
                existing_links = json.loads(existing_links)
            except json.decoder.JSONDecodeError:
                existing_links = None
        notifications = {
            announcement.subject: announcement.links
            for announcement in self.unfiltered_notifications
            if announcement.links and announcement.subject_type}
        if isinstance(existing_links, dict):
            notifications |= existing_links
        notifications = json.dumps(notifications, indent=4)
        IO_DATA_DIR("links_and_meetings.json", "w", notifications)

    def get_index_from_name(self, query: str):
        query = query.replace(" ", "").strip()
        reference_tuple = tuple(
            map(lambda tup: (tup[0].lower().split("-")[0], tup[1].lower()), self.course_mappings_dict.items()))
        try:
            index = None
            if query == "":
                raise TypeError
            for i, j in zip(reference_tuple, range(len(reference_tuple))):
                if query in i[0] or query in i[1]:
                    index = j
            if index is None:
                try:
                    reference_tuple = flatten_iter(reference_tuple)
                    index = reference_tuple.index(
                        autocorrect(reference_tuple, query, ratio=0.75))
                except (ValueError, IndexError):
                    index = None
            return index

        except TypeError:
            return None

    def get_name_from_index(self, index: int):
        if index:
            return self.course_mappings_dict[tuple(self.course_mappings_dict.keys())[index]]

    def name_wrapper(self, query: str):
        query = query.lower()
        if query:
            index = self.get_index_from_name(query)
            return bool_return(self.get_name_from_index(index), query)

    def autoremind_worker(self):

        is_relatively_recent = checker_factory(0, 7)
        return filter(is_relatively_recent, self.notifications)

    def search_notifications(self, query: str) -> str | None:
        def _search_announcement(announcement: Announcement, query: str):
            msg = announcement.message.lower()
            highlighted_string = search_case_insensitive(
                query, announcement.message)
            if msg and highlighted_string:
                return notification_message_builder(announcement, custom_message=highlighted_string)
        messages: list[Announcement] = clean_iter((_search_announcement(i, query)
                                                   for i in ALL_NOTIFICATIONS), list)
        if query:
            if len(messages) > 1:
                messages_str = string_builder(
                    messages, range(1, len(messages) + 1))
                prompt = f"\nFound [1-{len(messages)}]"
                messages_str = f"{messages_str}\n{prompt}"
                return messages_str
            elif len(messages) == 1:
                return messages[0].message

        return None

    def filter_by_type_worker(self, query: str) -> Iterable[Announcement] | None:

        def _traditional_types():
            course_mappings = self.course_mappings_dict
            messages = self.unfiltered_notifications
            processed_message = ""
            try:
                processed_message = self.name_wrapper(query)
            except TypeError:
                processed_message = None

            def subjects_codes_condition(x):
                return course_mappings[x.subject_code.split(":")[0]] == processed_message

            def subjects_types_condition(
                x): return self.overall_types[processed_message] in x.subject_type

            if processed_message in itertools.chain.from_iterable(course_mappings.items()):
                return filter(subjects_codes_condition, messages)
            elif processed_message in self.overall_types:
                return filter(subjects_types_condition, messages)

        if query == "recent":
            f = checker_factory(0, 7)
            return filter(lambda dt:  f((now - dt.date_created).days), self.unfiltered_notifications)
        else:
            return _traditional_types()
