import json
import subprocess
import sys
import tempfile
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
            event(role='user', usage=dict(input=100)),
            event(stop='error', usage=dict(input=100)),
            event(stop='aborted', usage=dict(input=100)),
            event(stop=None, usage=dict(input=100)),
            dict(type='message_end'),
            event(stop='stop', usage=dict(input=1)),
            event(stop='toolUse', usage=dict(output=2)),
            event(stop='length', usage=dict(cacheRead=3, cacheWrite=4)),
        ]
        self.assertEqual(summarize(records), dict(
            calls=3, input=1, output=2, cacheRead=3, cacheWrite=4, totalTokens=10
        ))

    def test_missing_usage_and_untrusted_totals(self):
        records = [
            dict(type='message_end', message=dict(role='assistant', stopReason='stop')),
            event(usage=dict(input=10, output=5, cacheRead=8, cacheWrite=2,
                             reasoning=4, totalTokens=999)),
        ]
        self.assertEqual(summarize(records), dict(
            calls=2, input=10, output=5, cacheRead=8, cacheWrite=2, totalTokens=25
        ))

    def test_cli_skips_blank_lines_and_prints_one_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text('\n' + json.dumps(event(usage=dict(input=7))) + '\n  \n')
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).with_name('usage_summary.py')), str(path)],
                capture_output=True, text=True, check=True,
            )
        self.assertEqual(completed.stderr, '')
        self.assertEqual(len(completed.stdout.splitlines()), 1)
        self.assertEqual(json.loads(completed.stdout), dict(
            calls=1, input=7, output=0, cacheRead=0, cacheWrite=0, totalTokens=7
        ))


if __name__ == '__main__':
    unittest.main()
