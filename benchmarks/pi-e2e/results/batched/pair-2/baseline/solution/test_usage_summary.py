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
    def test_completed_stop_reasons_and_missing_usage(self):
        records = [event(stop='stop', usage={'input': 10, 'output': 5}),
                   event(stop='toolUse', usage={'cacheRead': 8}),
                   event(stop='length', usage={'cacheWrite': 2}),
                   {'type': 'message_end', 'message': {'role': 'assistant', 'stopReason': 'stop'}}]
        self.assertEqual(summarize(records), dict(calls=4, input=10, output=5,
                                                  cacheRead=8, cacheWrite=2, totalTokens=25))

    def test_only_completed_assistant_messages_count(self):
        records = [event(kind=kind, usage={'input': 100})
                   for kind in ('message_start', 'message_update', 'tool_result')]
        records += [event(role='toolResult', usage={'input': 100}),
                    event(role='user', usage={'input': 100})]
        records += [event(stop=stop, usage={'input': 100})
                    for stop in ('error', 'aborted', None)]
        records.append(event(usage={'input': 3}))
        self.assertEqual(summarize(records), dict(calls=1, input=3, output=0,
                                                  cacheRead=0, cacheWrite=0, totalTokens=3))

    def test_ignores_reasoning_and_supplied_total(self):
        records = [event(usage=dict(input=10, output=5, cacheRead=8, cacheWrite=2,
                                    reasoning=3, totalTokens=999))]
        self.assertEqual(summarize(records), dict(calls=1, input=10, output=5,
                                                  cacheRead=8, cacheWrite=2, totalTokens=25))

    def test_cli_skips_blank_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text('\n' + json.dumps(event(usage={'output': 7})) + '\n  \n')
            output = subprocess.check_output([sys.executable, str(Path(__file__).with_name('usage_summary.py')),
                                              str(path)], text=True)
        self.assertEqual(json.loads(output), dict(calls=1, input=0, output=7,
                                                  cacheRead=0, cacheWrite=0, totalTokens=7))


if __name__ == '__main__':
    unittest.main()
