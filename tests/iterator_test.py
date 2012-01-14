import sys
import os.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import unittest
from tipprapi.tipprapi import ResultIterator, PAGE_SIZE

class IteratorTest(unittest.TestCase):

    def testSimplePagination(self):
        PAGES = 2
        def fakeAPI(params):
            data = [range(PAGE_SIZE * p, PAGE_SIZE * (p + 1)) for p in xrange(PAGES)]
            return {
                    'filtered_count': len(data) * PAGE_SIZE,
                    'promotions'    : data[params['page_start']]
                    }
        it = ResultIterator('promotions', lambda params: fakeAPI(params), {})
        collected = [r for r in it]
        self.assertEquals(collected, range(0, PAGE_SIZE*PAGES))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(IteratorTest)

if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2).run(suite())

