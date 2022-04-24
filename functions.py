import PyPDF2
from datetime import datetime
from functools import reduce
from typing import Iterable
from utilities.common import DATA_DIR, Announcement, bool_return, clean_iter, flatten_iter, json, autocorrect, string_builder, IO_DATA_DIR
from utilities.input_filters import notification_cleanup, ALL_NOTIFICATIONS


def notification_message_builder(
        notification: Announcement, custom_message=None):
    attrs = ("title", "subject", "message", "deadline")
    strings = [getattr(notification, attr)
               for attr in attrs]
    prefixes = [i.capitalize() for i in attrs]
    strings.append(notification.time_created)
    prefixes.append("Time created")
    if custom_message:
        strings[2] = custom_message

    return f"""
    ---------------------------------------
        {string_builder(strings,prefixes)}
    ---------------------------------------

    """


def search_notifications(query):
    def _search_announcement(announcement: Announcement, query: str):
        msg = announcement.message.lower()
        highlighted_string = search_case_insensitive(
            query, announcement.message)
        if msg and highlighted_string:
            return notification_message_builder(announcement, custom_message=highlighted_string)
    messages = (_search_announcement(i, query)
                for i in ALL_NOTIFICATIONS)
    messages = clean_iter(messages)
    if query:
        if len(messages) > 1:
            messages_str = string_builder(
                messages, range(1, len(messages) + 1))
            prompt = f"\nFound [1-{len(messages)}]"
            messages_str = f"{messages_str}\n{prompt}"
            return messages_str
        elif len(messages) == 1:
            return messages[0]


def search_case_insensitive(query: str, text: str):
    query = query.lower()
    found = [(q, f"[{q}]") for q in (
        query, query.capitalize(), query.upper()) if q in text]
    # *v here prevents another loop; semantically equivalent to for item in found: reduce(lambda s,v : s.replace(v), found , text where text is the default in case no results were found )
    result = reduce(lambda s, v: s.replace(*v), found, text)
    if result != text:
        return result


def get_current_week() -> str:
    pdf_file = DATA_DIR.open("rb")
    text =  PyPDF2.PdfFileReader(pdf_file)
    page = text.pages[0]
    page.extractText()
    now = datetime.now()



class TelegramInterface:
    def __init__(self) -> None:
        self.unfiltered_notifications = ALL_NOTIFICATIONS
        self.notifications = notification_cleanup(
            self.unfiltered_notifications)
        self.course_mappings_dict = json.loads(IO_DATA_DIR("mappings.json"))
        self.stripped_course_numbers = list(map(lambda x: x.split(
            "-")[0].lower(), self.course_mappings_dict.values()))
        self.update_links_and_meetings()

    def update_links_and_meetings(self):
        existing_links =IO_DATA_DIR("links_and_meetings.json")
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

    def get_index_from_name(self, query):
        query = query.replace(" ", "").strip()
        reference_tuple = self.course_mappings_dict.items()
        reference_tuple = tuple(
            map(lambda tup: (tup[0].lower().split("-")[0], tup[1].lower()), reference_tuple))
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

    def name_wrapper(self, query):
        query = query.lower()
        if query:
            index = self.get_index_from_name(query)
            return bool_return(self.get_name_from_index(index), query)
