from datetime import datetime
from itertools import starmap
import unittest
from functions import TelegramInterface
from idle import autoremind_worker, filter_by_type_worker, search_notifications
from utilities.async_functions import prep_courses
from utilities.common import coerce_to_none, date_calculator, flattening_iterator, matches_attribute, my_format, pad_iter, run


def run_suites(suite=None, func=None):
    if all((i is None for i in (suite, func))):
        unittest.main()
    else:
        suite = unittest.TestSuite()
        suite.addTest(suite(func.__name__))
        runner = unittest.TextTestRunner()
        runner.run(suite)


def test_prepper(obj, cases, assertions, messages=None, function=None):
    if function:
        cases = (function(i) for i in cases)

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
        cases = [pad_iter(i, None, 2) for i in cases]
        assertions = (("fag", None), ("fag", None), (object, object),
                      (object, None), (1, None), (False, None))
        messages = ("Should handle a list of strings", "Should handle a string", "Should handle a tuple of objects",
                    "Should handle a tuple of objects", "Should handle numbers", "Should handle boolean values")
        test_prepper(self, cases, assertions, messages)
        self.assertEqual(pad_iter((1, 2, 3), (False,) * 4), (1,
                         2, 3, False), "Should work without an amount as well")

    def test_flattening_iterator(self):
        cases, assertions, messages = [
            ("Meow", True, [1, 2]), ((i for i in range(2)), "Penos", object)], (("Meow", True, 1, 2), (0, 1, "Penos", object)), ("Should Ignore strings", "Should exhaust generators as well")
        cases = [tuple(flattening_iterator(i)) for i in cases]
        test_prepper(self, cases, assertions, messages)

    def test_course_objects(self):
        courses: set = run(prep_courses())
        my_format(courses, "Courses set (each course object is unique)")
        electricity_course = matches_attribute(
            courses, "name", "Electricity and Magnetism", True)
        self.assertTrue(electricity_course in courses,
                        "Testing subject should have a course object")
        courses.remove(electricity_course)
        self.assertTrue(courses,
                        "Should get the other courses")

    def test_date_calculator(self):
        def datetime_attrs(x: datetime): return (
            x.day, x.hour, x.minute, x.second)

        def represent_difference(input):
            r = {k : v for k,v in zip(("day","hour","minute","second"), input)}
            return datetime_attrs(datetime.now().replace(**r))
        container = (
            starmap(lambda x: date_calculator(x), ("2 hours 37 mins ago",
                "1 day 2 hours ago", "29 days 2 hours ago")),
            [represent_difference(i) for i in ((0,2,37,0), (1,2,0,0),(29,2,0,0))])
        cases, assertions = container
        test_prepper(self, cases, assertions, function=datetime_attrs)


class BotCommandsSuite(unittest.TestCase):
    QUERIES = ("midterm", "on campus", "THE NEXT SESSION")

    def test_autoremind(self):
        stuff = autoremind_worker()
        self.assertTrue(stuff, "Should not be empty")
        # self.assertTrue(len(stuff) > 2)

    def test_search_and_filter(self):
        for query in BotCommandsSuite.QUERIES:
            self.assertTrue(search_notifications(query))
            self.assertEqual(filter_by_type_worker(
                query), None, "Should not fail with junk words")

    def test_filter(self):
        t = TelegramInterface()
        # FIRST_NOTIFICATION = t.notifications[0]
        cases = ("math 283", "calculus", "CALCULUS",
                 "electric", "comp 225", "blah blah")
        assertions = ("Differential Equations", "Calculus",
                      "Calculus", "Electricity and Magnetism", "COMP225", "blah blah")
        messages = ("Should handle course codes",
                    "Should handle course names",
                    "Should handle capitalized course names",
                    "Should get last match if multiple courses collide",
                    "Should not fail on junk names")
        test_prepper(self, cases=cases, assertions=assertions,
                     messages=messages, function=t.name_wrapper)
        for i in cases[:-1]:
            messages = filter_by_type_worker(
                i)
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
