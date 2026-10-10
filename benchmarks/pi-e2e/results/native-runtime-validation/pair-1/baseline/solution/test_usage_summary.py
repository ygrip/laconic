import json
from pathlib import Path
import subprocess
import sys
import unittest
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
        ignored = [event(kind=kind, usage={'input': 100})
                   for kind in ('message_start', 'message_update', 'tool_result', 'error')]
        ignored += [event(role='user', usage={'input': 100}),
                    event(role='toolResult', usage={'input': 100})]
        ignored += [event(stop=stop, usage={'input': 100})
                    for stop in (None, 'error', 'aborted', 'pending')]
        completed = [event(stop=stop, usage={'input': 1})
                     for stop in ('stop', 'toolUse', 'length')]
        self.assertEqual(summarize(ignored + completed),
                         dict(calls=3, input=3, output=0, cacheRead=0,
                              cacheWrite=0, totalTokens=3))

    def test_missing_usage_and_fields_are_zero(self):
        records = [dict(type='message_end', message=dict(role='assistant', stopReason='stop')),
                   event(stop='length', usage={'cacheWrite': 4})]
        self.assertEqual(summarize(records),
                         dict(calls=2, input=0, output=0, cacheRead=0,
                              cacheWrite=4, totalTokens=4))

    def test_supplied_total_and_reasoning_are_not_added(self):
        result = summarize([event(usage=dict(input=2, output=5, cacheRead=7,
                                             cacheWrite=11, reasoning=3, totalTokens=999))])
        self.assertEqual(result, dict(calls=1, input=2, output=5, cacheRead=7,
                                      cacheWrite=11, totalTokens=25))

    def test_fixture_cli_ignores_blank_lines(self):
        path = Path(__file__).with_name('session.jsonl')
        output = subprocess.check_output([sys.executable,
                                          str(path.with_name('usage_summary.py')),
                                          str(path)], text=True)
        self.assertEqual(json.loads(output),
                         dict(calls=2, input=150, output=35, cacheRead=50,
                              cacheWrite=10, totalTokens=245))
        self.assertEqual(len(output.splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
