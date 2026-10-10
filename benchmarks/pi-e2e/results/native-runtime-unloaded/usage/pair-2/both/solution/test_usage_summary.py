import json
import subprocess
import sys
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
        usage = dict(input=10, output=5, cacheRead=8, cacheWrite=2,
                     reasoning=3, totalTokens=999)
        records = [event(stop=stop, usage=usage) for stop in ('stop', 'toolUse', 'length')]
        records += [event(kind=kind, usage=usage) for kind in
                    ('message_start', 'message_update', 'tool_result')]
        records += [event(role='toolResult', usage=usage)]
        records += [event(stop=stop, usage=usage) for stop in
                    ('error', 'aborted', None)]
        self.assertEqual(summarize(records), dict(calls=3, input=30, output=15,
                                                  cacheRead=24, cacheWrite=6, totalTokens=75))

    def test_missing_usage_and_fields(self):
        records = [dict(type='message_end', message=dict(role='assistant', stopReason='stop')),
                   event(stop='length', usage=dict(cacheWrite=4))]
        self.assertEqual(summarize(records), dict(calls=2, input=0, output=0,
                                                  cacheRead=0, cacheWrite=4, totalTokens=4))

    def test_cli_fixture(self):
        path = Path(__file__).with_name('session.jsonl')
        output = subprocess.check_output([sys.executable, str(path.with_name('usage_summary.py')),
                                          str(path)], text=True)
        self.assertEqual(json.loads(output), dict(calls=2, input=150, output=35,
                                                  cacheRead=50, cacheWrite=10, totalTokens=245))
        self.assertEqual(len(output.splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
