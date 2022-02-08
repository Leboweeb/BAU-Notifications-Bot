"""
Bot listens to commands here.
"""
import telebot
from concurrent.futures import ThreadPoolExecutor
from functions import TelegramInterface, notification_message_builder, search_case_insensitive, string_builder, ALL_NOTIFICATIONS
from utilities.common import Announcement, bool_return, clean_list, coerce_to_none, file_handler, is_similar, limit, null_safe
from webmeta import WebsiteMeta

testing = True
api_key, chat_id = WebsiteMeta.api_key, WebsiteMeta.public_context
if testing:
    chat_id = WebsiteMeta.testing_chat_context

bot = telebot.TeleBot(api_key)

intro = """
Hello ! To start using me, simply write a command in plain text and I will do my best to correct it (if you misspell a word).

    * Example : use the help command to show available commands and commands (or just c) to show the list of available commands and their aliases (this means
    that you execute this command with another name.)



    For any help, feature requests, or bug reports please create an issue in the dedicated GitHub repository (link_here)
    or contact me at mys239@student.bau.edu.lb via outlook.

"""

exam_types = ["quiz", "test", "exam", "grades", "exams", "quizzes", "tests"]
non_exam_types = [("lab", "lab"), ("labs", "lab"),
                  ("project", "project"), ("project", "projects"), ("projects", "projects")]
exam_types = {name: "exam" for name in exam_types}
non_exam_types = dict(non_exam_types)
overall_types = exam_types | non_exam_types


def silent_autocorrect(container, msg):
    msg = msg.lower()
    corrected = next(
        filter(lambda x: is_similar(msg, x, 0.7), container), None)
    return bool_return(corrected)


def autoremind():
    def augmented_checker(item):
        try:
            if 0 <= item <= 7:
                return True
            return False
        except TypeError:
            return False

    notifications = interface.urgent_notifications_gen
    linked_notifications = (
        i for i in interface.unfiltered_notifications if i.links and augmented_checker(i.timedelta))
    check, links = next(notifications, None), next(linked_notifications, None)
    print(check, links)
    if check:
        send_multithreaded(notifications, chat_id)
    elif links:
        send_multithreaded((notification_message_builder(i)
                           for i in linked_notifications), chat_id)


def send_message(message, text, mode=None):
    if message == None:
        bot.send_message(chat_id, text, mode)
    try:
        bot.send_message(message.chat.id, text, parse_mode=mode)
    except AttributeError:
        bot.send_message(message, text, parse_mode=mode)


def get_chat_id(message):
    return message.chat.id


def map_aliases(name: str):
    if "_" in name:
        aliases = (name, name.split("_")[1], chr(
            min(ord(name.split("_")[1][0]), ord(name[0]))))
    else:
        aliases = (name, name[0])

    return {alias: name for alias in aliases}


def send_multithreaded(T, message_object, function=None, *args, **kwargs):
    if function == None:
        function = send_message
    with ThreadPoolExecutor() as executor:
        for item in T:
            executor.submit(function, message_object, item, *args, **kwargs)


try:
    interface = TelegramInterface()
except (KeyError, FileNotFoundError) as e:
    bot.send_message(
        chat_id, "The moodle webservice is down, I will not respond until a minute or two.")


