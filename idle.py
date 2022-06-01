"""
Bot listens to commands here.
"""
import os
import telebot
from datefinder import find_dates
from concurrent.futures import ThreadPoolExecutor
from functions import TelegramInterface, notification_message_builder
from utilities.common import autocorrect, checker_factory, WebsiteMeta, null_safe_chaining, IO_DATA_DIR

api_key, chat_id = WebsiteMeta.api_key, WebsiteMeta.public_context

bot = telebot.TeleBot(api_key)

intro = """
Hello ! To start using me, simply write a command in plain text and I will do my best to correct it (if you misspell a word).

    * Example : use the help command to show available commands and commands (or just c) to show the list of available commands and their aliases (this means
    that you execute this command with another name.)



    For any help, feature requests, or bug reports please create an issue in the dedicated GitHub repository (link_here)
    or contact me at mys239@student.bau.edu.lb via outlook.

"""


try:
    interface = TelegramInterface()
except (KeyError, FileNotFoundError):
    bot.send_message(
        chat_id, "The moodle webservice is down, I will not respond until a minute or two.")



def autoremind():
    result = interface.autoremind_worker()
    send_multithreaded(result)
    return result


def send_message(message, text, mode=None):
    if message is None:
        bot.send_message(chat_id, text, mode)
    try:
        bot.send_message(message.chat.id, text, parse_mode=mode)
    except AttributeError:
        bot.send_message(message, text, parse_mode=mode)


def get_chat_id(message):
    return message.chat.id


def map_aliases(name: str):
    default_aliases : tuple[str,...] = (name, name[0])
    aliases = default_aliases
    if "_" in name:
        split = name.split("_")
        if len(split) == 2:
            aliases = (name, split[1], chr(
                min(ord(split[1][0]), ord(name[0]))))

    return {alias: name for alias in aliases}


def send_multithreaded(T, message_object=None, function=None, *args, **kwargs):
    if function is None:
        function = send_message
    with ThreadPoolExecutor() as executor:
        for item in T:
            executor.submit(function, message_object, item, *args, **kwargs)




class BotCommands:
    commands : list[str]
    aliases : dict[str, str]
    def __init__(self) -> None:
        BotCommands.commands = [func for func in dir(BotCommands) if callable(
        getattr(BotCommands, func)) and not func.startswith("__")]
        self.last_command = None
        self.last_argument = ""
        self.interactive = False
        BotCommands.aliases = {}
        aliases_dict = [map_aliases(name) for name in BotCommands.commands]
        for alias in aliases_dict:
            BotCommands.aliases |= alias

    @staticmethod
    def meeting_links():
        """
        A convenience function to send the zoom/teams meeting links of every subject in a text file.
        """
        interface.update_links_and_meetings()
        with open("links_and_meetings.json") as f:
            string_to_be_processed = f.read()
        IO_DATA_DIR("links_and_meetings.txt", "w", string_to_be_processed)
        bot.send_document(chat_id, document=open(
            "links_and_meetings.txt", "rb"))

    @staticmethod
    def help():
        """
        Displays relevant help text.
        """
        send_message(None, """
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
    def important_notifications():
        """
        Returns notifications representing exams, quizzes, exam deadlines, labs, etc.. in no particular order.
        If you want to filter notifications by type, call the search function with an argument.
        """
        gen = (notification_message_builder(i)
               for i in interface.notifications)
        send_multithreaded(gen, None)

    @staticmethod
    def show_commands():
        """
        Displays every available command and its description.
        """
        def _descriptions():
            for i in BotCommands.commands:
                func = getattr(BotCommands, i)
                aliases = list(map_aliases(i).keys())[1:]
                yield f"Aliases : {aliases} \n{i} : {func.__doc__} "

        messages = "\n".join(list(_descriptions(
        )))
        send_message(None, messages)

    @staticmethod
    def remind():
        """
        Sends notifications that are at most  1 week away from their deadline.
        """
        stuff = autoremind()
        print(stuff)
        if not stuff:
            send_message(None, "No urgent notifications found")

    @staticmethod
    def search(message: str):
        """
        Searches every notification and returns a "view" if more than one match is found.
        It can also search by notification type (lab, quiz, test, etc...) , see the help text or github page for more information.
        """
        potential_messages = interface.search_notifications(message)
        send_message(None, potential_messages) if potential_messages else send_message(
            None, "No notifications matching this word were found.")

    @staticmethod
    def filter_by_type(query):
        def _traditional_types():
            result = interface.filter_by_type_worker(query)
            if result:
                send_multithreaded(notification_message_builder(i)
                                   for i in result)
            else:
                send_message(None, "No notifications of that type were found")
        if query == "recent":
            checker = checker_factory(0, 4)
            send_multithreaded(notification_message_builder(
                i) for i in interface.unfiltered_notifications if checker(null_safe_chaining(next(find_dates(i.time_created), None), "day")))
        else:
            _traditional_types()

    @staticmethod
    def hot_reload():
        pass


c = BotCommands()


def func_caller(func, arguments):
    try:
        func(arguments)
    except TypeError:
        func()


@bot.message_handler(content_types=["text"])
def language_interpreter(message: telebot.types.Message):
    def execute_bot_command(arg): return func_caller(c.last_command, arg)
    def map_to_function(m): return getattr(BotCommands, c.aliases[m])
    thing = message.text.lower()
    function = thing.split(" ")[0].strip()
    argument = thing[len(function) + 1:].strip()
    in_aliases = function in c.aliases
    phrases = ("kif besta3mlo", "shou ba3mel", "shou hayda", "what is this")
    responses = ("yes", "y", "no", "n")
    if any(i == thing for i in phrases) or "use this" in thing:
        send_message(message, intro)
    elif in_aliases:
        c.last_command = map_to_function(function)
        execute_bot_command(argument)
    elif function in responses and c.interactive:
        if function in responses[2:]:
            send_message(message, "Abort.")
        else:
            func_caller(execute_bot_command, c.last_argument)
    elif not in_aliases:
        corrected: str = autocorrect(c.aliases, function)
        if corrected:
            c.last_command = map_to_function(corrected)
            c.last_argument = argument
            send_message(
                message, f"{message.text} not recognized, did you mean {corrected} ? Type [y]es to execute or [n]o to abort")
            c.interactive = True


def entry_point(testing=True):
    global chat_id
    chat_id = WebsiteMeta.testing_chat_context if testing else WebsiteMeta.public_context

    def update_notifications():
        os.chdir("/".join(__file__.split("/")[:-1]))
        os.system("python3 endpoint.py")
    # update_notifications()
    # print("Done updating notifications")


if __name__ == '__main__':
    entry_point(testing=True)
    # autoremind()
    bot.infinity_polling()
