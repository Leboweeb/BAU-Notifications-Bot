from __future__ import annotations
from datetime import datetime, timedelta
import re
from typing import Callable, Generator, Optional, Sequence
from utilities.common import UnexpectedBehaviourError, add_regex_boundaries, get_group, now


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


now = now.replace(**datetime_to_dict(now), tzinfo=None)

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
        # literally everything works except months because the gregorian calendar is stupid, seriously why the fuck do we use this shit
        transformed_date = anchor - \
            timedelta(days=simplified_dict["days"]) if operation == "-" else anchor + timedelta(
                days=simplified_dict["days"])
        # the month might change if a few days are added, so the anchor's month cannot be taken.
        return transformed_date.replace(month=transformed_date.month - simplified_dict["months"], year=transformed_date.year - simplified_dict["years"]) if operation == "-" else transformed_date.replace(month=transformed_date.month + simplified_dict["months"], year=transformed_date.year + simplified_dict["years"])
    return convert_unit


subtract_from_now = _change_dt(now)


class RelativeDate:
    positive_offsets, negative_offsets = (
        ("next ", "after", "following"),
        ("last", "before", "previous")
    )

    def __init__(self, string: str, anchor: datetime = now) -> None:
        self.string, self.sentences = string.lower(), string.lower().split(".")
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
            if source:
                yield self.mode(sentence), sentence
            yield self.mode(sentence)

    def natural_language_mode(self, sentence: str) -> Optional[datetime]:
        """
        Splits a single sentence based on english grammar.
        That is, only a single time unit(there can be more than one modifier though) can be in a sentence.
        Example : The exam will be next week. However, for another section it'll be after next week.
        ---------------------------^----^---------------------------------------------^----^----^----
                                modifier / time unit                                 2 modifiers / time unit

        use the mode_functor method to apply this over several strings (usually a list of sentences)
        """
        FIND_TIME_UNIT_REGEX = r"((next|after|this|following|ago|before|last|previous|)\s(day|week|month|year|decade|century))|(tomorrow|today|yesterday|before yesterday|after tomorrow)"
        current_unit = get_group(
            re.search(FIND_TIME_UNIT_REGEX, sentence, re.MULTILINE))

        def find_offsets():
            def find_in_sentence(seq: Sequence[str]): return re.findall(
                add_regex_boundaries(seq), sentence)
            p_ve_matches, n_ve_matches = len(find_in_sentence(RelativeDate.positive_offsets)), len(
                find_in_sentence(RelativeDate.negative_offsets))
            if not bool(p_ve_matches) ^ bool(n_ve_matches):
                raise UnexpectedBehaviourError(
                    "exactly 1 type of time unit can be present in a sentence", find_offsets)
            return (p_ve_matches, n_ve_matches)
        # 0 or 2 matches found (only 1 time unit can be in a sentence)
        if len(re.findall(FIND_TIME_UNIT_REGEX, sentence, re.MULTILINE)) in range(0, 3, 2) or current_unit is None:
            return None
        dates = {"tomorrow": self.anchor + timedelta(
            days=1), "today": self.anchor, "yesterday": self.anchor - timedelta(days=1), "after tomorrow": self.anchor + timedelta(days=2), "before yesterday": self.anchor - timedelta(days=2)}

        _curr_date = dates.get(current_unit)
        if _curr_date:
            return _curr_date
        current_unit = re.split("\s", current_unit)[1]

        try:
            offsets = find_offsets()
        except UnexpectedBehaviourError:
            return None
        _transform_date = _change_dt(self.anchor, "+" if offsets[0] else "-")
        # count the number of offsets and increase (or decrease) the
        # anchor, assuming there is only one type of operation happening
        return _transform_date({current_unit: list(filter(None, offsets))[0]})

    def mode_factory(self):
        if re.search(r"\d+ \w+ ago", self.string):
            return self.find_relative_date
        else:
            return self.natural_language_mode
