"""
Bot listens to commands here.
"""
import telebot
from concurrent.futures import ThreadPoolExecutor
from functions import Announcement, AsyncFunctions, LockFile, clean_list, coerce_to_none, file_handler, HighLevelFunctions,limit, notification_message_builder, null_safe, run, search_case_insensitive, string_builder, is_similar
from webmeta import WebsiteMeta


api_key, chat_id = WebsiteMeta.api_key, LockFile.public_context

bot = telebot.TeleBot(api_key)

intro = """
Hello ! To start using me, simply write a command in plain text and I will do my best to correct it (if you misspell a word).

    * Example : use the help command to show available commands and commands (or just c) to show the list of available commands and their aliases (this means
    that you execute this command with another name.)



    For any help, feature requests, or bug reports please create an issue in the dedicated GitHub repository (link_here)
    or contact me at mys239@student.bau.edu.lb via outlook.

"""

exam_types = ["quiz", "test", "exam", "grades","exams","quizzes","tests"]
non_exam_types = [("lab","lab"),("labs","lab"),("project","project"),("project","projects")]
exam_types = {name : "exam" for name in exam_types}
non_exam_types = dict(non_exam_types)
overall_types = exam_types | non_exam_types


def autocorrect(message_object, container, msg):
    msg = msg.lower()
    corrected = list(
        filter(lambda x: is_similar(msg, x, 0.7), container))
    if corrected:
        c.last_command = corrected[0]
        if msg in container:
            pass
        else:
            send_message(
                message_object, f"{message_object.text} not recognized, did you mean {corrected[0]} ? Type [y]es to execute or [n]o to abort")
        c.interactive = True


def get_results():
    return file_handler("results.json")


def get_mappings():
    return file_handler("mappings.json")


def send_message(message, text,mode=None):
    bot.send_message(message.chat.id, text,parse_mode=mode)


def get_chat_id(message):
    return message.chat.id


def map_aliases(name: str):
    if "_" in name:
        aliases = (name, name.split("_")[1], chr(
            min(ord(name.split("_")[1][0]), ord(name[0]))))
    else:
        aliases = (name, name[0])

    return {alias: name for alias in aliases}


try:
    h = HighLevelFunctions(bot.send_message)
except (KeyError, FileNotFoundError) as e:
    bot.send_message(
        chat_id, "The moodle webservice is down, I will not respond until a minute or two.")
    exit()


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

    @bot.message_handler(commands=["meeting_links", "links", "l"])
    @staticmethod
    def meeting_links(message):
        """
        A convenience function to send the zoom/teams meeting links of every subject in a text file.
        """
        h.update_links_and_meetings()
        with open("links_and_meetings.json") as f:
            string_to_be_processed = f.read()
        file_handler("links_and_meetings.txt", "w", string_to_be_processed)
        bot.send_document(get_chat_id(message), document=open(
            "links_and_meetings.txt", "rb"))

    @bot.message_handler(commands=["help", "h"])
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


        For any help, feature requests, or bug reports please create an issue in the dedicated GitHub repository (link_here)
        or contact me at mys239@student.bau.edu.lb via outlook
        """)

    @bot.message_handler(commands=["important_notifications", "i"])
    @staticmethod
    def important_notifications(message):
        """
        Returns notifications representing exams, quizzes, exam deadlines, labs, etc.. in no particular order.
        If you want to filter notifications by type, call the search function with an argument.
        """
        if h.notifications:
            with ThreadPoolExecutor() as executor:
                for i in h.notifications:
                    executor.submit(send_message, message,
                                    notification_message_builder(i))

    @bot.message_handler(commands=["commands", "c"])
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

        messages = "\n".join(limit(_descriptions(), None))
        send_message(message, messages)
    
    @bot.message_handler(commands=["remind","r"])
    @staticmethod
    def remind(message):
        """
        Sends notifications that are at most  1 week away from their deadline.
        """
        h.remind(send_message)


c = BotCommands()


@bot.message_handler(regexp="(s|search|filter|f) \w+")
def search_notifications(message):
    """
    Searches every notification and returns a "view" if more than one match is found.
    It can also search by notification type (lab, quiz, test, etc...) , see the help text or github page for more information.
    """
    mode, *query = message.text.lower().split(" ")
    if len(query) > 1:
        send_message(
            message, f"WARNING : Only the {query[0]} parameter will be accepted")
    query = query[0]
    try:
        null_safe(coerce_to_none(mode, query))
    except ValueError:
        send_message(
            message, """Please provide values for both arguments to this function.
                        Usage: (search/s) <text to find> or (filter,f) <type of notification(s)>. The types are : lab, test(quiz,exam,etc...), and project
                        Example : search zoom -> finds the notification(s) that have the word "zoom"(Zoom and ZOOM are also accepted) and highlights it/them.
                        filter lab -> finds all notifications that reminding of or announcing a lab.""")
    autocorrect(message,("search", "filter"), mode)

    def filter_by_type():
        messages = h.notifications
        if messages:
            gen = (notification_message_builder(m)
                   for m in messages if m.subject_type == overall_types[query])
            with ThreadPoolExecutor() as executor:
                for i in gen:
                    executor.submit(send_message, message, i)

    def search():
        def _search_announcement(announcement: Announcement, query: str):
            msg = announcement.message.lower()
            highlighted_string = search_case_insensitive(query, announcement.message)
            if msg and highlighted_string:
                return f"\n\n{announcement.title} \n {highlighted_string}"

        ALL_MESSAGES = run(AsyncFunctions.get_data(h.notifications_dict))
        messages = (_search_announcement(i, query)
                    for i in ALL_MESSAGES)
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
        
        send_message(message,messages,mode="Markdown")
    mode_dict = {"search": search, "s": search,
                 "filter": filter_by_type, "f": filter_by_type}
    return mode_dict[mode]()


@bot.message_handler(content_types=["text"])
def language_interpreter(message: telebot.types.Message):
    msg = message.text.lower()
    phrases = ("besta3mlo", "shou ba3mel", "shou hayda")
    corrected = list(
        filter(lambda x: is_similar(msg, x, 0.7), BotCommands.aliases.keys()))
    responses = ("yes", "y", "no", "n")
    if (msg in responses and c.interactive) or msg in BotCommands.aliases:
        if msg in BotCommands.aliases:
            callback = getattr(c, BotCommands.aliases[msg])
        else:
            callback = getattr(c, c.aliases[c.last_command])
        callback(message) if msg in BotCommands.aliases or msg == "yes" or msg == "y" else send_message(
            message, "Abort.")
        c.interactive = False
    if any(i == msg for i in phrases) or "use this" in msg:
        send_message(message, intro)
    elif corrected:
        c.last_command = corrected[0]
        if msg in BotCommands.aliases:
            pass
        else:
            send_message(
                message, f"{message.text} not recognized, did you mean {corrected[0]} ? Type [y]es to execute or [n]o to abort")
        c.interactive = True


if __name__ == '__main__':
    bot.infinity_polling()
