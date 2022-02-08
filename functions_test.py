import unittest




def run_suites(suite=None, func=None):
    if all((i == None for i in (suite, func))):
        unittest.main()
    else:
        suite = unittest.TestSuite()
        suite.addTest(suite(func.__name__))
        runner = unittest.TextTestRunner()
        runner.run(suite)


def test_prepper(cases, assertions, messages):
    for i,j,k in zip(cases,assertions,messages):
        unittest.TestCase.assertEqual(i,j,k)


class SanityChecks(unittest.TestCase):
    pass

    


if __name__ == "__main__":
    unittest.main()
    # suite = unittest.TestSuite()
    # suite.addTest(SanityChecks(SanityChecks.test_utility_functions.__name__))
    # runner = unittest.TextTestRunner()
    # runner.run(suite)
