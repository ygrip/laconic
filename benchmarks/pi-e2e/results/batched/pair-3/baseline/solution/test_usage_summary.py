import json
from pathlib import Path
import subprocess
import sys
import unittest
from usage_summary import summarize


def event(kind='message_end', role='assistant', stop='stop', usage=None):
    return dict(type=kind, message=dict(role=role, stopReason=stop, usage=usage or {}))


class UsageTests(unittest.TestCase):
    def test_only_completed_assistant_messages_count(self):
        ignored = [
            event(kind='message_start', usage=dict(input=100)),
            event(kind='message_update', usage=dict(input=100)),
            event(kind='tool_result', usage=dict(input=100)),
            event(role='toolResult', usage=dict(input=100)),
            event(role='user', usage=dict(input=100)),
            event(stop='error', usage=dict(input=100)),
            event(stop='aborted', usage=dict(input=100)),
            event(stop=None, usage=dict(input=100)),
            dict(type='message_end'),
        ]
        completed = [event(stop=stop, usage=dict(input=1)) for stop in ('stop', 'toolUse', 'length')]
        self.assertEqual(summarize(ignored + completed), dict(
            calls=3, input=3, output=0, cacheRead=0, cacheWrite=0, totalTokens=3,
        ))

    def test_missing_usage_and_fields_count_as_zero(self):
        without_usage = dict(type='message_end', message=dict(role='assistant', stopReason='stop'))
        self.assertEqual(summarize([without_usage, event(usage=dict(cacheRead=4))]), dict(
            calls=2, input=0, output=0, cacheRead=4, cacheWrite=0, totalTokens=4,
        ))

    def test_total_is_computed_without_double_counting_reasoning(self):
        result = summarize([
            event(usage=dict(input=10, output=5, cacheRead=8, cacheWrite=2,
                             reasoning=3, totalTokens=999)),
            event(stop='toolUse', usage=dict(input=2, output=7, totalTokens=0)),
        ])
        self.assertEqual(result, dict(
            calls=2, input=12, output=12, cacheRead=8, cacheWrite=2, totalTokens=34,
        ))

    def test_cli_fixture(self):
        directory = Path(__file__).resolve().parent
        output = subprocess.check_output(
            [sys.executable, str(directory / 'usage_summary.py'), str(directory / 'session.jsonl')],
            text=True,
        )
        self.assertEqual(json.loads(output), dict(
            calls=2, input=150, output=35, cacheRead=50, cacheWrite=10, totalTokens=245,
        ))


if __name__ == '__main__':
    unittest.main()
