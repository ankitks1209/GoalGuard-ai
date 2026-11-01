"""Synthetic model turns exercise the actual bounded dispatcher and ledger."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from goalguard import Ledger
from goalguard.catalog import Catalog
from goalguard.gateway import Gateway, Principal
from goalguard.models import ModelTurn, ModelUnavailable
from goalguard.runner import ProposalRunner
from goalguard.shopping import ShoppingAgent, valid_arguments


ROOT = Path(__file__).resolve().parents[1]
TOOLS = json.loads((ROOT / 'agent-tools.json').read_text())['tools']


def call(name, **args):
    return {"name": name, "args": args}


def proposal(sku):
    return call("propose_purchase", items=[{"sku": sku, "quantity": 1}])


def turn(*calls, text=""):
    return ModelTurn({"role": "model", "parts": [{"text": "hidden-fixture", "thought": True,
                      "thoughtSignature": "opaque-fixture"}]}, tuple(calls), text, {"totalTokenCount": 2}, "fixture-v1")


class ShoppingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.ledger = Ledger(Path(self.directory.name) / 'ledger.sqlite')
        self.ledger.create_household('fixture-home', 35000, 0)
        self.gateway = Gateway(self.ledger, Catalog())

    def agent(self, identity, *turns):
        provider = Mock(provider='synthetic-fixture', model='fixture', max_output_tokens=2048, timeout_seconds=60)
        provider.generate.side_effect = turns
        runner = ProposalRunner(self.gateway, Principal('fixture-home', identity, 'agent'),
                                skills={'propose-purchase': 'fixture skill'})
        return ShoppingAgent(provider, runner, 'Choose a suitable catalog product.', TOOLS)

    def test_two_scopes_share_capacity_and_recover_once(self):
        first = self.agent('agent-a', turn(call('get_catalog')), turn(proposal('mic-standard')), turn(text='Owner review'))
        progress = []
        a = first.run('Find a USB mic.', progress=progress.append)
        second = self.agent('agent-b', turn(proposal('vacuum-standard')), turn(call('get_skill', resource='propose-purchase')),
                            turn(proposal('vacuum-budget')), turn(text='Compact option awaits owner review.'))
        b = second.run('Find a floor vacuum; compact is acceptable.')
        self.assertEqual((a['outcome'], b['outcome']), ('reserved_for_owner', 'reserved_for_owner'))
        self.assertEqual(b['proposals'], 2)
        self.assertTrue(any(e.get('result', {}).get('reason') == 'budget_exceeded' for e in b['events']))
        self.assertEqual(self.ledger.summary('fixture-home')['available_cents'], 3000)
        self.assertEqual(self.ledger.summary('fixture-home')['spent_cents'], 0)
        self.assertEqual(first.provider.generate.call_args.kwargs['tools_enabled'], False)
        self.assertTrue(progress)
        self.assertNotIn('hidden-fixture', json.dumps(a))
        self.assertNotIn('opaque-fixture', json.dumps(a))
        self.assertEqual(a['usage']['totalTokenCount'], 6)

    def test_model_prose_alone_cannot_reserve_or_claim_a_payment(self):
        agent = self.agent('agent-a', turn(text='I paid for the microphone.'))
        result = agent.run('Find a microphone.')
        self.assertEqual(result['outcome'], 'no_purchase')
        self.assertEqual(result['proposals'], 0)
        self.assertFalse(result['live_paypal'])
        self.assertEqual(self.ledger.summary('fixture-home')['encumbered_cents'], 0)

    def test_whole_oversized_batch_is_rejected_before_dispatch(self):
        agent = self.agent('agent-a', turn(*[call('get_catalog') for _ in range(9)]))
        result = agent.run('Find a microphone.')
        self.assertEqual((result['stop_reason'], result['tool_calls']), ('tool_limit', 0))

    def test_invalid_calls_cannot_reach_gateway_or_leak_arguments(self):
        agent = self.agent('agent-a', turn(call('approve', owner_token='synthetic-private-value')),
                           turn(text='Cannot approve.'))
        result = agent.run('Find a microphone.')
        self.assertEqual(result['tool_calls'], 1)
        self.assertEqual(result['proposals'], 0)
        self.assertNotIn('synthetic-private-value', json.dumps(result))
        self.assertEqual(self.ledger.summary('fixture-home')['encumbered_cents'], 0)

    def test_terminal_batch_prevents_followup_dispatch_and_extra_model_tools(self):
        agent = self.agent('agent-a', turn(proposal('mic-standard'), proposal('vacuum-budget')),
                           turn(proposal('vacuum-budget')))
        result = agent.run('Find a microphone.')
        self.assertEqual(result['proposals'], 1)
        self.assertEqual(result['outcome'], 'reserved_for_owner')
        self.assertEqual(self.ledger.summary('fixture-home')['encumbered_cents'], 22000)

    def test_provider_error_is_recorded_without_fallback_or_gateway_action(self):
        agent = self.agent('agent-a', ModelUnavailable('model_timeout'))
        progress = []
        result = agent.run('Find a microphone.', progress=progress.append)
        self.assertEqual(result['stop_reason'], 'model_timeout')
        self.assertEqual(result['model_calls'], 1)
        self.assertEqual(result['tool_calls'], 0)
        self.assertEqual(progress[-1]['phase'], 'error')

    def test_repeated_tool_reads_stop_at_eight(self):
        agent = self.agent('agent-a', *[turn(call('get_catalog')) for _ in range(8)], turn(text='Stopped.'))
        result = agent.run('Find a microphone.')
        self.assertEqual((result['tool_calls'], result['model_calls']), (8, 9))
        self.assertEqual(result['stop_reason'], 'tool_limit')

    def test_uncertain_transport_retry_reuses_one_reservation(self):
        original = self.gateway.propose
        keys = []
        def retry(principal, body):
            keys.append(body['request_key'])
            if len(keys) == 1:
                raise ConnectionError('synthetic lost reply')
            return original(principal, body)
        self.gateway.propose = retry
        agent = self.agent('agent-a', turn(proposal('mic-standard')), turn(proposal('mic-standard')), turn(text='Owner review'))
        result = agent.run('Find a microphone.')
        self.assertEqual(result['outcome'], 'reserved_for_owner')
        self.assertEqual(result['proposals'], 1)
        self.assertEqual(keys[0], keys[1])
        self.assertEqual(self.ledger.summary('fixture-home')['encumbered_cents'], 22000)

    def test_validation_rejects_owner_tools_and_noncanonical_arguments(self):
        self.assertTrue(valid_arguments('get_catalog', {}))
        self.assertTrue(valid_arguments('get_purchase', {'purchase_id': 'fixture-id'}))
        cases = [('get_catalog', []), ('get_catalog', {'extra': 1}), ('get_purchase', {'purchase_id': '../owner'}),
                 ('get_skill', {'resource': '../secret'}), ('approve', {}), ('propose_purchase', {'items': []}),
                 ('propose_purchase', {'items': [{'sku': 'mic-standard', 'quantity': True}]}),
                 ('propose_purchase', {'items': [{'sku': 'mic-standard', 'quantity': 1, 'price': 1}]})]
        for name, arguments in cases:
            self.assertFalse(valid_arguments(name, arguments))
        agent = self.agent('agent-a', turn())
        for request in ('', ' ' * 2, 'x' * 4001, None):
            with self.assertRaises(ValueError):
                agent.run(request)
        with self.assertRaises(ValueError):
            ShoppingAgent(agent.provider, agent.runner, 'prompt', [{'name': 'approve'}])
