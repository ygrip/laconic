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
        records = [event(stop=stop) for stop in ('stop', 'toolUse', 'length')]
        records += [event(kind=kind, usage=dict(input=100))
                    for kind in ('message_start', 'message_update', 'tool_result')]
        records += [event(role='toolResult', usage=dict(input=100)),
                    event(role='user', usage=dict(input=100))]
        records += [event(stop=stop, usage=dict(input=100))
                    for stop in (None, 'error', 'aborted')]
        self.assertEqual(summarize(records), dict(calls=3, input=0, output=0,
                                                   cacheRead=0, cacheWrite=0, totalTokens=0))

    def test_missing_usage_and_fields_count_as_zero(self):
        records = [dict(type='message_end', message=dict(role='assistant', stopReason='stop')),
                   event(usage=dict(input=4)), event(usage=dict(cacheWrite=2))]
        self.assertEqual(summarize(records), dict(calls=3, input=4, output=0,
                                                   cacheRead=0, cacheWrite=2, totalTokens=6))

    def test_supplied_total_and_reasoning_are_ignored(self):
        usage = dict(input=10, output=5, cacheRead=8, cacheWrite=2,
                     reasoning=3, totalTokens=999)
        self.assertEqual(summarize([event(usage=usage)]),
                         dict(calls=1, input=10, output=5, cacheRead=8,
                              cacheWrite=2, totalTokens=25))

    def test_cli_ignores_blank_lines_and_prints_one_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text('\n' + json.dumps(event(usage=dict(input=4))) + '\n  \n')
            completed = subprocess.run([sys.executable, str(Path(__file__).with_name('usage_summary.py')),
                                        str(path)], capture_output=True, text=True, check=True)
        self.assertEqual(completed.stderr, '')
        self.assertEqual(completed.stdout.count('\n'), 1)
        self.assertEqual(json.loads(completed.stdout),
                         dict(calls=1, input=4, output=0, cacheRead=0,
                              cacheWrite=0, totalTokens=4))


if __name__ == '__main__':
    unittest.main()
