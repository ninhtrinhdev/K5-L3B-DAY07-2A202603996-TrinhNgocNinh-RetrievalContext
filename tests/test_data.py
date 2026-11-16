"""Contract checks for the real Day 7 data (Day 6 WHO pre-eclampsia corpus). Skipped if data is not exported."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'starter'))
from baseline import validate  # noqa: E402

DATA = ROOT / 'data'
HAVE = all((DATA / n).exists() for n in ('chunks.json', 'questions.json', 'agent_cases.json'))


@unittest.skipUnless(HAVE, 'run scripts/export_day6.py and scripts/build_questions.py first')
class RealDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load = lambda n: json.loads((DATA / n).read_text(encoding='utf-8'))
        cls.chunks, cls.answerable, cls.cases = load('chunks.json'), load('questions.json'), load('agent_cases.json')

    def test_chunk_ids_unique_and_traceable(self):
        ids = [c['id'] for c in self.chunks]
        self.assertEqual(len(ids), len(set(ids)))
        for c in self.chunks:
            self.assertTrue(c['source_id'] and c['source'] and isinstance(c['page'], int))
            self.assertEqual(c['metadata']['day6_chunk_id'], c['id'])

    def test_counts_meet_minimum(self):
        count = lambda split, ans: sum(1 for q in self.cases if q['split'] == split and q['answerable'] is ans)
        self.assertGreaterEqual(count('dev', True), 15)
        self.assertGreaterEqual(count('dev', False), 2)
        self.assertGreaterEqual(count('test', True), 5)
        self.assertGreaterEqual(count('test', False), 2)
        self.assertGreaterEqual(len(self.cases), 24)

    def test_gold_is_exact_substring_of_a_chunk_on_the_page(self):
        for split in ('dev', 'test'):
            validate(self.chunks, [q for q in self.answerable if q['split'] == split])

    def test_unanswerable_have_reason_and_no_gold(self):
        for q in self.cases:
            if not q['answerable']:
                self.assertTrue(q['absence_reason'].strip())
                self.assertEqual(q['expected_behavior'], 'search_and_abstain')
                self.assertNotIn('gold', q)

    def test_dev_and_test_questions_disjoint(self):
        dev = {q['question'].casefold() for q in self.cases if q['split'] == 'dev'}
        test = {q['question'].casefold() for q in self.cases if q['split'] == 'test'}
        self.assertFalse(dev & test)
        self.assertEqual(len({q['id'] for q in self.cases}), len(self.cases))


if __name__ == '__main__':
    unittest.main()
