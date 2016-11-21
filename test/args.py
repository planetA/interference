#!/usr/bin/env python

import unittest

from scripts.interference import Filter


class TestFilterObject(unittest.TestCase):
    def test_benchname(self):
        filter_str = 'prog=ep:nodes=8'
        filter = Filter.create_filter(filter_str)
        self.assertEqual(filter.params['prog'], ['ep'])
        self.assertEqual(filter.params['nodes'], ['8'])

    def test_benchobj(self):
        class Bench:
            def __init__(self, prog, nodes):
                self.prog = prog
                self.nodes = nodes

        bench_pass = Bench('ep', '8')
        bench_fail = Bench('ep', '4')

        filter_str = 'prog=ep:nodes=8'
        filter = Filter.create_filter(filter_str)
        self.assertEqual(filter.skip(bench_pass), False)
        self.assertEqual(filter.skip(bench_fail), True)


if __name__ == '__main__':
    unittest.main()