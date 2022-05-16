from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from typing import Callable, Generator, Iterable, Sequence
from utilities.common import UnexpectedBehaviourError, add_regex_boundaries, get_group, to_natural_str


datetime_dict = dict[str, int]
POSITIVE_OFFSETS, NEGATIVE_OFFSETS = (
    ("next", "after", "this", "following"), ("ago", "before", "last", "previous"))
temp = ("today", "tomorrow", "day", "week",
        "month", "year", "decade", "century", 'days', 'weeks', 'months', 'years', 'decades', 'centuries')
DATE_UNITS = ("day", "week", "month", "year", "decade", "century")
DATE_WORDS: dict[str, str] = dict(
    zip(temp[8:], temp[2:8])) | {i: i for i in temp[2:8]}


def datetime_to_dict(dt: datetime) -> datetime_dict: return {
    "year": dt.year, "month": dt.month, "day": dt.day}


def replace_dt_with_dict(dt: datetime, dt_dict: datetime_dict):
    return dt.replace(**dt_dict, tzinfo=None)


DAYS, MONTHS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"), ("January",
                                                                                                "February", "March", "April", "June", "July", "August", "September", "October", "November", "December")


def _change_dt(anchor: datetime, operation: str = '-') -> Callable[[datetime_dict], datetime]:
    # less error prone date subtraction or addition api
    if operation not in ("+", "-"):
        raise UnexpectedBehaviourError(
            f"Operation type {operation} not defined in datetime context", _change_dt)

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


class RelativeDate:

    def __init__(self, string: str, anchor: datetime = datetime.now()) -> None:
        self.string , self.sentences  = string.lower() , string.lower().split(".")
        self.mode = self.mode_factory()
        self.anchor = anchor

    def find_relative_date(self, sentence: str) -> datetime:
        """
        Finds a relative date in a single sentence or word, use 
        find_relative dates to get a generator of all relative dates possible
        ex : 1 day ago -> Monday 25 April 2022 if the current date is Tue-Apr-26-2022
        """
        # remove unnecessary characters that are not numbers or alphabet letters
        sentence = re.sub(r"[^a-zA-Z0-9\s]", "", sentence)
        offset = _change_dt(self.anchor)

        class Proxy:
            pass
        p, split = Proxy(), sentence.split(" ")
        if len(split) > 1:
            for i, j in enumerate(split):
                if j.isdigit() and split[i + 1] in DATE_WORDS:
                    # p.__dict__ has type dict[str, int]
                    setattr(
                        p, DATE_WORDS[split[i + 1].lower()], int(j))
        return offset(p.__dict__)


    def generate_results(self, source: bool = False) -> Generator[datetime, None, None] | Generator[tuple[datetime, str], None, None]:
        """
        apply the current mode (automatically) over a list of strings since each method accepts only one string and get
        a generator of datetime objects instead of only one. Useful for parsing natural text 
        """
        for sentence in self.sentences:
            yield self.mode(sentence) if not source else self.find_relative_date(sentence), sentence

    def natural_language_mode(self, sentence: str) -> datetime:
        """
        Splits a single sentence based on english grammar.
        That is, only a single time unit(there can be more than one modifier though) can be in a sentence.
        Example : The exam will be next week. However, for another section it'll be after next week.
        ---------------------------^----^---------------------------------------------^----^----^----
                                modifier / time unit                                 2 modifiers / time unit

        use the mode_functor method to apply this over several strings (usually a list of sentences)
        """
        POSITIVE_OFFSETS, NEGATIVE_OFFSETS = (
            ("next", "after", "this"), ("ago", "before", "last"))
        FIND_TIME_UNIT_REGEX = r"((next|after|this|following|ago|before|last|previous|)\s(day|week|month|year|decade|century))|(tomorrow|today|yesterday)"
        current_unit = get_group(re.search(FIND_TIME_UNIT_REGEX, sentence , re.MULTILINE))
        if len(re.findall(FIND_TIME_UNIT_REGEX, sentence, re.MULTILINE)) in range(0,2,2) or current_unit is None: # 0 or 2 matches found (only 1 time unit can be in a sentence)
            raise UnexpectedBehaviourError("too many or no relative time matches found", RelativeDate)
        if current_unit == "today":
            return self.anchor
        # remaining logic here  


    def mode_factory(self):
        if re.search(r"\d+ \w+ ago", self.string):
            return self.find_relative_date
        else:
            return self.natural_language_mode


# The natural language mode helper  method in the RelativeDate class can format the result as a string
positive_offsets, negative_offsets = (
    ("next ", "after", "following", "tomorrow"),
    ("last", "before", "previous", "yesterday")
)


def unit_stack(s: str):
    # yesterday, tomorrow, and day should not be in the same sentence
    day_units: tuple[str, ...] = (
        DATE_UNITS[0], positive_offsets[-1], negative_offsets[-1])
    return len(re.findall("|".join(day_units), s)) > 1


def only_one_offset(s: str):
    def found_any_in_str(
        coll: Iterable[str]): return any(i in s for i in coll)
    return found_any_in_str(positive_offsets) ^ found_any_in_str(negative_offsets)


def offset(offset_obj: Offset, dt: datetime) -> datetime | None:
    transform_fn = _change_dt(dt, offset_obj.offset_type)
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
        add_regex_boundaries(DATE_UNITS), s))

    def transform_into_regex(x: Sequence[str]): return re.fullmatch(
        add_regex_boundaries(x), s)
    offset_type = ''
    if transform_into_regex(positive_offsets):
        offset_type = "+"
    # elif is necessary here, since string could have no matches in either case
    elif transform_into_regex(negative_offsets):
        offset_type = "-"
    positive_count, negative_count = (re.findall(add_regex_boundaries(
        i), s) for i in (positive_offsets, negative_offsets))

    off = Offset(offset_type,  len(positive_count)
                 or len(negative_count), current_units)
    return offset(off, anchor)
