import json
from pathlib import Path
import subprocess
import sys
import unittest
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

    def test_only_completed_assistant_messages_count(self):
        records = [event(kind=kind, usage=dict(input=100))
                   for kind in ('message_start', 'message_update', 'message')]
        records += [event(role='toolResult', usage=dict(input=100)),
                    event(stop='error', usage=dict(input=100)),
                    event(stop='aborted', usage=dict(input=100)),
                    event(stop=None, usage=dict(input=100)),
                    {'type': 'message_end'},
                    event(stop='stop', usage=dict(input=1)),
                    event(stop='toolUse', usage=dict(output=2)),
                    event(stop='length', usage=dict(cacheRead=3))]
        self.assertEqual(summarize(records), dict(calls=3, input=1, output=2,
                                                  cacheRead=3, cacheWrite=0, totalTokens=6))

    def test_missing_usage_and_untrusted_totals(self):
        records = [{'type': 'message_end', 'message': {'role': 'assistant', 'stopReason': 'stop'}},
                   event(usage=dict(input=4, output=5, cacheRead=6, cacheWrite=7,
                                    reasoning=3, totalTokens=999))]
        self.assertEqual(summarize(records), dict(calls=2, input=4, output=5,
                                                  cacheRead=6, cacheWrite=7, totalTokens=22))

    def test_cli_fixture_ignores_blank_lines(self):
        directory = Path(__file__).resolve().parent
        process = subprocess.run([sys.executable, str(directory / 'usage_summary.py'),
                                  str(directory / 'session.jsonl')],
                                 capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(process.stdout),
                         dict(calls=2, input=150, output=35, cacheRead=50,
                              cacheWrite=10, totalTokens=245))
        self.assertEqual(len(process.stdout.splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
