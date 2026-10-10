"""Tests for the measurement harness, not the intentionally broken dogfood fixture."""
import json
from pathlib import Path
import tempfile
import unittest
from analyze import analyze
from run import completed_messages, verify, ROOT


class HarnessTests(unittest.TestCase):
    def test_usage_is_collected_only_at_message_end(self):
        message = dict(role='assistant', content=[], usage=dict(input=10))
        events = [dict(type=t, message=message) for t in ('message_start', 'message_update', 'message_end')]
        events.append(dict(type='message_end', message=dict(role='toolResult')))
        self.assertEqual(completed_messages(events), [message])

    def test_independent_checks_detect_broken_fixture(self):
        result = verify(ROOT/'fixture')
        self.assertNotEqual(result['acceptance_exit_code'], 0)
        self.assertNotEqual(result['suite_exit_code'], 0)
        self.assertEqual(len(result['acceptance']), 9)

    def test_savings_and_per_tool_volume(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for arm, multiplier in [('baseline', 2), ('laconic', 1)]:
                dest = root/'pair-1'/arm
                dest.mkdir(parents=True)
                metric = dict(pair=1, arm=arm, acceptance_passed=9, acceptance_total=9, suite_exit_code=0)
                for key in ('final_words','prose_words','output','input','cacheRead','cacheWrite','total_tokens',
                            'tool_calls','tool_result_text_bytes','model_calls','elapsed_seconds'):
                    metric[key] = 100*multiplier
                (dest/'metrics.json').write_text(json.dumps(metric))
                event = dict(type='message_end', message=dict(role='toolResult',toolName='read',
                             isError=False,content=[dict(type='text',text='é')]))
                assistant = dict(type='message_end', message=dict(role='assistant', content=[],
                                 usage=dict(cost=dict(total=0.01*multiplier))))
                (dest/'events.jsonl').write_text(json.dumps(event)+'\n'+json.dumps(assistant)+'\n')
            summary = analyze(root)
            self.assertEqual(summary['aggregate_savings_percent']['total_tokens'], 50)
            self.assertEqual(summary['runs'][0]['by_tool_sanitized']['read']['text_bytes'], 2)
            self.assertTrue(summary['arms']['laconic']['verified'])
            self.assertEqual(summary['aggregate_savings_percent']['estimated_cost_usd'], 50)
            self.assertEqual(summary['aggregate_savings_percent']['input_context_tokens'], 50)
            self.assertEqual(summary['arms']['laconic']['skill_read_calls']['sum'], 0)


if __name__ == '__main__':
    unittest.main()
