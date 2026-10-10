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
        ignored = [event(kind=kind, usage=dict(input=100))
                   for kind in ('message_start', 'message_update', 'message_delta')]
        ignored += [event(role='toolResult', usage=dict(input=100)),
                    event(role='user', usage=dict(input=100))]
        ignored += [event(stop=stop, usage=dict(input=100))
                    for stop in (None, 'error', 'aborted')]
        completed = [event(stop=stop, usage=dict(input=1))
                     for stop in ('stop', 'toolUse', 'length')]
        self.assertEqual(summarize(ignored + completed), dict(
            calls=3, input=3, output=0, cacheRead=0, cacheWrite=0, totalTokens=3))

    def test_missing_usage_and_fields_count_as_zero(self):
        no_usage = dict(type='message_end', message=dict(role='assistant', stopReason='stop'))
        self.assertEqual(summarize([no_usage, event(usage=dict(cacheWrite=4))]), dict(
            calls=2, input=0, output=0, cacheRead=0, cacheWrite=4, totalTokens=4))

    def test_total_is_computed_without_reasoning_or_supplied_total(self):
        self.assertEqual(summarize([event(usage=dict(input=10, output=5, cacheRead=8,
                                                    cacheWrite=2, reasoning=3, totalTokens=999))]),
                         dict(calls=1, input=10, output=5, cacheRead=8, cacheWrite=2,
                              totalTokens=25))

    def test_cli_fixture_including_blank_lines(self):
        directory = Path(__file__).resolve().parent
        result = subprocess.run([sys.executable, str(directory / 'usage_summary.py'),
                                 str(directory / 'session.jsonl')],
                                check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout), dict(
            calls=2, input=150, output=35, cacheRead=50, cacheWrite=10, totalTokens=245))
        self.assertEqual(result.stderr, '')


if __name__ == '__main__':
    unittest.main()
