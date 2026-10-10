import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from usage_summary import summarize


def event(kind='message_end', role='assistant', stop='stop', usage=None):
    return dict(type=kind, message=dict(role=role, stopReason=stop, usage=usage or {}))


class UsageTests(unittest.TestCase):
    def test_only_completed_assistant_messages_count(self):
        usage = dict(input=10, output=5, cacheRead=8, cacheWrite=2,
                     reasoning=3, totalTokens=999)
        records = [event(kind=kind, usage=usage)
                   for kind in ('message_start', 'message_update', 'message_end')]
        records += [event(role='toolResult', usage=usage),
                    event(role='user', usage=usage),
                    event(stop='error', usage=usage),
                    event(stop='aborted', usage=usage),
                    event(stop=None, usage=usage),
                    {'type': 'message_end'}]
        self.assertEqual(summarize(records), dict(
            calls=1, input=10, output=5, cacheRead=8, cacheWrite=2, totalTokens=25))

    def test_all_completed_stop_reasons_and_missing_usage(self):
        records = [event(stop='stop', usage={'input': 4}),
                   event(stop='toolUse', usage={'output': 6, 'reasoning': 2}),
                   event(stop='length'),
                   {'type': 'message_end', 'message': {'role': 'assistant', 'stopReason': 'stop'}}]
        self.assertEqual(summarize(records), dict(
            calls=4, input=4, output=6, cacheRead=0, cacheWrite=0, totalTokens=10))

    def test_cli_ignores_blank_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text('\n' + json.dumps(event(usage={'cacheWrite': 7})) + '\n  \n')
            output = subprocess.check_output([sys.executable, str(Path(__file__).with_name('usage_summary.py')),
                                              str(path)], text=True)
        self.assertEqual(json.loads(output), dict(
            calls=1, input=0, output=0, cacheRead=0, cacheWrite=7, totalTokens=7))


if __name__ == '__main__':
    unittest.main()
