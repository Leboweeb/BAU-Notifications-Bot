import asyncio
import json
import unittest
from functions import AsyncFunctions, FunctionFridge, file_handler, InputFilters, pad_iter, string_builder


def run(x): return asyncio.run(x)


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

    
    def test_fridge_class(self):
        def func_1(x): return x
        def func_2(x): return x**2
        fridge = FunctionFridge((func_1, 1), (func_2, 2))
        fridge.get_plate(func_1).run()
        self.assertEqual(len((fridge.__dict__)), 2,
                         "Should work for two regular functions")
        fridge = FunctionFridge((func_1, 1), (func_1, 1))
        dummy_list = (fridge.get_plate(func_1)*2)
        val1, val2 = dummy_list
        self.assertEqual(
            val1, val2, "Should store and run the same function twice with mul and rmul methods")
        val1, val2 = (2 * fridge.get_plate(func_1))
        self.assertEqual(
            val1, val2, "Should store and run the same function twice with mul and rmul methods")

        async def main(*args):
            return args

        fridge = FunctionFridge((main, (1, 2, 3, 4)))
        res = fridge.get_plate(main)
        res = res.run()
        self.assertEqual(res, (1, 2, 3, 4),
                         "Should run async coroutines as well and handle special *args and **kwargs syntax")
        self.assertEqual(FunctionFridge().__dict__, {},
                         "Should handle no input at all")

        def fag(): print(5)
        fridge = FunctionFridge(fag)
        self.assertEqual(fridge.get_plate(fag).run(), None,
                         "Should handle running a function with no arguments.")

    def test_utility_functions(self):
        def test_pad_iter():
            cases = [pad_iter((1, 2, 3), 1, 3), pad_iter((1, 2, 3), (1, 2, 3), 3), pad_iter(
                1, (1, 2, 3)), pad_iter(1, 2, 5), pad_iter(object, (None, None)), pad_iter("fag", 2, 2)]
            assertions = [(1, 2, 3), (1, 2, 3), (1, 1, 2, 3),
                        (1, 2, 2, 2, 2, 2), (object, None, None), ("fag", 2, 2)]
            messages = ["Should return an unpadded iterable", "Should return an unpadded iterable", "Should handle non-iterables as well",
                        "Should handle non-iterables as well", "Should handle arbitrary data types", "Should handle strings as well"]
            for i,j,k in zip(*[cases,assertions,messages]):
                self.assertEqual(i,j,k)
        def test_str_builder():
            self.assertEqual(string_builder(set(),set()),"", "Should handle empty iterables")
            self.assertEqual(string_builder(object,object),None, "Should handle incorrect inputs")
            self.assertEqual(string_builder(("1","2","3"),("Fag","bag"),separator=""),"Fag : 1bag : 2","Should ignore extra arguments to each side (they should be symmetrical)")
            self.assertEqual(string_builder([1,2],[str(i) for i in range(1,3)],separator=""),"1 : 12 : 2","Should return in an expected form.")
            self.assertEqual(string_builder([1,2,None],[1,2,3],""),"1 : 12 : 2","Should filter out null values")
            self.assertEqual(string_builder([1,2,3],[1,2,None],""),"1 : 12 : 2","Should filter out null values")
        test_str_builder()

    def setUp(self) -> None :
        pass
        # res = file_handler("results.json")
        # try:
            # self.data = json.loads(res)[0]["data"]["notifications"]
        # except KeyError:
            # raise ValueError("The moodle webservice is down, try again")

    def test_thing(self):
        objects = asyncio.run(AsyncFunctions.get_data(self.data))
        self.assertTrue(all(i for i in objects))

    def test_api(self):
        def update_text(): return file_handler("mappings.json")
        try:
            cont = update_text()
        except FileNotFoundError:
            InputFilters.mapping_init()
            cont = update_text()
        if "view.php" in cont:
            run(AsyncFunctions.get_titles())

        self.assertTrue("view.php" not in cont)


if __name__ == "__main__":
    # unittest.main()
    suite = unittest.TestSuite()
    suite.addTest(SanityChecks(SanityChecks.test_utility_functions.__name__))
    runner = unittest.TextTestRunner()
    runner.run(suite)
