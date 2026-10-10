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
        ignored += [event(role='toolResult', usage={'input': 100})]
        ignored += [event(stop=stop, usage={'input': 100})
                    for stop in ('error', 'aborted', None)]
        ignored += [{'type': 'message_end'}, {'type': 'message_end', 'message': {'role': 'assistant'}}]
        counted = [event(stop=stop, usage={'input': 1})
                   for stop in ('stop', 'toolUse', 'length')]
        self.assertEqual(summarize(ignored + counted), dict(
            calls=3, input=3, output=0, cacheRead=0, cacheWrite=0, totalTokens=3))

    def test_missing_usage_and_supplied_totals_are_ignored(self):
        records = [
            {'type': 'message_end', 'message': {'role': 'assistant', 'stopReason': 'stop'}},
            event(stop='length', usage={'input': 4, 'output': 5, 'cacheRead': 6,
                                        'cacheWrite': 7, 'reasoning': 3, 'totalTokens': 999}),
        ]
        self.assertEqual(summarize(records), dict(
            calls=2, input=4, output=5, cacheRead=6, cacheWrite=7, totalTokens=22))

    def test_cli_fixture_with_blank_lines(self):
        root = Path(__file__).resolve().parent
        completed = subprocess.run(
            [sys.executable, str(root / 'usage_summary.py'), str(root / 'session.jsonl')],
            capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(completed.stdout), dict(
            calls=2, input=150, output=35, cacheRead=50, cacheWrite=10, totalTokens=245))
        self.assertEqual(len(completed.stdout.splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
