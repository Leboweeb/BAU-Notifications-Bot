from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from io import BufferedReader
import re
import requests
import PyPDF2
from typing import Callable, Generator, Iterable, Optional, Sequence
from utilities.common import DATA_DIR, IO_DATA_DIR, REQUIRED_DATE_FORMAT, UnexpectedBehaviourError, flattening_iterator, null_safe_chaining


datetime_dict = dict[str, int]


DAYS, MONTHS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"), ("January",
                                                                                                "February", "March", "April", "June", "July", "August", "September", "October", "November", "December")


def to_natural_str(dt: datetime): return dt.strftime("%A %B %d %Y")


def datetime_to_dict(dt: datetime) -> datetime_dict: return {
    "year": dt.year, "month": dt.month, "day": dt.day}


def replace_dt_with_dict(dt: datetime, dt_dict: datetime_dict, tzinfo=None):
    return dt.replace(**dt_dict, tzinfo=None)


# Semester Namespace

PDF_URL = r"https://mis.bau.edu.lb/web/v12/PortalAssets/Calendar.pdf"


@dataclass
class SemesterMetaInfo:
    semester: str = field(init=False)
    semester_month_dict: dict[datetime, Optional[str]] = field(init=False)


def find_current_semester(info_obj: SemesterMetaInfo):
    semester_months = info_obj.semester_month_dict
    semester_list = sorted(flattening_iterator(semester_months, now))
    return semester_months[semester_list[semester_list.index(now) - 1]]


def find_week(info_obj: SemesterMetaInfo,  week: int = 0):
    # find the current week if week = 0, otherwise find out when a particular week is
    semester, semester_dict = info_obj.semester, {
        v: k for k, v in info_obj.semester_month_dict.items()}
    FIRST_WEEK_DATE = semester_dict[semester.capitalize()]
    if week:
        return to_natural_str(FIRST_WEEK_DATE + timedelta(weeks=week))
    count, curr_dt = 0, FIRST_WEEK_DATE

    def in_week(timestamp: datetime, ref: datetime):
        def find_week(dt: datetime): return dt - timedelta(days=dt.weekday())
        return find_week(timestamp) == find_week(ref)
    while not in_week(curr_dt, now):
        count += 1
        curr_dt += timedelta(weeks=1)
    return count


def get_semester_dict(text: str):
    DATE_FORMAT = fr"\d+-({'|'.join(mon_abbr)})-\d+"

    def find_semester_dates():
        return re.finditer(fr"{DATE_FORMAT}\w+(semester|session)(beginsforallfaculties|begins)", text, re.IGNORECASE)

    dates = find_semester_dates()

    def search_no_case(pattern: str, _string: str) -> Optional[str]: return null_safe_chaining(
        re.search(pattern, _string, re.IGNORECASE), "group")()

    semester_months: dict[datetime, Optional[str]] = {
        datetime.strptime(re.sub(r"(fall|spring|summer)\w+", "", i.group(), flags=re.IGNORECASE),
                          "%d-%b-%y"):  search_no_case("fall|spring|summer", i.group()) for i in dates
    }
    return semester_months


def make_request():
    pdf_req = requests.get(PDF_URL)
    IO_DATA_DIR("smth.pdf", "wb", pdf_req.content)


def abbreviate(x): return x[:3]
def read_pdf(): return DATA_DIR.joinpath("smth.pdf").open("rb")


day_abbr, mon_abbr = (map(abbreviate, i) for i in (DAYS, MONTHS))
now = datetime(**datetime_to_dict(datetime.now()), tzinfo=None)


def get_pdf_text(fileobj: BufferedReader):
    text = PyPDF2.PdfFileReader(fileobj)
    page = text.pages[0]
    pdf_txt: str = page.extractText()
    pdf_txt = re.sub("\s", "", pdf_txt)
    return pdf_txt


def set_pdf(): return get_pdf_text(read_pdf())


pdf_text = set_pdf()

meta_inf = SemesterMetaInfo()

meta_inf.semester_month_dict = get_semester_dict(pdf_text)
if max(meta_inf.semester_month_dict).year < now.year:
    make_request()
    pdf_text = set_pdf()

meta_inf.semester = find_current_semester(meta_inf)


