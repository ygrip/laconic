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
    def test_only_completed_assistant_messages_count(self):
        records = [event(stop=stop) for stop in ('stop', 'toolUse', 'length')]
        records += [event(kind=kind, usage={'input': 100})
                    for kind in ('message_start', 'message_update', 'tool_result')]
        records += [event(role='toolResult', usage={'input': 100}),
                    event(role='user', usage={'input': 100}),
                    event(stop='error', usage={'input': 100}),
                    event(stop='aborted', usage={'input': 100}),
                    event(stop=None, usage={'input': 100})]
        self.assertEqual(summarize(records), dict(
            calls=3, input=0, output=0, cacheRead=0, cacheWrite=0, totalTokens=0))

    def test_usage_fields_and_total_are_derived_without_double_counting(self):
        records = [event(usage=dict(input=10, output=5, cacheRead=8, cacheWrite=2,
                                    reasoning=3, totalTokens=999)),
                   event(stop='toolUse', usage=dict(input=4, output=7, totalTokens=1)),
                   event(stop='length', usage=dict(cacheWrite=6))]
        self.assertEqual(summarize(records), dict(
            calls=3, input=14, output=12, cacheRead=8, cacheWrite=8, totalTokens=42))

    def test_missing_usage_still_counts(self):
        self.assertEqual(summarize([{'type': 'message_end', 'message':
                                     {'role': 'assistant', 'stopReason': 'stop'}}]),
                         dict(calls=1, input=0, output=0, cacheRead=0,
                              cacheWrite=0, totalTokens=0))

    def test_cli_ignores_blank_lines_and_prints_one_json_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text('\n  \n' + json.dumps(event(usage={'input': 2, 'output': 3})) + '\n\n')
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).with_name('usage_summary.py')), str(path)],
                capture_output=True, text=True, check=True)
        self.assertEqual(len(completed.stdout.splitlines()), 1)
        self.assertEqual(json.loads(completed.stdout), dict(
            calls=1, input=2, output=3, cacheRead=0, cacheWrite=0, totalTokens=5))


if __name__ == '__main__':
    unittest.main()
