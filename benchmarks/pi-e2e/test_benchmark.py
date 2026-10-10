"""Tests for the measurement harness, not the intentionally broken dogfood fixture."""
import json
import argparse
import contextlib
import io
from unittest.mock import patch
from pathlib import Path
import tempfile
import shutil
import unittest
from analyze import analyze
from run import completed_messages, run_one, verify, ROOT
from validate_results import validate
import hashlib


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
            for arm, multiplier in [('baseline', 2), ('laconic', 1), ('runtime',1), ('both',1)]:
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
            self.assertEqual(summary['comparisons_to_baseline']['runtime']['total_tokens'],50)
            self.assertEqual(summary['comparisons_to_baseline']['both']['total_tokens'],50)
            self.assertEqual(len(summary['paired']),3)
            self.assertEqual(summary['arms']['runtime']['recovery_calls']['sum'],0)

    def test_combined_analysis_keeps_same_pair_numbers_separate_by_workflow(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'manifest.json').write_text(json.dumps(dict(tasks=['usage','log-triage'])))
            for task in ['usage','log-triage']:
                for arm,multiplier in [('baseline',2),('runtime',1)]:
                    dest=root/task/'pair-1'/arm
                    dest.mkdir(parents=True)
                    metric=dict(pair=1,task=task,arm=arm,acceptance_passed=9,acceptance_total=9,suite_exit_code=0)
                    for key in ('final_words','prose_words','output','input','cacheRead','cacheWrite','total_tokens',
                                'tool_calls','tool_result_text_bytes','model_calls','elapsed_seconds'):
                        metric[key]=100*multiplier
                    (dest/'metrics.json').write_text(json.dumps(metric))
                    (dest/'events.jsonl').write_text('')
            summary=analyze(root)
            self.assertEqual(len(summary['runs']),4)
            self.assertEqual(len(summary['paired']),2)
            self.assertEqual({p['task'] for p in summary['paired']},{'usage','log-triage'})
            self.assertEqual(summary['comparisons_to_baseline']['runtime']['total_tokens'],50)

    def test_runtime_recovery_tool_is_explicitly_active_in_restricted_tool_list(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            auth=root/'agent'
            auth.mkdir()
            (auth/'auth.json').write_text('{}')
            args=argparse.Namespace(agent_dir=str(auth),task='usage',provider='test',model='test',thinking='medium',timeout=5)
            event=dict(type='message_end',message=dict(role='assistant',stopReason='stop',content=[dict(type='text',text='done')],usage={}))
            response=argparse.Namespace(returncode=0,stdout=json.dumps(event)+'\n',stderr='')
            def fake_run(command, **kwargs):
                if command[0] == 'pi':
                    Path(kwargs['env']['LACONIC_BENCHMARK_AUDIT']).write_text(json.dumps(dict(correct_active_tools=True)))
                return response
            for arm in ('baseline','laconic','runtime','both'):
                with patch('run.subprocess.run',side_effect=fake_run) as execute, patch('run.verify',return_value=dict(acceptance=[],suite_exit_code=0)), contextlib.redirect_stdout(io.StringIO()):
                    run_one(1,arm,args,root/'results')
                command=execute.call_args_list[1].args[0]
                tools=command[command.index('--tools')+1].split(',')
                self.assertEqual('laconic_read_result' in tools,arm in ('runtime','both'))
                self.assertIn('--extension',command)  # Identical silent observer in every arm.
                self.assertTrue(command[command.index('--extension')+1].endswith('.ts'))
                self.assertEqual(execute.call_args_list[1].kwargs['env']['LACONIC_BENCHMARK_PREFLIGHT'],'1')
                self.assertNotIn('LACONIC_BENCHMARK_PREFLIGHT',execute.call_args_list[2].kwargs['env'])
                self.assertEqual('--skill' in command,arm in ('laconic','both'))

    def test_result_audit_rejects_incorrect_activation_and_usage(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            manifest=dict(tasks=['usage'],pairs=1,arms=['baseline','runtime'],runtime_sha256={},
                          observer_sha256=hashlib.sha256((ROOT/'audit-extension.ts').read_bytes()).hexdigest())
            (root/'manifest.json').write_text(json.dumps(manifest))
            for arm in manifest['arms']:
                dest=root/'pair-1'/arm
                dest.mkdir(parents=True)
                tools=sorted(['read','bash','edit','write']+(['laconic_read_result'] if arm=='runtime' else []))
                audit=dict(correct_active_tools=True,active_tools=tools)
                (dest/'startup-audit.json').write_text(json.dumps(dict(preflight=audit,session=audit)))
                checks=dict(suite_exit_code=0,acceptance_exit_code=0,acceptance=[dict(passed=True)]*9)
                (dest/'verification.json').write_text(json.dumps(checks))
                metric=dict(acceptance_passed=9,acceptance_total=9,total_tokens=6,reported_total_tokens=6,model_calls=1)
                (dest/'metrics.json').write_text(json.dumps(metric))
                event=dict(message=dict(role='assistant',content=[],usage=dict(input=5,output=1)))
                (dest/'events.jsonl').write_text(json.dumps(event)+'\n')
            self.assertEqual(validate(root)['runs'],2)
            dest=root/'pair-1'/'runtime'
            bad=dict(metric,total_tokens=7)
            (dest/'metrics.json').write_text(json.dumps(bad))
            with self.assertRaises(AssertionError): validate(root)
            (dest/'metrics.json').write_text(json.dumps(metric))
            audit['active_tools']=['bash','read','edit','write']
            (dest/'startup-audit.json').write_text(json.dumps(dict(preflight=audit,session=audit)))
            with self.assertRaises(AssertionError): validate(root)

    def test_activation_preflight_failure_stops_before_inference(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            auth=root/'agent'
            auth.mkdir()
            (auth/'auth.json').write_text('{}')
            args=argparse.Namespace(agent_dir=str(auth),task='usage',provider='test',model='test',thinking='medium',timeout=5)
            response=argparse.Namespace(returncode=0,stdout='',stderr='')
            with patch('run.subprocess.run',return_value=response) as execute:
                with self.assertRaisesRegex(RuntimeError,'activation preflight failed'):
                    run_one(1,'runtime',args,root/'results')
            self.assertEqual(execute.call_count,2)  # git init and preflight; no provider session.

    def test_log_triage_checks_incident_and_unchanged_generator(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)/'work'
            shutil.copytree(ROOT/'fixture',work)
            shutil.copy2(ROOT/'log-triage.py',work/'diagnose.py')
            (work/'incident.json').write_text(json.dumps(dict(customer='cedar',batch=463,reason='stale-cache',lost_calls=17)))
            result=verify(work,'log-triage')
            self.assertEqual(len(result['acceptance']),11)
            self.assertTrue(all(c['passed'] for c in result['acceptance'][-2:]))
            (work/'diagnose.py').write_text('modified')
            result=verify(work,'log-triage')
            self.assertFalse(result['acceptance'][-1]['passed'])


if __name__ == '__main__':
    unittest.main()
