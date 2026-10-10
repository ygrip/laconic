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
        records = [
            event(kind='message_start', usage=dict(input=100)),
            event(kind='message_update', usage=dict(input=100)),
            event(kind='tool_result', usage=dict(input=100)),
            event(role='toolResult', usage=dict(input=100)),
            event(stop='pending', usage=dict(input=100)),
            event(stop='error', usage=dict(input=100)),
            event(stop='aborted', usage=dict(input=100)),
            event(stop=None, usage=dict(input=100)),
            event(stop='stop', usage=dict(input=1)),
            event(stop='toolUse', usage=dict(output=2)),
            event(stop='length', usage=dict(cacheRead=3, cacheWrite=4)),
            dict(type='message_end', message=dict(role='assistant', stopReason='stop')),
        ]
        self.assertEqual(summarize(records), dict(
            calls=4, input=1, output=2, cacheRead=3, cacheWrite=4, totalTokens=10,
        ))

    def test_total_ignores_supplied_total_and_reasoning(self):
        self.assertEqual(summarize([event(usage=dict(
            input=10, output=5, cacheRead=8, cacheWrite=2,
            reasoning=3, totalTokens=999,
        ))]), dict(calls=1, input=10, output=5, cacheRead=8, cacheWrite=2, totalTokens=25))

    def test_cli_session_fixture(self):
        script = Path(__file__).with_name('usage_summary.py')
        session = Path(__file__).with_name('session.jsonl')
        output = subprocess.check_output([sys.executable, str(script), str(session)], text=True)
        self.assertEqual(json.loads(output), dict(
            calls=2, input=150, output=35, cacheRead=50, cacheWrite=10, totalTokens=245,
        ))


if __name__ == '__main__':
    unittest.main()
