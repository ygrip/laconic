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
        ignored = [event(kind=kind, usage={'input': 100}) for kind in
                   ('message_start', 'message_update', 'tool_result')]
        ignored += [event(role='toolResult', usage={'input': 100}),
                    event(role='user', usage={'input': 100})]
        ignored += [event(stop=stop, usage={'input': 100}) for stop in
                    ('error', 'aborted', None)]
        ignored += [{'type': 'message_end'}, {'type': 'message_end', 'message': {'role': 'assistant'}}]
        completed = [event(stop=stop, usage={'input': 1}) for stop in
                     ('stop', 'toolUse', 'length')]
        self.assertEqual(summarize(ignored + completed),
                         dict(calls=3, input=3, output=0, cacheRead=0,
                              cacheWrite=0, totalTokens=3))

    def test_missing_usage_and_partial_usage(self):
        no_usage = {'type': 'message_end', 'message': {'role': 'assistant', 'stopReason': 'stop'}}
        result = summarize([no_usage, event(usage={'cacheRead': 4, 'cacheWrite': 2})])
        self.assertEqual(result, dict(calls=2, input=0, output=0,
                                      cacheRead=4, cacheWrite=2, totalTokens=6))

    def test_supplied_total_and_reasoning_are_ignored(self):
        result = summarize([event(usage=dict(input=10, output=5, cacheRead=8,
                                             cacheWrite=2, reasoning=3, totalTokens=999)),
                            event(usage=dict(output=7, totalTokens=999))])
        self.assertEqual(result, dict(calls=2, input=10, output=12,
                                      cacheRead=8, cacheWrite=2, totalTokens=32))

    def test_cli_ignores_blank_lines_and_prints_one_json_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.jsonl'
            path.write_text('\n  \n' + json.dumps(event(usage={'input': 2})) + '\n\n')
            process = subprocess.run([sys.executable, str(Path(__file__).with_name('usage_summary.py')),
                                      str(path)], capture_output=True, text=True, check=True)
        self.assertEqual(len(process.stdout.splitlines()), 1)
        self.assertEqual(json.loads(process.stdout),
                         dict(calls=1, input=2, output=0, cacheRead=0,
                              cacheWrite=0, totalTokens=2))


if __name__ == '__main__':
    unittest.main()
