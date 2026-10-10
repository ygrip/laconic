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
        records = [event(stop=stop) for stop in ('stop', 'toolUse', 'length')]
        records += [event(kind=kind, usage={'input': 100}) for kind in ('message_start', 'message_update', 'tool_result')]
        records += [event(role='toolResult', usage={'input': 100}), event(role='user', usage={'input': 100})]
        records += [event(stop=stop, usage={'input': 100}) for stop in ('error', 'aborted', None)]
        records += [{'type': 'message_end', 'message': {'role': 'assistant'}}]
        self.assertEqual(summarize(records), dict(calls=3, input=0, output=0, cacheRead=0,
                                                  cacheWrite=0, totalTokens=0))

    def test_partial_usage_and_supplied_total_are_ignored(self):
        records = [event(usage={'input': 2, 'cacheRead': 3, 'reasoning': 4, 'totalTokens': 999}),
                   event(stop='length', usage={'output': 5, 'cacheWrite': 7})]
        self.assertEqual(summarize(records), dict(calls=2, input=2, output=5, cacheRead=3,
                                                  cacheWrite=7, totalTokens=17))

    def test_cli_fixture_with_blank_lines(self):
        root = Path(__file__).resolve().parent
        run = subprocess.run([sys.executable, str(root / 'usage_summary.py'), str(root / 'session.jsonl')],
                             capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(run.stdout), dict(calls=2, input=150, output=35,
                                                      cacheRead=50, cacheWrite=10, totalTokens=245))
        self.assertEqual(run.stderr, '')


if __name__ == '__main__':
    unittest.main()
