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
        records += [event(kind=kind, usage={'input': 100}) for kind in
                    ('message_start', 'message_update', 'tool_result', 'error')]
        records += [event(role=role, usage={'input': 100}) for role in ('user', 'toolResult')]
        records += [event(stop=stop, usage={'input': 100}) for stop in
                    ('error', 'aborted', None)]
        records += [{'type': 'message_end', 'message': {'role': 'assistant'}}]
        self.assertEqual(summarize(records), dict(calls=3, input=0, output=0,
                                                   cacheRead=0, cacheWrite=0, totalTokens=0))

    def test_usage_fields_sum_without_reasoning_or_supplied_total(self):
        records = [event(usage=dict(input=10, output=5, cacheRead=8, cacheWrite=2,
                                    reasoning=3, totalTokens=999)),
                   event(stop='length', usage=dict(input=1, output=4, cacheRead=6,
                                                   totalTokens=999))]
        self.assertEqual(summarize(records), dict(calls=2, input=11, output=9,
                                                   cacheRead=14, cacheWrite=2, totalTokens=36))

    def test_missing_usage_and_missing_fields(self):
        records = [{'type': 'message_end', 'message': {'role': 'assistant', 'stopReason': 'stop'}},
                   event(stop='toolUse', usage={'cacheWrite': 7})]
        self.assertEqual(summarize(records), dict(calls=2, input=0, output=0,
                                                   cacheRead=0, cacheWrite=7, totalTokens=7))

    def test_cli_ignores_blank_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'events.jsonl'
            path.write_text('\n  \n' + json.dumps(event(usage={'output': 4})) + '\n\n')
            output = subprocess.check_output([sys.executable, 'usage_summary.py', str(path)], text=True)
        self.assertEqual(json.loads(output), dict(calls=1, input=0, output=4,
                                                  cacheRead=0, cacheWrite=0, totalTokens=4))
        self.assertEqual(len(output.splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
