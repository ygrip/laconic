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
    def test_completed_messages_sum_only_usage_components(self):
        records = [
            event(stop='stop', usage=dict(input=10, output=5, cacheRead=8,
                                          cacheWrite=2, reasoning=3, totalTokens=999)),
            event(stop='toolUse', usage=dict(input=4, cacheRead=6)),
            event(stop='length', usage=dict(output=7, cacheWrite=1)),
            dict(type='message_end', message=dict(role='assistant', stopReason='stop')),
        ]
        self.assertEqual(summarize(records), dict(
            calls=4, input=14, output=12, cacheRead=14, cacheWrite=3, totalTokens=43,
        ))

    def test_non_completed_events_are_ignored(self):
        usage = dict(input=100, output=20, cacheRead=30, cacheWrite=40)
        records = [
            event(kind='message_start', usage=usage),
            event(kind='message_update', usage=usage),
            event(kind='tool_result', usage=usage),
            event(role='toolResult', usage=usage),
            event(role='user', usage=usage),
            event(stop='error', usage=usage),
            event(stop='aborted', usage=usage),
            event(stop=None, usage=usage),
            dict(type='message_end'),
        ]
        self.assertEqual(summarize(records), dict(
            calls=0, input=0, output=0, cacheRead=0, cacheWrite=0, totalTokens=0,
        ))

    def test_cli_ignores_blank_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text('\n  \n' + json.dumps(event(usage=dict(input=2, output=3))) + '\n\n')
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).with_name('usage_summary.py')), str(path)],
                capture_output=True, text=True, check=True,
            )
        self.assertEqual(json.loads(completed.stdout), dict(
            calls=1, input=2, output=3, cacheRead=0, cacheWrite=0, totalTokens=5,
        ))
        self.assertEqual(len(completed.stdout.splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
