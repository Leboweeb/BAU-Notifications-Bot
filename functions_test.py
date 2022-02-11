import unittest
from utilities.common import coerce_to_none, pad_iter




def run_suites(suite=None, func=None):
    if all((i == None for i in (suite, func))):
        unittest.main()
    else:
        suite = unittest.TestSuite()
        suite.addTest(suite(func.__name__))
        runner = unittest.TextTestRunner()
        runner.run(suite)


def test_prepper(obj,cases, assertions, messages=None):
    def _check(case,assertion,message=None):
        if not message:
            obj.assertEqual(case,assertion)
        else:
            obj.assertEqual(case,assertion,message)
    if messages:
        container = zip(cases,assertions,messages)
    else:
        container = zip(cases,assertions)
    for i in container:
        _check(*i)


class SanityChecks(unittest.TestCase):
 
    def test_basic_functions(self):
        self.assertEqual(list(coerce_to_none(0,[],set(),tuple(),{})),[None]*5)
        self.assertEqual(tuple(coerce_to_none(1,None,0,object)),(1,None,None,object))
    
    def test_pad_iter(self):
        cases = [["fag"],"fag",(object,object),(object),1,False]
        cases = [pad_iter(i,None,2) for i in cases]
        assertions = [("fag",None),("fag",None),(object,object),(object,None),(1,None),(False,None)]
        messages = ["Should handle a list of strings","Should handle a string""Should handle a tuple of objects","Should handle a tuple of objects","Should handle numbers","Should handle boolean values"]
        test_prepper(self,cases,assertions,messages)
        self.assertEqual(pad_iter((1,2,3),(False,)*4),(1,2,3,False),"Should work without an amount as well")

if __name__ == "__main__":
    # unittest.main()
    suite = unittest.TestSuite()
    suite.addTest(SanityChecks(SanityChecks.test_pad_iter.__name__))
    runner = unittest.TextTestRunner()
    runner.run(suite)
