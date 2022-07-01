from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import partial
from io import BufferedReader
import re
from typing import Optional
from utilities.common import DATA_DIR, IO_DATA_DIR, flattening_iterator, null_safe_chaining, to_natural_str
import requests
import PyPDF2

from utilities.time_parsing_lib import DAYS, MONTHS


def abbreviate(x): return x[:3]


PDF_URL = r"https://mis.bau.edu.lb/web/v12/PortalAssets/Calendar.pdf"
datetime_dict = dict[str, int]


def datetime_to_dict(dt: datetime) -> datetime_dict: return {
    "year": dt.year, "month": dt.month, "day": dt.day}


day_abbr, mon_abbr = (map(abbreviate, i) for i in (DAYS, MONTHS))
now = datetime(**datetime_to_dict(datetime.now()), tzinfo=None)


@dataclass
class SemesterMetaInfo:
    semester: str = field(init=False)
    semester_month_dict: dict[datetime, Optional[str]] = field(init=False)
    inverted_month_dict: dict[Optional[str], datetime] = field(init=False)


def find_certain_semester(info_obj: SemesterMetaInfo, query: str) -> Optional[datetime]:
    query = query.lower().capitalize()
    return info_obj.inverted_month_dict.get(query, None)


def _find_current_semester(info_obj: SemesterMetaInfo):
    semester_months = info_obj.semester_month_dict
    semester_list = sorted(flattening_iterator(semester_months, now))
    return semester_months[semester_list[semester_list.index(now) - 1]]


def find_week_of_datetime(dt: datetime): return dt - timedelta(days=dt.weekday())

def _find_week(info_obj: SemesterMetaInfo, week: int = 0, date: datetime = now):
    # find the current week if week = 0, otherwise find out when a particular week is
    semester, semester_dict = info_obj.semester, {
        v: k for k, v in info_obj.semester_month_dict.items()}
    FIRST_WEEK_DATE = semester_dict[semester.capitalize()]
    if week:
        return FIRST_WEEK_DATE + timedelta(weeks=week)
    count, curr_dt = 0, FIRST_WEEK_DATE

    def in_week(timestamp: datetime, ref: datetime):
        return find_week_of_datetime(timestamp) == find_week_of_datetime(ref)
    while not in_week(curr_dt, date):
        count += 1
        curr_dt += timedelta(weeks=1)
    return count


def _get_semester_dicts(text: str):
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
    return semester_months, {v: k for k, v in semester_months.items()}


def make_request():
    pdf_req = requests.get(PDF_URL)
    IO_DATA_DIR("smth.pdf", "wb", pdf_req.content)


def read_pdf(): return DATA_DIR.joinpath("smth.pdf").open("rb")


def get_pdf_text(fileobj: BufferedReader):
    text = PyPDF2.PdfFileReader(fileobj)
    page = text.pages[0]
    pdf_txt: str = page.extractText()
    pdf_txt = re.sub("\s", "", pdf_txt)
    return pdf_txt


def set_pdf(): return get_pdf_text(read_pdf())


pdf_text = set_pdf()


meta_inf = SemesterMetaInfo()
meta_inf.semester_month_dict, meta_inf.inverted_month_dict = _get_semester_dicts(
    pdf_text)
meta_inf.semester = _find_current_semester(meta_inf)


if max(meta_inf.semester_month_dict).year < now.year:
    make_request()
    pdf_text = set_pdf()
    meta_inf = SemesterMetaInfo()


# Constant to be used by external modules
FINAL_INFO_OBJ = deepcopy(meta_inf)
find_week_of_datetime = partial(_find_week, info_obj=FINAL_INFO_OBJ)
