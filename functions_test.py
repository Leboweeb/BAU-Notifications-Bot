from itertools import starmap
from types import FunctionType
from typing import Optional
import unittest
from utilities.async_functions import prep_courses
from utilities.common import UnexpectedBehaviourError, coerce_to_none, matches_attribute, my_format, pad_iter, run


def run_suites(suite=None, func=None):
    if all((i is None for i in (suite, func))):
        unittest.main()
    else:
        suite = unittest.TestSuite()
        suite.addTest(suite(func.__name__))
        runner = unittest.TextTestRunner()
        runner.run(suite)


class TestPrepper:
    def __init__(self, function: FunctionType, cases_and_assertions: tuple, messages: Optional[tuple] = None) -> None:
        self.function = function
        if not any(cases_and_assertions, messages):
            raise UnexpectedBehaviourError(
                "At least one case and assertion is needed", TestPrepper)
        self.messages = pad_iter(messages, None, len(cases_and_assertions))
        self.cases_and_assertions = tuple(
            starmap(lambda x, y, z: (function(x), y, z), (*cases_and_assertions, messages)))

    def test_prepper(self, obj):
        def _check(case, assertion, message=None):
            if not message:
                obj.assertEqual(case, assertion)
            else:
                obj.assertEqual(case, assertion, message)
        container = zip(
            self.cases_and_assertions[0], self.cases_and_assertions[1], self.messages)
        for i in container:
            _check(*i)


class SanityChecks(unittest.TestCase):

    def test_basic_functions(self):
        self.assertEqual(
            list(coerce_to_none(0, [], set(), tuple(), {})), [None] * 5)
        self.assertEqual(tuple(coerce_to_none(
            1, None, 0, object)), (1, None, None, object))

    def test_pad_iter(self):
        cases = [["fag"], "fag", (object, object), (object), 1, False]
        cases = [pad_iter(i, None, 2) for i in cases]
        assertions = [("fag", None), ("fag", None), (object, object),
                      (object, None), (1, None), (False, None)]
        messages = ["Should handle a list of strings", "Should handle a string""Should handle a tuple of objects",
                    "Should handle a tuple of objects", "Should handle numbers", "Should handle boolean values"]
        SanityChecks.test_prepper(self, cases, assertions, messages)
        self.assertEqual(pad_iter((1, 2, 3), (False,) * 4), (1,
                         2, 3, False), "Should work without an amount as well")

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


if __name__ == "__main__":
    # unittest.main()
    suite = unittest.TestSuite()
    suite.addTest(SanityChecks(SanityChecks.test_course_objects.__name__))
    runner = unittest.TextTestRunner()
    runner.run(suite)
