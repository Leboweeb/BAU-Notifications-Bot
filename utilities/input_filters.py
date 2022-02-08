from collections import Counter
import html
from typing import List
from utilities.async_functions import all_notifications, re
from utilities.common import Announcement, bool_return, file_handler, gen_exec, is_similar,clean_list, json, notifications_wrapper


ALL_NOTIFICATIONS = all_notifications(notifications_wrapper())
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

def update_links(Announcements: List[Announcement]):
    links_dict = {
        announcement.subject: announcement.links
        for announcement in Announcements}
    file_handler("links_and_meetings.json", "w", json.dumps(
        links_dict, indent=4)) if links_dict else None


def silent_autocorrect(container, msg, ratio=0.7):
    msg = msg.lower()
    corrected = next(
        filter(lambda x: is_similar(msg, x, ratio), container), None)
    return bool_return(corrected)




def mapping_init():
    file_handler("mappings.json", "w", "")
    res = file_handler("courses.json")
    data = json.loads(res)[0]["data"]["courses"]
    data = [i for i in data]
    mappings = {item["shortname"]: html.unescape(
        item["fullname"]).split("-")[0] for item in data}
    file_handler("mappings.json", "w", json.dumps(mappings, indent=4))


def lockfile_cleanup(res: dict) -> List[Announcement]:
    important_notifications = hilight(res)
    important_notifications = PostponedHandler(
        important_notifications).find_matching()
    important_notifications = clean_list(
        important_notifications)
    return important_notifications


def hilight(res: dict) -> List[Announcement]:
    def _important_notification(Notification: Announcement):
        if re.findall(
            r"\blab\b|\btest\b|\bquiz\b|\bfinal\b|\bgrades\b|\bgrade\b|\bmakeup\b|\bincomplete exam\b|\bproject\b",
            Notification.message.lower(),
                flags=re.MULTILINE):
            return True
    important_objects = list(filter(_important_notification, ALL_NOTIFICATIONS))
    return important_objects