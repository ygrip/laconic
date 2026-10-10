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
        records = [event(stop=stop, usage={'input': 10}) for stop in ('stop', 'toolUse', 'length')]
        records += [event(kind=kind, usage={'input': 100}) for kind in ('message_start', 'message_update')]
        records += [event(role='toolResult', usage={'input': 100}),
                    event(role='user', usage={'input': 100})]
        records += [event(stop=stop, usage={'input': 100}) for stop in ('error', 'aborted', None)]
        self.assertEqual(summarize(records), dict(calls=3, input=30, output=0,
                                                  cacheRead=0, cacheWrite=0, totalTokens=30))

    def test_missing_usage_and_fields_count_as_zero(self):
        records = [{'type': 'message_end', 'message': {'role': 'assistant', 'stopReason': 'stop'}},
                   event(stop='length', usage={'cacheWrite': 7})]
        self.assertEqual(summarize(records), dict(calls=2, input=0, output=0,
                                                  cacheRead=0, cacheWrite=7, totalTokens=7))

    def test_total_is_computed_not_supplied_or_double_counted(self):
        records = [event(usage=dict(input=10, output=5, cacheRead=8, cacheWrite=2,
                                    reasoning=3, totalTokens=999)),
                   event(stop='toolUse', usage=dict(input=1, output=4, totalTokens=0))]
        self.assertEqual(summarize(records), dict(calls=2, input=11, output=9,
                                                  cacheRead=8, cacheWrite=2, totalTokens=30))

    def test_cli_ignores_blank_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'events.jsonl'
            path.write_text('\n' + json.dumps(event(usage={'output': 4})) + '\n  \n')
            completed = subprocess.run([sys.executable, str(Path(__file__).with_name('usage_summary.py')),
                                        str(path)], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(completed.stdout), dict(calls=1, input=0, output=4,
                                                             cacheRead=0, cacheWrite=0, totalTokens=4))


if __name__ == '__main__':
    unittest.main()
