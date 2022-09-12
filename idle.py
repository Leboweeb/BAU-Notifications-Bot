"""
Bot listens to commands here.
"""
import os
from typing import Callable, Iterable, Optional, TypeVar
import telebot
from concurrent.futures import ThreadPoolExecutor
from functions import TelegramInterface, notification_message_builder
from utilities.common import autocorrect, WebsiteMeta, IO_DATA_DIR, bool_return, mapping_init

api_key, chat_id = WebsiteMeta.api_key, WebsiteMeta.public_context
# set the bot to testing mode if the words true, True, T, yes, y, or yes, set to normal mode otherwise
testing = dict.fromkeys(("true", "True", "T", "yes", "y", "Yes"), True).get(
    IO_DATA_DIR("settings.cfg").split("=")[1], False)
chat_id = WebsiteMeta.testing_chat_context if testing else WebsiteMeta.public_context
bot = telebot.TeleBot(api_key)
mapping_init()
intro = """
Hello ! To start using me, simply write a command in plain text and I will do my best to correct it (if you misspell a word).

    * Example : use the help command to show available commands and commands (or just c) to show the list of available commands and their aliases (this means
    that you execute this command with another name.)



    For any help, feature requests, or bug reports please create an issue in the dedicated GitHub repository (link_here)
    or contact me at mys239@student.bau.edu.lb via outlook.

"""

T = TypeVar("T")
def auto_split(msg: str): return telebot.util.smart_split(msg, 3000)


try:
    interface = TelegramInterface()
except (KeyError, FileNotFoundError):
    bot.send_message(
        chat_id, "The moodle webservice is down, I will not respond until a minute or two.")


def autoremind():
    result = interface.autoremind_worker()
    send_multithreaded(result)
    return result


def send_message(text: str):
    bot.send_message(chat_id, text)


def wrap_result(res: Optional[str], fail_message: str):
    # handle both Announcement objects and strings
    send_multithreaded(auto_split(res)) if res else send_message(fail_message)


def map_aliases(name: str) -> dict[str, str]:
    default_aliases: tuple[str, ...] = (name, name[0])
    aliases = default_aliases

    def sort_by_alpha_order(chr1: str, chr2: str):
        return chr(min(ord(chr1), ord(chr2)))

    if "_" in name:
        split = name.split("_")
        if len(split) > 1:
            aliases = (name, split[0], sort_by_alpha_order(
                split[0][0], name[0]), split[1], sort_by_alpha_order(split[1][0], name[0]))

    return {alias: name for alias in aliases}


def send_multithreaded(T: Iterable[str], *args, **kwargs):
    with ThreadPoolExecutor() as executor:
        for item in T:
            executor.submit(send_message, item, *args, **kwargs)


