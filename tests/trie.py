
from pprint import pprint
from dagcli.tries import TrieNode

def debuginfo(tnode: TrieNode):
    return {
        "terminal": tnode.terminal,
        "count": tnode.count,
        "children": {
            k: debuginfo(v) for k,v in tnode.children.items()
        }
    }

import unittest
class TestMethods(unittest.TestCase):
    def test_init(self):
        tn = TrieNode("")
        self.assertEqual(debuginfo(tn), {'children': {}, 'count': 0, 'terminal': False})

        tn.add_strings("app").terminal = True
        tn.add_strings("apple").terminal = True
        tn.add_strings("bad").terminal = True
        tn.add_strings("code").terminal = True
        tn.add_strings("cody").terminal = True
        tn.add_strings("cobb").terminal = True
        self.assertEqual(debuginfo(tn),
                         {'terminal': False, 'count': 6,
                          'children': {
                              'a': {'terminal': False, 'count': 2,
                                    'children': {
                                        'p': {'terminal': False, 'count': 2,
                                              'children': {
                                                  'p': {'terminal': True, 'count': 2,
                                                        'children': {
                                                            'l': {'terminal': False, 'count': 1,
                                                                  'children': {
                                                                      'e': {'terminal': True, 'count': 1,
                                                                            'children': {}}}}}}}}}},
                                'b': {'terminal': False, 'count': 1,
                                      'children': {
                                          'a': {'terminal': False, 'count': 1,
                                                'children': {
                                                    'd': {'terminal': True, 'count': 1,
                                                          'children': {}}}}}},
                                'c': {'terminal': False, 'count': 3,
                                      'children': {
                                          'o': {'terminal': False, 'count': 3,
                                                'children': {
                                                    'd': {'terminal': False, 'count': 2,
                                                          'children': {
                                                              'e': {'terminal': True, 'count': 1,
                                                                    'children': {}},
                                                              'y': {'terminal': True, 'count': 1,
                                                                    'children': {}}}},
                                                    'b': {'terminal': False,
                                                          'count': 1,
                                                          'children': {
                                                              'b': {'terminal': True, 'count': 1,
                                                                    'children': {}}}}}}}}}})

        self.assertEqual(tn.remove_string("application"), False)
        # Nothing should change when removing a non-existent val
        self.assertEqual(debuginfo(tn),
                         {'children':
                          {'a': {'children':
                            {'p': {'children':
                              {'p': {'children':
                                {'l': {'children':
                                  {'e': {'children': {}, 'count': 1, 'terminal': True}},
                                  'count': 1, 'terminal': False }},
                                'count': 2, 'terminal': True}},
                              'count': 2, 'terminal': False}},
                            'count': 2, 'terminal': False},
                           'b': {'children':
                                 {'a': {'children':
                                        {'d': {'children': {}, 'count': 1, 'terminal': True}},
                                       'count': 1, 'terminal': False}},
                                 'count': 1, 'terminal': False},
                           'c': {'children':
                                 {'o': {'children':
                                        {'b': {'children':
                                               {'b': {'children': {}, 'count': 1, 'terminal': True}},
                                               'count': 1, 'terminal': False},
                                         'd': {'children':
                                               {'e': {'children': {}, 'count': 1, 'terminal': True},
                                                'y': {'children': {}, 'count': 1, 'terminal': True}},
                                               'count': 2, 'terminal': False}},
                                        'count': 3, 'terminal': False}},
                                 'count': 3, 'terminal': False}},
                          'count': 6, 'terminal': False})

        self.assertEqual(tn.remove_string("app"), True)
        # Nothing should change when removing a non-existent val
        self.assertEqual(debuginfo(tn),
                         {'terminal': False, 'count': 5,
                          'children': {
                            'a': {'terminal': False, 'count': 1,
                                  'children': {
                                      'p': {'terminal': False, 'count': 1,
                                            'children': {
                                                'p': {'terminal': True, 'count': 1,
                                                      'children': {
                                                          'l': {'terminal': False, 'count': 1,
                                                                'children': {
                                                                    'e': {'terminal': True, 'count': 1,
                                                                          'children': {}}}}}}}}}},
                            'b': {'terminal': False, 'count': 1,
                                  'children': {
                                      'a': {'terminal': False, 'count': 1,
                                            'children': {
                                                'd': {'terminal': True, 'count': 1,
                                                      'children': {}}}}}},
                            'c': {'terminal': False, 'count': 3,
                                  'children': {
                                      'o': {'terminal': False, 'count': 3,
                                            'children': {
                                                'd': {'terminal': False, 'count': 2,
                                                      'children': {
                                                          'e': {'terminal': True, 'count': 1,
                                                                'children': {}},
                                                          'y': {'terminal': True, 'count': 1,
                                                                'children': {}}}},
                                                'b': {'terminal': False, 'count': 1,
                                                      'children': {
                                                          'b': {'terminal': True, 'count': 1,
                                                                'children': {}}}}}}}}}})

        self.assertEqual(tn.find_leaf("apple").path_to_root(), "apple")
if __name__ == '__main__':
    # Run with python -m unittest *.py
    unittest.main()