class BotCommands:
    def __init__(self) -> None:
        self.last_command = None
        self.interactive = False
        BotCommands.commands = [func for func in dir(BotCommands) if callable(
            getattr(BotCommands, func)) and not func.startswith("__")]
        BotCommands.aliases = {}
        aliases_dict = [map_aliases(name) for name in BotCommands.commands]
        for alias in aliases_dict:
            BotCommands.aliases |= alias

    @staticmethod
    def meeting_links(message):
        """
        A convenience function to send the zoom/teams meeting links of every subject in a text file.
        """
        interface.update_links_and_meetings()
        with open("links_and_meetings.json") as f:
            string_to_be_processed = f.read()
        file_handler("links_and_meetings.txt", "w", string_to_be_processed)
        bot.send_document(get_chat_id(message), document=open(
            "links_and_meetings.txt", "rb"))

    @staticmethod
    def help(message):
        """
        Displays relevant help text.
        """
        send_message(message, """
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
    def important_notifications(message):
        """
        Returns notifications representing exams, quizzes, exam deadlines, labs, etc.. in no particular order.
        If you want to filter notifications by type, call the search function with an argument.
        """
        gen = (notification_message_builder(i)
               for i in interface.notifications)
        send_multithreaded(gen, message)

    @staticmethod
    def show_commands(message):
        """
        Displays every available command and its description.
        """
        def _descriptions():
            for i in BotCommands.commands:
                func = getattr(BotCommands, i)
                aliases = list(map_aliases(i).keys())[1:]
                yield f"Aliases : {aliases} \n{i} : {func.__doc__} "

        messages = "\n".join(limit(_descriptions(
        ), None))
        send_message(message, messages)

    @staticmethod
    def remind(message):
        """
        Sends notifications that are at most  1 week away from their deadline.
        """
        autoremind()


class CommandExecutor:
    autocorrect_text = "{message.text} not recognized, did you mean {corrected} ? Type [y]es to execute or [n]o to abort"

    def __init__(self, message) -> None:
        """
        Autocorrect all names, including aliases. If the external message is a potential alias, see if it's in a botcommand object. If more than one match is found,
        panic and terminate the program.

        TODO : Move functions here to a separate module.
        """
        all_commands = ()
        self.command, *self.query = message.split(" ")
        if not self.query:
            self.query = None
        self.corrected_message = silent_autocorrect((), self.command)

    def execute_command(self):
        commands_gen = (BotCommand(getattr(BotCommands, i), map_aliases(i))
                        for i in BotCommands.commands)
        commands_gen = filter(None, commands_gen)
        current_function = BotCommand.fetch_from_executor(
            self.corrected_message, commands_gen)
        return current_function.run(self.corrected_message)


class BotCommand:

    __slots__ = ("function", "aliases", "condition_predicate")

    def __init__(self, function, aliases, condition_predicate=None) -> None:
        self.function = function
        self.aliases = aliases
        if condition_predicate:
            self.condition_predicate = bool_return(
                condition_predicate, default=lambda x: True)

    def __contains__(self, item):
        return item in self.aliases

    def __repr__(self) -> str:
        return self.function.__name__

    def run(self, corrected_message: str):
        # send the autocorrected message from the executor
        if self.condition_predicate(corrected_message):
            if corrected_message in self.aliases:
                self.function(corrected_message)

    @staticmethod
    def fetch_from_executor(message, command_iter):
        for command in command_iter:
            if message == command.function.__name__ or message in command.aliases:
                return command


c = BotCommands()


def search(message):
    """
    Searches every notification and returns a "view" if more than one match is found.
    It can also search by notification type (lab, quiz, test, etc...) , see the help text or github page for more information.
    """
    try:
        mode, *query = message.text.lower().split(" ")
        if len(query) > 1:
            query = " ".join(query)
        else:
            query = query[0]
        null_safe(coerce_to_none(mode, query))
    except ValueError:
        send_message(
            message, """Please provide values for both arguments to this function.
                        Usage: (search/s) <text to find> or (filter,f) <type of notification(s)>. The types are : lab, test(quiz,exam,etc...), and project
                        Example : search zoom -> finds the notification(s) that have the word "zoom"(Zoom and ZOOM are also accepted) and highlights it/them.
                        filter lab -> finds all notifications that reminding of or announcing a lab.""")

    def filter_by_type():
        course_mappings = interface.course_mappings_dict
        messages = interface.unfiltered_notifications
        try:
            processed_message = interface.get_index_from_name(query)
            processed_message = tuple(course_mappings.keys())[
                processed_message]
        except TypeError:
            send_message(
                message, "No notifications of that subject were found")

        def get_subjects_codes():
            send_multithreaded(
                (i for i in messages if i.subject_code == processed_message or i.subject == processed_message), message)

        def get_subjects_types():
            messages = interface.notifications
            if messages:
                gen = (notification_message_builder(m)
                       for m in messages if m.subject_type == overall_types[query])
                if next(gen, None) != None:
                    send_multithreaded(gen, message)
                else:
                    send_message(
                        message, "No notifications of that subject were found")

        if processed_message not in course_mappings.items():
            get_subjects_types()
        else:
            get_subjects_codes()

    def _search():
        def _search_announcement(announcement: Announcement, query: str):
            msg = announcement.message.lower()
            highlighted_string = search_case_insensitive(
                query, announcement.message)
            if msg and highlighted_string:
                return notification_message_builder(announcement, custom_message=highlighted_string)
        messages = (_search_announcement(i, query)
                    for i in ALL_NOTIFICATIONS)
        messages = clean_list(messages)
        if len(messages) == 1:
            messages = messages[
                0]
        elif len(messages) > 1:
            send_message(
                message, f"Found more than one match for {query} in announcements:")
            messages_str = string_builder(
                (i for i in messages), range(1, len(messages)+1))
            prompt = f"\nFound [1-{len(messages)}"
            messages = f"{messages_str}\n{prompt}"

        send_message(message, messages)
    mode_dict = {"search": _search, "s": _search,
                 "filter": filter_by_type, "f": filter_by_type}
    return mode_dict[mode]()


@bot.message_handler(content_types=["text"])
def language_interpreter(message: telebot.types.Message):
    msg = message.text.lower()
    phrases = ("kif besta3mlo", "shou ba3mel", "shou hayda", "what is this")
    corrected = next(
        filter(lambda x: is_similar(msg, x, 0.7), BotCommands.aliases), None)
    responses = ("yes", "y", "no", "n")
    if (msg in responses and c.interactive) or msg in BotCommands.aliases:
        if msg in BotCommands.aliases:
            callback = getattr(c, BotCommands.aliases[msg])
        else:
            callback = getattr(c, c.aliases[c.last_command])
        callback(message) if msg in BotCommands.aliases or msg == "yes" or msg == "y" else send_message(
            message, "Abort.")
        c.interactive = False
    elif any(i == msg for i in phrases) or "use this" in msg:
        send_message(message, intro)
    elif corrected:
        c.last_command = corrected
        if msg in BotCommands.aliases:
            pass
        else:
            send_message(
                message, f"{message.text} not recognized, did you mean {corrected} ? Type [y]es to execute or [n]o to abort")
        c.interactive = True


if __name__ == '__main__':
    autoremind()
    bot.infinity_polling()