class BotCommands:
    bot_commands: list[str]
    aliases: dict[str, str]

    def __init__(self) -> None:
        BotCommands.bot_commands = [func for func in dir(BotCommands) if callable(
            getattr(BotCommands, func)) and not func.startswith("__")]
        self.last_command: Callable[[str], None]
        self.last_argument = ""
        self.interactive = False
        BotCommands.aliases = {}
        aliases_dict = [map_aliases(name) for name in BotCommands.bot_commands]
        for alias in aliases_dict:
            BotCommands.aliases |= alias

    @staticmethod
    def whatis(message):
        """
        Tells you what a subject code is if it is recognized.
        For example, COMP210 is Programming II
        """
        subject = interface.name_wrapper(message)
        send_message(
            f"{message} is {subject}" if subject else "Subject not recognized")

    @staticmethod
    def meeting_links(message):
        """
        A convenience function to send the zoom/teams meeting links of every subject in a text file.
        """
        interface.update_links_and_meetings()
        string_to_be_processed = IO_DATA_DIR("links_and_meetings.json")
        IO_DATA_DIR("links_and_meetings.txt", "w", string_to_be_processed)
        bot.send_document(chat_id, document=open(
            "./bot_data_stuff/links_and_meetings.txt", "rb"))

    @staticmethod
    def help(message):
        """
        Displays relevant help text.
        """
        send_message("""
        Features:

        * Automatically filters out unimportant notifications with the /important or /i command and sends them in a digestible format.


        * It also reminds you a week and a day before their deadlines.

        * Send a text file containing zoom/teams meetings links for each subject (and resets every semester)

        * Send a message by subject or type (exam,lab,etc..).

        * Search notifications, if more than one match is found, this bot will provide a "view" on them and
        help you select the correct one.

        * Corrects commands automatically.

        To see the list of available commands, type c or commands (on their own)


        For any help, feature requests, or bug reports please create an issue in the dedicated GitHub repository (https://github.com/Leboweeb/BAU-Notifications-Bot)
        or contact me at mys239@student.bau.edu.lb via outlook
        """)

    @staticmethod
    def important(message):
        """
        Returns notifications representing exams, quizzes, exam deadlines, labs, etc.. in no particular order.
        If you want to filter notifications by type, call the search function with an argument.
        """
        send_message(
            "\n".join(map(notification_message_builder, interface.notifications)))

    @staticmethod
    def commands(message):
        """
        Displays every available command and its description.
        """
        def _descriptions():
            for i in BotCommands.bot_commands:
                func = getattr(BotCommands, i)
                aliases = list(map_aliases(i).keys())[1:]
                yield f"Aliases : {aliases} \n{i} : {func.__doc__} "

        messages = "\n".join(list(_descriptions(
        )))
        send_message(messages)

    @staticmethod
    def remind(message):
        """
        Sends notifications that are at most  1 week away from their deadline.
        """
        stuff = autoremind()
        wrap_result(stuff, "No urgent notifications found")

    @staticmethod
    def search(message: str):
        """
        Searches every notification and returns a "view" if more than one match is found.
        It can also search by notification type (lab, quiz, test, etc...) , see the help text or github page for more information.
        """
        potential_messages = interface.search_notifications(message)
        wrap_result(potential_messages,
                    "No notifications matching this query were found.")

    @staticmethod
    def filter_by_type(query: str):
        """
        Filter notifications by 3 categories:

        recent : gets notifications that have been posted at most one week away from now.

        course code or name : gets all notifications that match the subject code or name. (for example, filter comp 208 or filter programming will get all notifcations
        that correspond to programming I)

        subject type : gets all notifications that correspond to a notification type (exam, project, lab , etc...). For example, filter lab will get all

        notifications from a subject's lab (note that lab exams can be found from both filter exam and filter lab so certain types may overlap)
        """

        res = bool_return(interface.filter_by_type_worker(query), "")
        final_res = "\n".join(map(notification_message_builder, res))
        wrap_result(
            final_res, "No notifications matching this filter were found")

    @staticmethod
    def update(message):
        """
        Refreshes notifications automatically
        """
        send_message("Updating notifications")
        os.chdir("/".join(__file__.split("/")[:-1]))
        os.system("python3 endpoint.py")
        send_message("Done updating notifications")


c = BotCommands()


@bot.message_handler(content_types=["text"])
def language_interpreter(message: telebot.types.Message):
    def get_fn(f: str): return getattr(c, c.aliases[f])
    thing = message.text.lower()
    function, *_ = thing.split(" ")
    argument = " ".join(_)
    def in_aliases(): return function in c.aliases
    phrases = ("kif besta3mlo", "shou ba3mel", "shou hayda", "what is this")
    responses = ("yes", "y", "no", "n")
    if any(i == thing for i in phrases) or "use this" in thing:
        send_message(intro)
    elif in_aliases():
        c.last_command = get_fn(function)
        c.last_command(argument)
    elif function in responses and c.interactive:
        if function in responses[2:]:
            send_message("Abort.")
        else:
            c.last_command(c.last_argument)
    elif not in_aliases():
        corrected: str = autocorrect(c.aliases, function)
        if corrected:
            c.last_command = get_fn(corrected)
            c.last_argument = argument
            send_message(
                f"{message.text} not recognized, did you mean {corrected} ? Type [y]es to execute or [n]o to abort")
            c.interactive = True


if __name__ == '__main__':
    # autoremind()
    bot.infinity_polling()
