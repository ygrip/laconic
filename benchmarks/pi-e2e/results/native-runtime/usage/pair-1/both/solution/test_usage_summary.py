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
        ignored = [event(kind=kind, usage={'input': 100})
                   for kind in ('message_start', 'message_update', 'tool_result')]
        ignored += [event(role='toolResult', usage={'input': 100}),
                    event(role='user', usage={'input': 100})]
        ignored += [event(stop=stop, usage={'input': 100})
                    for stop in ('error', 'aborted', None)]
        ignored += [{'type': 'message_end', 'message': {'role': 'assistant'}},
                    {'type': 'message_end'}, {}]
        completed = [event(stop=stop, usage={'input': 2})
                     for stop in ('stop', 'toolUse', 'length')]
        self.assertEqual(summarize(ignored + completed), dict(
            calls=3, input=6, output=0, cacheRead=0, cacheWrite=0, totalTokens=6))

    def test_missing_usage_and_fields_count_as_zero(self):
        records = [{'type': 'message_end', 'message':
                    {'role': 'assistant', 'stopReason': 'stop'}},
                   event(stop='length', usage={'cacheWrite': 4})]
        self.assertEqual(summarize(records), dict(
            calls=2, input=0, output=0, cacheRead=0, cacheWrite=4, totalTokens=4))

    def test_totals_ignore_reasoning_and_supplied_total(self):
        result = summarize([event(usage=dict(input=10, output=5, cacheRead=8,
                                             cacheWrite=2, reasoning=3, totalTokens=999))])
        self.assertEqual(result, dict(calls=1, input=10, output=5,
                                      cacheRead=8, cacheWrite=2, totalTokens=25))

    def test_cli_fixture(self):
        script = Path(__file__).with_name('usage_summary.py')
        fixture = Path(__file__).with_name('session.jsonl')
        completed = subprocess.run([sys.executable, str(script), str(fixture)],
                                   capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(completed.stdout), dict(
            calls=2, input=150, output=35, cacheRead=50, cacheWrite=10,
            totalTokens=245))
        self.assertEqual(len(completed.stdout.splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
