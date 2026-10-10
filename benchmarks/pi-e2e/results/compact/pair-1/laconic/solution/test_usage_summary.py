import json
import subprocess
import sys
import unittest
from pathlib import Path
from usage_summary import summarize


def event(kind='message_end', role='assistant', stop='stop', usage=None):
    return dict(type=kind, message=dict(role=role, stopReason=stop, usage=usage or {}))


class UsageTests(unittest.TestCase):
    def test_completed_reasons_and_token_math(self):
        records = [
            event(stop='stop', usage=dict(input=10, output=5, cacheRead=8, cacheWrite=2,
                                          reasoning=3, totalTokens=999)),
            event(stop='toolUse', usage=dict(input=4, output=6, cacheRead=1)),
            event(stop='length', usage=dict(output=7, cacheWrite=3)),
            dict(type='message_end', message=dict(role='assistant', stopReason='stop')),
        ]
        self.assertEqual(summarize(records), dict(calls=4, input=14, output=18,
                                                   cacheRead=9, cacheWrite=5, totalTokens=46))

    def test_ignores_noncompleted_assistant_and_other_roles(self):
        records = [event(kind=kind, usage=dict(input=100))
                   for kind in ('message_start', 'message_update', 'tool_result')]
        records += [event(role='toolResult', usage=dict(input=100)),
                    event(role='user', usage=dict(input=100)),
                    event(stop='error', usage=dict(input=100)),
                    event(stop='aborted', usage=dict(input=100)),
                    event(stop=None, usage=dict(input=100)),
                    dict(type='message_end'),
                    dict(type='message_end', message=dict(role='assistant'))]
        self.assertEqual(summarize(records), dict(calls=0, input=0, output=0,
                                                   cacheRead=0, cacheWrite=0, totalTokens=0))

    def test_cli_fixture_ignores_blank_lines(self):
        script = Path(__file__).with_name('usage_summary.py')
        fixture = Path(__file__).with_name('session.jsonl')
        output = subprocess.check_output([sys.executable, str(script), str(fixture)], text=True)
        self.assertEqual(json.loads(output), dict(calls=2, input=150, output=35,
                                                  cacheRead=50, cacheWrite=10, totalTokens=245))


if __name__ == '__main__':
    unittest.main()
