import httpx
from functools import reduce
from bs4 import BeautifulSoup
from typing import Iterable
from utilities.common import Announcement, flatten_iter, my_format, notifications_wrapper, run, file_handler, json, autocorrect
from utilities.input_filters import notification_cleanup, ALL_NOTIFICATIONS



def notification_message_builder(
        notification: Announcement, custom_message=None):
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


def soup_bowl(html): return BeautifulSoup(html, "lxml")


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


def hilight_word(string: str, query) -> str:
    if all((string, query)):
        words = string.lower().split(" ")
        words[words.index(query)] = f"**{query}**"
        return " ".join(words)




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
            encoded = url_encode(
                {"username": username, "password": password,
                 "execution": fr"{execution}", "_eventId": "submit",
                 "geolocation": ""})
            await Client.post(LOGIN_URL, data=encoded,
                              headers=login_headers, params=querystring)

            cookies = [Client.cookies.get(i) for i in (
                'MoodleSession', 'BNES_MoodleSession')]
            my_format(cookies, "Cookies in async api")
            await func(cookies, Client)
    return wrapper_func


class TelegramInterface:
    def __init__(self) -> None:
        self.unfiltered_notifications = ALL_NOTIFICATIONS
        self.notifications = notification_cleanup(
            self.unfiltered_notifications)
        self.course_mappings_dict = json.loads(file_handler("mappings.json"))
        self.stripped_course_numbers = list(map(lambda x: x.split(
            "-")[0].lower(), self.course_mappings_dict.values()))
        self.update_links_and_meetings()

    def update_links_and_meetings(self):
        existing_links = file_handler("links_and_meetings.json")
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
        file_handler("links_and_meetings.json", "w", notifications)

    def get_index_from_name(self, query):
        query = query.replace(" ", "").strip()
        reference_tuple = self.course_mappings_dict.items()
        reference_tuple = tuple(
            map(lambda tup: (tup[0].lower().split("-")[0], tup[1].lower()), reference_tuple))
        try:
            index = None
            if query == "":
                raise TypeError("empty strings are not allowed")
            for i, j in zip(reference_tuple, range(len(reference_tuple))):
                if query in i[0] or query in i[1]:
                    index = j
            if index == None:
                try:
                    reference_tuple = flatten_iter(reference_tuple)
                    index = reference_tuple.index(autocorrect(reference_tuple,query,ratio=0.75))
                except (ValueError,IndexError):
                    index = None
            return index

        except TypeError:
            return None

    def get_name_from_index(self, index: int):
        if index:
            return self.course_mappings_dict[tuple(self.course_mappings_dict.keys())[index]]
            
