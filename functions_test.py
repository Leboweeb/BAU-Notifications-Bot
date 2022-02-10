import unittest
from functions import TelegramInterface
from idle import BotCommands
from utilities.common import autocorrect, coerce_to_none, flatten_iter




def run_suites(suite=None, func=None):
    if all((i == None for i in (suite, func))):
        unittest.main()
    else:
        suite = unittest.TestSuite()
        suite.addTest(suite(func.__name__))
        runner = unittest.TextTestRunner()
        runner.run(suite)


def test_prepper(obj,cases, assertions, messages):
    for i,j,k in zip(cases,assertions,messages):
        obj.assertEqual(i,j,k)


class SanityChecks(unittest.TestCase):
    
    def test_basic_functions(self):
        self.assertEqual(list(coerce_to_none(0,[],set(),tuple(),{})),[None]*5)
        self.assertEqual(tuple(coerce_to_none(1,None,0,object)),(1,None,None,object))
    
    def test_name_getter(self):
        t = TelegramInterface()
        index_getter = t.get_index_from_name
        self.assertEqual(t.get_name_from_index(index_getter("math 283")),"Differential Equations","Should get course names from codes")
        self.assertEqual(t.get_name_from_index(index_getter("calc")),"Calculus","Should get courses from short names as well.")
        self.assertEqual(t.get_name_from_index(index_getter("mathe 283")),"Differential Equations","Should get courses from misspelled course codes")
        self.assertEqual(t.get_name_from_index(index_getter("")),None,"Should handle invalid input")

if __name__ == "__main__":
    # unittest.main()
    suite = unittest.TestSuite()
    suite.addTest(SanityChecks(SanityChecks.test_working_autocorrect.__name__))
    runner = unittest.TextTestRunner()
    runner.run(suite)
