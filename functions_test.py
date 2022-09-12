from datetime import datetime, timedelta
import re
from types import FunctionType
from typing import Iterable, Optional
import unittest
from functions import TelegramInterface
from utilities.async_functions import prep_courses, datefinder
from utilities.common import coerce_to_none, flattening_iterator, my_format, pad_iter, run, to_natural_str
from utilities.time_parsing_lib import RelativeDate


def begin_test(obj: unittest.TestCase, cases: list, assertions: tuple, function: FunctionType = None, messages: Optional[Iterable[str]] = None):
    if function:
        cases = list(function(i) for i in cases)

    def _check(case, assertion, message=None):
        if not message:
            obj.assertEqual(case, assertion)
        else:
            obj.assertEqual(case, assertion, message)
    messages = (f"Case {i}" for i, _ in enumerate(
        cases)) if not messages else messages
    container = zip(cases, assertions, messages)
    for i in container:
        _check(*i)


class SanityChecks(unittest.TestCase):

    def test_basic_functions(self):
        self.assertEqual(
            list(coerce_to_none(0, [], set(), tuple(), {})), [None] * 5)
        self.assertEqual(tuple(coerce_to_none(
            1, None, 0, object)), (1, None, None, object))

    def test_pad_iter(self):
        cases = (["fag"], "fag", (object, object), (object), 1, False)
        assertions = (("fag", None), ("fag", None), (object, object),
                      (object, None), (1, None), (False, None))
        messages = ("Should handle a list of strings", "Should handle a string", "Should handle a tuple of objects",
                    "Should handle a tuple of objects", "Should handle numbers", "Should handle boolean values")
        self.assertEqual(pad_iter((1, 2, 3), (False,) * 4), (1,
                         2, 3, False), "Should work without an amount as well")
        cases = tuple(pad_iter(i, None, 2) for i in cases)
        begin_test(self, cases, assertions, messages=messages)

    def test_flattening_iterator(self):
        def flattener_proxy(x): return tuple(flattening_iterator(*x))
        cases, assertions, messages = [
            ("Meow", True, [1, 2]), ((i for i in range(2)), "Penos", object)], (("Meow", True, 1, 2), (0, 1, "Penos", object)), ("Should Ignore strings", "Should exhaust generators as well")
        begin_test(self, cases, assertions, flattener_proxy, messages)

    def test_course_objects(self):
        courses: set = run(prep_courses())
        my_format(courses, "Courses set (each course object is unique)")
        self.assertTrue(courses,
                        "Should get the other courses")
        self.assertTrue(len(courses) > 4)

    def test_date_calculator(self):
        anchor = datetime(2022, 3, 25)
        str_anc = to_natural_str(anchor)
        sentences = ("1 day ago",
                     "1 year ago",
                     "2 months ago",
                     "1 week, 1 day ago",
                     "1 week ,1 day ago , and 1 month",
                     "1 century ago",
                     "1 decade ago""",
                     "1",
                     "1234411 ; ';' ;''''",
                     "___________")
        obj = RelativeDate(".".join(sentences), anchor=anchor)
        assertions = ("Thursday March 24 2022",
                      "Thursday March 25 2021",
                      "Tuesday January 25 2022",
                      "Thursday March 17 2022",
                      "Thursday February 17 2022",
                      "Saturday March 25 1922",
                      "Sunday March 25 2012",
                      str_anc,
                      str_anc,
                      str_anc,
                      str_anc)
        begin_test(self, tuple(
            map(to_natural_str, obj.generate_results())), assertions)
        sentences = ("yesterday",
                     "before yesterday",
                     "last year",
                     "last week",
                     "before last month",
                     "last century",
                     "previous decade",
                     "tomorrow",
                     "after tomorrow",
                     "today",
                     "next week",
                     " after next week",
                     "next month",
                     "following year",
                     "after this decade",
                     "after this century")

        assertions = ("Thursday March 24 2022",
                      "Wednesday March 23 2022",
                      "Thursday March 25 2021",
                      "Friday March 18 2022",
                      "Tuesday January 25 2022",
                      "Saturday March 25 1922",
                      "Sunday March 25 2012",
                      "Saturday March 26 2022",
                      "Sunday March 27 2022",
                      str_anc,
                      to_natural_str(anchor + timedelta(7)),
                      to_natural_str(anchor + timedelta(14)),
                      "Monday April 25 2022",
                      to_natural_str(anchor.replace(year=anchor.year + 1)),
                      to_natural_str(anchor.replace(year=anchor.year + 10)),
                      to_natural_str(anchor.replace(year=anchor.year + 100)))
        obj = RelativeDate(".".join(sentences), anchor=anchor)
        cases = tuple(map(to_natural_str, obj.generate_results()))
        begin_test(self, cases=cases,
                   assertions=assertions)

    def test_date_getter(self):
        test_thing = datetime(2022, 3, 19)
        cases = ("Saturday March 19", "Sat march 19",
                 "sat March 19", "sat mar 19", "Saturday March 19 2022")
        for case in cases:
            self.assertTrue(test_thing in datefinder.find_dates(
                case), "Should be equal to the Saturday datetime object")

    def test_multiple_type_subjects(self):
        def generate_subjects(title: str) -> set[Optional[str]]:
            non_exam_types, exam_types = (
                "lab", "project", "session"), ("quiz", "test", "exam", "grades", "midterm")
            type_dict = dict.fromkeys(exam_types, "exam") | {
                name: name for name in non_exam_types}
            types: list[str] = re.findall(
                "|".join(flattening_iterator(non_exam_types, exam_types)), title)
            return set(map(lambda x: type_dict.get(x, None), types))

        cases, assertions = (("incomplete final exam", "semester grades", "null", "lab final makeup exam", "midterm exam",
                              "quiz 2 makeup", "final project", "lab session tomorrow", "session date changed"),
                             ({"exam"}, {"exam"}, set(),  {"lab", "exam"}, {"exam"}, {"exam"}, {"project"}, {"lab", "session"}, {"session"}))
        begin_test(self, cases, assertions, generate_subjects)


t = TelegramInterface()


if __name__ == "__main__":
    unittest.main()
    # suite = unittest.TestSuite()
    # current_class = SanityChecks
    # current_function = SanityChecks.test_flattening_iterator
    # suite.addTest(current_class(
    #     current_function.__name__))
    # runner = unittest.TextTestRunner()
    # runner.run(suite)
