from datetime import datetime
from types import FunctionType
import unittest
from functions import TelegramInterface
from idle import autoremind_worker, filter_by_type_worker, search_notifications
from utilities.async_functions import prep_courses, datefinder
from utilities.common import coerce_to_none, flattening_iterator, my_format, pad_iter, run, RelativeDates


def begin_test(obj: unittest.TestCase, cases: list, assertions: tuple, function: FunctionType = None, messages=None):
    if function:
        cases = list(function(i) for i in cases)

    def _check(case, assertion, message=None):
        if not message:
            obj.assertEqual(case, assertion)
        else:
            obj.assertEqual(case, assertion, message)
    messages = pad_iter(messages, None, len(assertions))
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
        def flattener_proxy(x): return tuple(flattening_iterator(x))
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
        def test_relative_date_mode():
            cases = tuple(RelativeDates(i, datetime(2022, 3 , 25 ) ).parse_number_mode() for i in ("1 day ago", "1 year ago", "2 months ago",
                                                                         "", "1", "1234411 ; ';' ;''''", "___________"))
            begin_test(self, cases,
                       ("Thursday March 24 2022", "Thursday March 25 2021",
                        "Tuesday January 25 2022",  None, None, None, None),
                       messages=tuple(f"Case {i}" for i in range(len(cases))),
                       )
        test_relative_date_mode()


class BotCommandsSuite(unittest.TestCase):
    QUERIES = ("midterm", "on campus", "session")

    def test_date_getter(self):
        test_thing = datetime(2022, 3, 19)
        cases = ("Saturday March 19", "Sat march 19",
                 "sat March 19", "sat mar 19", "Saturday March 19 2022")
        for case in cases:
            self.assertTrue(test_thing in datefinder.find_dates(
                case), "Should be equal to the Saturday datetime object")

    def test_autoremind(self):
        stuff = autoremind_worker()
        self.assertTrue(stuff, "Should not be empty")

    def test_search_and_filter(self):
        for query in BotCommandsSuite.QUERIES:
            self.assertTrue(search_notifications(query))
            self.assertEqual(filter_by_type_worker(
                query), None, "Should not fail with junk words")

    def test_name_wrapper(self):
        t = TelegramInterface()
        # FIRST_NOTIFICATION = t.notifications[0]
        cases = ("math 283",
                 "electric", "comp 225", "blah blah")
        assertions = ("Differential Equations",
                      "electric circuits 1", "COMP225", "blah blah")

        messages = ("Should handle course codes",
                    "Should handle course names",
                    "Should handle capitalized course names",
                    "Should get last match if multiple courses collide",
                    "Should not fail on junk names")
        essential_tests = tuple(t.name_wrapper(i) for i in cases[:-1])
        begin_test(self, essential_tests, assertions, messages=messages)
        self.assertNotEqual(
            messages, None, "Should show notifications for cases")
        self.assertIsNone(filter_by_type_worker(cases[-1]))


if __name__ == "__main__":
    unittest.main()
    # suite = unittest.TestSuite()
    # current_class = SanityChecks
    # current_function = SanityChecks.test_flattening_iterator
    # suite.addTest(current_class(
    #     current_function.__name__))
    # runner = unittest.TextTestRunner()
    # runner.run(suite)
