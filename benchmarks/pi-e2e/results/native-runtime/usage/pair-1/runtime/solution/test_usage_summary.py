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
        result = summarize([event(usage=dict(output=5, reasoning=3, totalTokens=999))])
        self.assertEqual(result['output'], 5)
        self.assertEqual(result['totalTokens'], 5)

    def test_only_completed_assistant_messages_count(self):
        excluded = [
            event(kind='message_start', usage=dict(input=100)),
            event(kind='message_update', usage=dict(input=100)),
            event(kind='tool_result', usage=dict(input=100)),
            event(role='toolResult', usage=dict(input=100)),
            event(role='user', usage=dict(input=100)),
            event(stop='error', usage=dict(input=100)),
            event(stop='aborted', usage=dict(input=100)),
            event(stop=None, usage=dict(input=100)),
            {'type': 'message_end'},
        ]
        completed = [event(stop=stop, usage=dict(input=1, output=2, cacheRead=3, cacheWrite=4))
                     for stop in ('stop', 'toolUse', 'length')]
        self.assertEqual(summarize(excluded + completed), dict(
            calls=3, input=3, output=6, cacheRead=9, cacheWrite=12, totalTokens=30))

    def test_missing_usage_and_fields(self):
        no_usage = dict(type='message_end', message=dict(role='assistant', stopReason='stop'))
        self.assertEqual(summarize([no_usage, event(stop='length', usage=dict(cacheWrite=7))]),
                         dict(calls=2, input=0, output=0, cacheRead=0, cacheWrite=7, totalTokens=7))

    def test_cli_ignores_blank_lines_and_prints_one_json_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text('\n  \n' + json.dumps(event(usage=dict(input=2, output=3))) + '\n\n')
            output = subprocess.check_output([sys.executable, str(Path(__file__).with_name('usage_summary.py')),
                                              str(path)], text=True)
        self.assertEqual(len(output.splitlines()), 1)
        self.assertEqual(json.loads(output), dict(
            calls=1, input=2, output=3, cacheRead=0, cacheWrite=0, totalTokens=5))


if __name__ == '__main__':
    unittest.main()
