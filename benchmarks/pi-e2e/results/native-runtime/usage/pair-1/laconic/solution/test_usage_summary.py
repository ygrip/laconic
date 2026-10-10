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
        for stop in ('stop', 'toolUse', 'length'):
            with self.subTest(stop=stop):
                self.assertEqual(summarize([event(stop=stop)])['calls'], 1)
        for kind, role, stop in (
            ('message_start', 'assistant', 'stop'),
            ('message_update', 'assistant', 'stop'),
            ('message_end', 'toolResult', 'stop'),
            ('message_end', 'user', 'stop'),
            ('message_end', 'assistant', None),
            ('message_end', 'assistant', 'error'),
            ('message_end', 'assistant', 'aborted'),
        ):
            with self.subTest(kind=kind, role=role, stop=stop):
                self.assertEqual(summarize([event(kind=kind, role=role, stop=stop,
                                                  usage=dict(input=99))])['calls'], 0)

    def test_missing_usage_and_fields_count_as_zero(self):
        no_usage = event()
        del no_usage['message']['usage']
        self.assertEqual(summarize([no_usage, event(usage=dict(cacheWrite=4))]),
                         dict(calls=2, input=0, output=0, cacheRead=0,
                              cacheWrite=4, totalTokens=4))

    def test_aggregates_only_usage_fields_without_trusting_total_or_reasoning(self):
        records = [
            event(usage=dict(input=10, output=5, cacheRead=8, cacheWrite=2,
                             reasoning=3, totalTokens=999)),
            event(stop='length', usage=dict(input=4, output=6, totalTokens=1)),
            event(kind='message_update', usage=dict(input=1000)),
            event(stop='error', usage=dict(output=1000)),
        ]
        self.assertEqual(summarize(records), dict(calls=2, input=14, output=11,
                                                  cacheRead=8, cacheWrite=2,
                                                  totalTokens=35))

    def test_cli_ignores_blank_lines_and_prints_one_json_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text('\n' + json.dumps(event(usage=dict(input=2, output=3))) + '\n  \n')
            output = subprocess.check_output([sys.executable, str(Path(__file__).with_name('usage_summary.py')),
                                              str(path)], text=True)
        self.assertEqual(output.count('\n'), 1)
        self.assertEqual(json.loads(output), dict(calls=1, input=2, output=3,
                                                  cacheRead=0, cacheWrite=0,
                                                  totalTokens=5))


if __name__ == '__main__':
    unittest.main()
