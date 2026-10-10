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
        ignored = [
            event(kind='message_start', usage=dict(input=100)),
            event(kind='message_update', usage=dict(input=100)),
            event(kind='tool_result', usage=dict(input=100)),
            event(role='toolResult', usage=dict(input=100)),
            event(role='user', usage=dict(input=100)),
            event(stop='error', usage=dict(input=100)),
            event(stop='aborted', usage=dict(input=100)),
            event(stop=None, usage=dict(input=100)),
        ]
        for record in ignored:
            with self.subTest(record=record):
                self.assertEqual(summarize([record]), dict(
                    calls=0, input=0, output=0, cacheRead=0, cacheWrite=0, totalTokens=0))
        result = summarize(ignored + [event(stop='stop'), event(stop='toolUse'), event(stop='length')])
        self.assertEqual(result['calls'], 3)
        self.assertEqual(result['totalTokens'], 0)

    def test_usage_fields_and_total_are_derived(self):
        records = [
            event(usage=dict(input=10, output=5, cacheRead=8, cacheWrite=2,
                             reasoning=3, totalTokens=999)),
            event(stop='toolUse', usage=dict(input=4, cacheWrite=6)),
            event(stop='length', usage=dict(output=7, cacheRead=1)),
            event(),
        ]
        del records[3]['message']['usage']
        # An absent usage object still counts as a completed call.
        self.assertEqual(summarize(records), dict(
            calls=4, input=14, output=12, cacheRead=9, cacheWrite=8, totalTokens=43))

    def test_cli_ignores_blank_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text('\n' + json.dumps(event(usage=dict(input=2, output=3))) + '\n \n')
            output = subprocess.check_output([sys.executable, str(Path(__file__).with_name('usage_summary.py')),
                                              str(path)], text=True)
            self.assertEqual(json.loads(output), dict(
                calls=1, input=2, output=3, cacheRead=0, cacheWrite=0, totalTokens=5))


if __name__ == '__main__':
    unittest.main()
