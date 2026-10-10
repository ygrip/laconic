import json
import subprocess
import sys
import unittest
from pathlib import Path

from usage_summary import summarize


ROOT = Path(__file__).resolve().parent
ZERO = dict(calls=0, input=0, output=0, cacheRead=0, cacheWrite=0, totalTokens=0)


def event(kind='message_end', role='assistant', stop='stop', usage=None):
    message = dict(role=role, stopReason=stop)
    if usage is not None:
        message['usage'] = usage
    return dict(type=kind, message=message)


class UsageTests(unittest.TestCase):
    def test_only_completed_assistant_messages_count(self):
        ignored = [
            event(kind=kind, usage={'input': 100})
            for kind in ('message_start', 'message_update', 'tool_result')
        ] + [
            event(role='user', usage={'input': 100}),
            event(role='toolResult', usage={'input': 100}),
            event(stop='error', usage={'input': 100}),
            event(stop='aborted', usage={'input': 100}),
            event(stop=None, usage={'input': 100}),
            {'type': 'message_end'},
        ]
        self.assertEqual(summarize(ignored), ZERO)
        self.assertEqual(summarize(ignored + [event(stop=stop) for stop in ('stop', 'toolUse', 'length')]),
                         dict(ZERO, calls=3))

    def test_usage_and_total_are_derived_without_double_counting_reasoning(self):
        records = [
            event(usage=dict(input=10, output=5, cacheRead=8, cacheWrite=2,
                             reasoning=3, totalTokens=999)),
            event(stop='toolUse', usage=dict(input=4, cacheWrite=1, totalTokens=0)),
            event(stop='length', usage=dict(output=6, reasoning=6)),
            event(),
        ]
        self.assertEqual(summarize(records),
                         dict(calls=4, input=14, output=11, cacheRead=8,
                              cacheWrite=3, totalTokens=36))

    def test_fixture_cli_ignores_blank_lines(self):
        result = subprocess.run([sys.executable, str(ROOT / 'usage_summary.py'),
                                 str(ROOT / 'session.jsonl')],
                                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout),
                         dict(calls=2, input=150, output=35, cacheRead=50,
                              cacheWrite=10, totalTokens=245))
        self.assertEqual(len(result.stdout.splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
