"""Synthetic CLI inputs verify privacy and configuration without external calls."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import agent
import demo
import draft_plan
import server
from goalguard.models import ModelUnavailable


CONFIG = {'GEMINI_API_KEY': 'synthetic-test-key', 'GEMINI_MODEL_A': 'fixture-a', 'GEMINI_MODEL_B': 'fixture-b'}
ROOT = Path(__file__).resolve().parents[1]


class AgentCLITests(unittest.TestCase):
    def invoke(self, *args):
        output = io.StringIO()
        with patch('sys.argv', ['agent.py', *args]), patch.object(agent, 'model_config', return_value=CONFIG), redirect_stdout(output):
            agent.main()
        return json.loads(output.getvalue())

    def test_help_for_all_entry_points_has_no_model_or_payment_calls(self):
        for module in (agent, demo, draft_plan, server):
            with self.subTest(module=module.__name__), patch('sys.argv', [module.__name__, '--help']), redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    module.main()
                self.assertEqual(error.exception.code, 0)

    def test_check_config_reports_presence_without_secret_values(self):
        result = self.invoke('--check-config')
        self.assertTrue(result['api_key_present'])
        self.assertEqual(result['live_call'], 'not_run')
        self.assertNotIn(CONFIG['GEMINI_API_KEY'], json.dumps(result))

    def test_list_models_keeps_generation_and_gateway_unverified(self):
        provider = Mock()
        provider.list_models.return_value = {'models': ['fixture-a'], 'list_complete': True}
        with patch.object(agent, 'Gemini', return_value=provider):
            result = self.invoke('--list-models')
        self.assertEqual(result['generation'], 'not_run')
        self.assertEqual(result['gateway'], 'not_contacted')
        self.assertFalse(result['configured_models_listed']['fixture-b'])
        with patch.object(agent, 'Gemini', side_effect=ModelUnavailable('model_timeout')):
            with self.assertRaises(SystemExit) as error:
                self.invoke('--list-models')
            self.assertEqual(error.exception.code, 1)

    def test_real_caller_factory_receives_only_the_selected_agent_token(self):
        caller = agent.make_caller(ROOT, CONFIG, 'agent-b', 'b' * 40, 8765)
        self.assertEqual(caller.runner.principal.identity, 'agent-b')
        self.assertEqual(caller.provider.model, 'fixture-b')
        self.assertEqual(caller.runner.tool_calls, 0)
        self.assertNotIn('approve', {t['name'] for t in caller.tools})

    def test_private_records_are_exclusive_restricted_and_outside_public_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with self.assertRaises(ValueError):
                agent.private_record(root / 'public.json', {'fixture': True}, root)
            record = root / '.local' / 'fixture.json'
            agent.private_record(record, {'fixture': True}, root)
            self.assertEqual(stat.S_IMODE(record.stat().st_mode), 0o600)
            with self.assertRaises(FileExistsError):
                agent.private_record(record, {'fixture': False}, root)
            self.assertTrue(json.loads(record.read_text())['fixture'])

    def test_persistent_request_saves_only_fixture_report_and_keeps_existing_record(self):
        report = {'outcome': 'reserved_for_owner', 'stop_reason': 'run_complete', 'last_proposal': None,
                  'model_message': 'Owner review required', 'model_calls': 1, 'tool_calls': 1}
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            (state / 'tokens.json').write_text(json.dumps({'owner': 'o' * 40, 'agent-a': 'a' * 40, 'agent-b': 'b' * 40}))
            record = state / 'record.json'
            caller = Mock()
            caller.run.return_value = dict(report)
            with patch.object(agent, 'make_caller', return_value=caller) as factory:
                result = self.invoke('--request', 'Find a microphone.', '--state-dir', str(state), '--record', str(record))
            self.assertEqual(result['outcome'], 'reserved_for_owner')
            self.assertEqual(stat.S_IMODE(record.stat().st_mode), 0o600)
            self.assertEqual(factory.call_args.args[3], 'a' * 40)
            self.assertNotIn('o' * 40, repr(factory.call_args))
            self.assertEqual(set(caller.run.call_args.kwargs), {'progress'})
            with patch.object(agent, 'make_caller', return_value=caller), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    self.invoke('--request', 'Find a microphone.', '--state-dir', str(state), '--record', str(record))
            self.assertEqual(error.exception.code, 2)

    def test_missing_tokens_invalid_tokens_and_missing_request_fail_safely(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stderr(io.StringIO()):
            state = Path(directory)
            for tokens in (None, {}, {'owner': 'same' * 10, 'agent-a': 'same' * 10, 'agent-b': 'same' * 10}):
                if tokens is not None:
                    (state / 'tokens.json').write_text(json.dumps(tokens))
                with self.assertRaises(SystemExit) as error:
                    self.invoke('--request', 'Find a microphone.', '--state-dir', str(state))
                self.assertEqual(error.exception.code, 2)
            with self.assertRaises(SystemExit):
                self.invoke('--only-agent', 'agent-b')
            with self.assertRaises(SystemExit):
                self.invoke()

    def test_demo_dispatch_and_provenance_errors_do_not_make_network_calls(self):
        with patch.object(agent, 'run_demo') as mocked, patch('sys.argv', ['agent.py', '--demo', '--only-agent', 'agent-b']), patch.object(agent, 'model_config', return_value=CONFIG):
            agent.main()
            self.assertEqual(mocked.call_args.kwargs['only_agent'], 'agent-b')
        with patch.object(agent.subprocess, 'check_output', side_effect=OSError()):
            self.assertIsNone(agent.provenance(ROOT)['source_revision'])
        with patch.object(agent.subprocess, 'check_output', side_effect=subprocess.CalledProcessError(1, 'git')):
            self.assertIsNone(agent.provenance(ROOT)['source_tree_dirty'])

    def test_progress_errors_cannot_alter_state(self):
        with redirect_stderr(io.StringIO()):
            for event in ({'phase': 'request', 'call': 1}, {'phase': 'response', 'call': 1, 'tools': 1},
                          {'phase': 'error', 'call': 1, 'code': 'model_timeout'}):
                agent.show_progress('agent-a', event)
        with patch('builtins.print', side_effect=OSError()):
            agent.show_progress('agent-a', {'phase': 'request', 'call': 1})

    def test_deterministic_demo_and_synthetic_draft_request(self):
        with patch('sys.argv', ['demo.py']), redirect_stdout(io.StringIO()) as output:
            demo.main()
        self.assertIn('accepted_counteroffer', output.getvalue())
        self.assertNotIn('permit', output.getvalue())
        text = draft_plan.synthetic_request()
        self.assertIn('excluding separately held savings', text)
        self.assertIn('suggest the monthly contribution', text)
