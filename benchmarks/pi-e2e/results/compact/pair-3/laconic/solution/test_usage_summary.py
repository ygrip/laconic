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

    def test_only_completed_assistant_messages_count(self):
        counted = [
            event(stop='stop', usage=dict(input=10, output=5, cacheRead=8,
                                          cacheWrite=2, reasoning=3, totalTokens=999)),
            event(stop='toolUse', usage=dict(output=7)),
            event(stop='length'),
            dict(type='message_end', message=dict(role='assistant', stopReason='stop')),
        ]
        ignored = [
            event(kind='message_start', usage=dict(input=100)),
            event(kind='message_update', usage=dict(input=100)),
            event(role='toolResult', usage=dict(input=100)),
            event(stop='error', usage=dict(input=100)),
            event(stop='aborted', usage=dict(input=100)),
            event(stop=None, usage=dict(input=100)),
        ]
        self.assertEqual(summarize(counted + ignored), dict(
            calls=4, input=10, output=12, cacheRead=8, cacheWrite=2, totalTokens=32))

    def test_fixture_cli(self):
        directory = Path(__file__).resolve().parent
        result = subprocess.run(
            [sys.executable, str(directory / 'usage_summary.py'), str(directory / 'session.jsonl')],
            capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), dict(
            calls=2, input=150, output=35, cacheRead=50, cacheWrite=10, totalTokens=245))


if __name__ == '__main__':
    unittest.main()
