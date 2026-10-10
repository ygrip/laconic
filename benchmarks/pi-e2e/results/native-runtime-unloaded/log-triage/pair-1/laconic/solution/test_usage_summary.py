import json
import subprocess
import sys
import unittest
from pathlib import Path

from usage_summary import summarize


def event(kind='message_end', role='assistant', stop='stop', usage=None):
    return dict(type=kind, message=dict(role=role, stopReason=stop, usage=usage or {}))


class UsageTests(unittest.TestCase):
    def test_completed(self):
        self.assertEqual(summarize([event(usage=dict(input=10, output=5))])['calls'], 1)

    def test_streaming_is_not_a_call(self):
        self.assertEqual(summarize([event(kind='message_update')])['calls'], 0)

    def test_cache_is_included(self):
        result = summarize([event(usage=dict(input=10, output=5, cacheRead=8, cacheWrite=2))])
        self.assertEqual(result['totalTokens'], 25)
        self.assertEqual(result['cacheRead'], 8)
        self.assertEqual(result['cacheWrite'], 2)

    def test_reasoning_is_not_added_twice(self):
        self.assertEqual(summarize([event(usage=dict(output=5, reasoning=3))])['output'], 5)

    def test_only_completed_assistant_end_events_count(self):
        records = [event(stop=stop, usage={'input': 100}) for stop in ('stop', 'toolUse', 'length')]
        records += [event(kind=kind, usage={'input': 1000}) for kind in ('message_start', 'message_update')]
        records += [event(role='toolResult', usage={'input': 1000})]
        records += [event(stop=stop, usage={'input': 1000}) for stop in ('error', 'aborted', None)]
        self.assertEqual(summarize(records), dict(calls=3, input=300, output=0,
                                                  cacheRead=0, cacheWrite=0, totalTokens=300))

    def test_missing_usage_and_fields_and_untrusted_totals(self):
        records = [
            {'type': 'message_end', 'message': {'role': 'assistant', 'stopReason': 'length'}},
            event(usage={'input': 4, 'output': 5, 'cacheRead': 6, 'cacheWrite': 7,
                         'reasoning': 3, 'totalTokens': 999}),
            event(stop='toolUse', usage={'cacheWrite': 2, 'totalTokens': 500}),
        ]
        self.assertEqual(summarize(records), dict(calls=3, input=4, output=5,
                                                  cacheRead=6, cacheWrite=9, totalTokens=24))

    def test_cli_fixture_with_blank_lines(self):
        script = Path(__file__).with_name('usage_summary.py')
        fixture = Path(__file__).with_name('session.jsonl')
        output = subprocess.check_output([sys.executable, str(script), str(fixture)], text=True)
        self.assertEqual(json.loads(output), dict(calls=2, input=150, output=35,
                                                  cacheRead=50, cacheWrite=10, totalTokens=245))
        self.assertEqual(len(output.splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