class RelativeDates:

    ANCHORS = ("next", "last", "before", "after")
    temp = ("today", "tomorrow", "day", "week",
            "month", "year", "decade", "century", 'days', 'weeks', 'months', 'years', 'decades', 'centuries')
    DATE_WORDS: dict[str, str] = dict(
        zip(temp[8:], temp[2:8])) | {i: i for i in temp[2:8]}

    def __init__(self, string: str, anchor: datetime = datetime.now()) -> None:
        self.string = string
        self.mode = self.mode_factory()
        self.anchor = anchor

    class DateCopy:
        def __init__(self, datetime: datetime = datetime.now()) -> None:
            ALL_ATTRS = ("hour", "day", "month", "year")
            self.date = datetime
            self.weekday = self.date.weekday()
            self.minute, self.hour, self.day, self.month, self.year = {
                getattr(self.date, i, None) for i in ALL_ATTRS}

        def transform_copy(self):
            return datetime(self.year, self.month, self.day, self.hour, self.minute)

    @staticmethod
    def change_dt(anchor: datetime, operation: str = '-') -> Callable[[datetime_dict], datetime]:
        # less error prone date subtraction or addition api
        if operation not in ("+", "-"):
            raise UnexpectedBehaviourError(
                f"Operation type {operation} not defined in datetime context", RelativeDates.change_dt)

        def convert_unit(date: datetime_dict) -> datetime:
            day_conversion_map = {
                "day": 1,
                "days": 1,
                "week": 7,
                "weeks": 7,
            }
            year_conversion_map = {
                "year": 1,
                "years": 1,
                "decade": 10,
                "decades": 10,
                "century": 100,
                "centuries": 100
            }
            def generate_unit(map: datetime_dict, reference: datetime_dict) -> int: return sum(
                (v * map[k] for k, v in reference.items() if k in map))
            simplified_dict = {
                "days": generate_unit(day_conversion_map, date),
                "months": date.get("month", 0) or date.get("months", 0),
                "years": generate_unit(year_conversion_map, date)
            }
            # # literally everything works except months because the gregorian calendar is stupid, seriously why the fuck do we use this shit
            transformed_date = anchor - \
                timedelta(days=simplified_dict["days"]) if operation == "-" else anchor + timedelta(
                    days=simplified_dict["days"])
            return transformed_date.replace(month=anchor.month - simplified_dict["months"], year=anchor.year - simplified_dict["years"]) if operation == "-" else transformed_date.replace(month=anchor.month + simplified_dict["months"], year=anchor.year + simplified_dict["years"])
        return convert_unit

    def find_relative_dates(self, string: str):

        string = re.sub(r"[^a-zA-Z0-9\s]", "", string)

        class Proxy:
            pass
        if re.search(r"\d+ \w+ ago", string):
            p, split = Proxy(), string.split(" ")
            for i, j in enumerate(split):
                if j.isdigit() and split[i + 1] in RelativeDates.DATE_WORDS:
                    # p.__dict__ has type dict[str, int]
                    setattr(
                        p, RelativeDates.DATE_WORDS[split[i + 1].lower()], int(j))
            offset = self.change_dt(self.anchor)
            return offset(p.__dict__)

    def parse_number_mode(self) -> str | None:
        potential_date: Callable[[str], str] = null_safe_chaining(
            self.find_relative_dates(self.string), "strftime")
        if potential_date:
            return potential_date(REQUIRED_DATE_FORMAT)
        return None

    def natural_language_mode(self) -> datetime | None:
        POSITIVE_OFFSETS, NEGATIVE_OFFSETS = (
            ("next", "after", "this"), ("ago", "before", "last"))
        ...
        return None

    def mode_factory(self):
        if re.fullmatch(r"\d+", self.string):
            return self.parse_number_mode
        else:
            return self.natural_language_mode


# The natural language mode helper  method in the RelativeDate class can format the result as a string
date_words = ("day", "week", "month", "year", "decade", "century")
positive_offsets, negative_offsets = (
    ("next ", "after", "following", "tomorrow"),
    ("last", "before", "previous", "yesterday")
)


def add_regex_boundaries(coll: Sequence[str]) -> Generator[str, None, None]:
    for i in coll:
        yield fr"\b{i}\b|"


def unit_stack(s: str):
    # yesterday, tomorrow, and day should not be in the same sentence
    day_units: tuple[str, ...] = (
        date_words[0], positive_offsets[-1], negative_offsets[-1])
    return len(re.findall("|".join(day_units), s)) > 1


def only_one_offset(s: str):
    def found_any_in_str(
        coll: Iterable[str]): return any(i in s for i in coll)
    return found_any_in_str(positive_offsets) ^ found_any_in_str(negative_offsets)


def offset(offset_obj: Offset, dt: datetime) -> datetime | None:
    transform_fn = RelativeDates.change_dt(dt, offset_obj.offset_type)
    return None


@dataclass
class Offset:
    offset_type: str
    offset_count: int
    offset_units: datetime_dict


def relative_date(s: str, anchor: datetime = datetime.now()) -> datetime | None:
    """
        neg offsets are -1 and pos offsets are +1. All offsets stack and are relative to the unit and the specified anchor\n
        For example, \n
        You got this yesterday -> -1 DAYS\n
        The day before yesterday -> before and yesterday stack (-2 days)\n
        The problem is, pos and neg[-1] are time units themselves\n
However, yesterday (or tomorrow) which are implicit day units cannot be used at the same time as the explicit "day" unit. (Because "the day before yesterday day"" doesn't make sense)\n
    """
    # sentinel if clauses, ensures no errors will happen after them.

    if any((unit_stack(s), not only_one_offset(s))):
        raise UnexpectedBehaviourError(
            " 'Tomorrow' or 'Today' implicit units cannot be used with the day explicit unit and only one type of offset can be applied at a time ", relative_date)

    current_units: datetime_dict = Counter(re.findall(
        "".join(add_regex_boundaries(date_words)), s))

    def transform_into_regex(x: Sequence[str]): return re.fullmatch(
        "".join(add_regex_boundaries(x)), s)
    offset_type = ''
    if transform_into_regex(positive_offsets):
        offset_type = "+"
    # elif is necessary here, since string could have no matches in either case
    elif transform_into_regex(negative_offsets):
        offset_type = "-"
    positive_count, negative_count = (re.findall("".join(add_regex_boundaries(
        i)), s) for i in (positive_offsets, negative_offsets))

    off = Offset(offset_type,  len(positive_count)
                 or len(negative_count), current_units)
    return offset(off, anchor)
