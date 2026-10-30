"""Owner-plan draft characterization with synthetic structured output; no live AI."""

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from goalguard import Ledger
from goalguard.catalog import Catalog
from goalguard.drafting import PlanDrafter, validate_extraction
from goalguard.gateway import Gateway, Principal
from goalguard.ledger import Rejection
from goalguard.models import StructuredTurn


NOW = datetime(2026, 10, 20, 12, tzinfo=timezone.utc).timestamp()
REQUEST = ('Cash $600 excluding separately held savings; buffer $50. '
           'Utilities $100 due 2026-10-25. Income $400 on 2026-10-30. '
           'Studio target $600, saved $300, deadline 2026-12-28.')


def extraction():
    return {'opening_cash': '$600', 'buffer': '$50',
            'income': {'amount': '$400', 'date': '2026-10-30'},
            'bills': [{'name': 'Utilities', 'amount': '$100', 'date': '2026-10-25'}],
            'goal': {'title': 'Studio', 'target': '$600', 'saved': '$300', 'date': '2026-12-28', 'contribution': None},
            'no_income_quote': None, 'no_bills_quote': None, 'no_goal_quote': None,
            'unsupported_currency_quotes': [], 'clarifications': []}


class DraftingTests(unittest.TestCase):
    def drafter(self, value=None):
        provider = Mock(provider='synthetic-fixture', model='fixture')
        provider.extract.return_value = StructuredTurn(extraction() if value is None else value,
                                                       {'totalTokenCount': 5}, 'fixture-version')
        return PlanDrafter(provider)

    def draft(self, value=None, request=REQUEST):
        return self.drafter(value).draft(request, 'UTC', 'USD', True, clock=lambda: NOW)

    def test_complete_draft_computes_contribution_without_confirming(self):
        result = self.draft()
        self.assertEqual(result['status'], 'draft_ready')
        self.assertEqual(result['plan']['goal']['contribution_cents'], 10000)
        self.assertEqual(result['calculation']['available_cents'], 35000)
        self.assertIn('goal.contribution_cents', result['computed_fields'])
        self.assertTrue(result['requires_owner_confirmation'])
        self.assertTrue(result['manual_entry_available'])
        self.assertEqual(result['usage']['totalTokenCount'], 5)

    def test_consent_input_currency_and_timezone_fail_before_model(self):
        drafter = self.drafter()
        cases = [(REQUEST, 'UTC', 'USD', False), (REQUEST, 'UTC', 'USD', 1),
                 ('', 'UTC', 'USD', True), ('x' * 4001, 'UTC', 'USD', True),
                 (REQUEST, 'bad/zone', 'USD', True), (REQUEST, None, 'USD', True),
                 (REQUEST, 'UTC', 'EUR', True)]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(Rejection):
                drafter.draft(*args, clock=lambda: NOW)
        drafter.provider.extract.assert_not_called()

    def test_foreign_currency_uses_manual_path_without_a_model_call(self):
        for marker in ('INR', 'euros', '₹', '€'):
            drafter = self.drafter()
            result = drafter.draft(REQUEST + ' ' + marker, 'UTC', 'USD', True, clock=lambda: NOW)
            self.assertEqual(result['status'], 'needs_manual_entry')
            self.assertFalse(result['model_call_attempted'])
            drafter.provider.extract.assert_not_called()

    def test_missing_unsourced_signed_or_relative_values_require_clarification(self):
        changes = [('opening_cash', None), ('opening_cash', '$999'), ('buffer', '$-50')]
        for field, value in changes:
            sample = extraction()
            sample[field] = value
            with self.subTest(field=field, value=value):
                result = self.draft(sample)
                self.assertEqual(result['status'], 'needs_clarification')
                self.assertIsNone(result['plan'])
        for literal in ('$-651', '-$651', '$651.001', '$651%'):
            sample = extraction()
            sample['opening_cash'] = literal
            self.assertEqual(self.draft(sample, REQUEST + ' ' + literal)['status'], 'needs_clarification')
        sample = extraction()
        sample['income']['date'] = 'tomorrow'
        self.assertEqual(self.draft(sample, REQUEST + ' tomorrow')['status'], 'needs_clarification')

    def test_amount_boundaries_accept_punctuation_but_not_numeric_prefixes(self):
        for punctuation in ('.', ',', ';'):
            self.assertEqual(self.draft(request=REQUEST.replace('$50.', '$50' + punctuation))['status'], 'draft_ready')
        for source in ('$651.25', '$651,000', '- $651', '$651 %'):
            sample = extraction()
            sample['opening_cash'] = '$651'
            self.assertEqual(self.draft(sample, REQUEST + ' ' + source)['status'], 'needs_clarification')

    def test_schema_errors_fall_back_to_manual_entry(self):
        invalid = [{}, {**extraction(), 'unexpected': True}, {**extraction(), 'bills': 'invalid'},
                   {**extraction(), 'bills': [{}]}, {**extraction(), 'opening_cash': 600},
                   {**extraction(), 'clarifications': [True]}, {**extraction(), 'bills': extraction()['bills'] * 21}]
        for value in invalid:
            with self.subTest(value=value):
                result = self.draft(value)
                self.assertEqual(result['status'], 'needs_manual_entry')
                self.assertEqual(result['issues'][0]['code'], 'invalid_draft_schema')
        with self.assertRaises(Rejection):
            validate_extraction({**extraction(), 'no_goal_quote': 'x' * 241})

    def test_explicit_absence_is_distinct_from_missing_information(self):
        value = extraction()
        value.update(income=None, bills=[], goal=None, no_income_quote='no income',
                     no_bills_quote='no bills', no_goal_quote='no goal')
        result = self.draft(value, 'Cash $600 buffer $50; no income, no bills, no goal.')
        self.assertEqual(result['status'], 'draft_ready')
        self.assertFalse(result['calculation']['can_propose'])
        value.update(no_income_quote=None, no_bills_quote=None, no_goal_quote=None)
        self.assertEqual(self.draft(value)['status'], 'needs_clarification')
        value['no_goal_quote'] = 'Studio'
        self.assertEqual(self.draft(value)['status'], 'needs_clarification')

    def test_conflicts_model_questions_and_currency_quotes_remain_visible(self):
        for field, quote in (('no_income_quote', 'no income'), ('no_bills_quote', 'no bills'), ('no_goal_quote', 'no goal')):
            sample = extraction()
            sample[field] = quote
            self.assertEqual(self.draft(sample, REQUEST + ' ' + quote)['status'], 'needs_clarification')
        for currency in ('foreign-currency', 'absent-quote'):
            sample = extraction()
            sample['unsupported_currency_quotes'] = [currency]
            self.assertEqual(self.draft(sample, REQUEST + ' foreign-currency')['status'], 'needs_clarification')
        sample = extraction()
        sample['clarifications'] = ['Which cash balance do you mean?']
        self.assertIn('Which cash balance do you mean?', self.draft(sample)['questions'])

    def test_labels_and_explicit_installments_preserve_owner_values(self):
        sample = extraction()
        sample['bills'][0]['name'] = None
        sample['goal']['title'] = None
        sample['goal']['contribution'] = '$50'
        result = self.draft(sample)
        self.assertEqual(result['plan']['bills'][0]['name'], 'Bill 1')
        self.assertEqual(result['plan']['goal']['title'], 'Savings target')
        self.assertEqual(result['plan']['goal']['contribution_cents'], 5000)
        self.assertTrue(result['calculation']['goal']['schedule_off_track'])
        sample['goal']['title'] = 'not supplied'
        self.assertEqual(self.draft(sample)['status'], 'needs_clarification')

    def test_invalid_goal_deadline_and_money_bounds_never_make_a_plan(self):
        sample = extraction()
        sample['goal']['date'] = '2020-01-01'
        self.assertEqual(self.draft(sample, REQUEST + ' 2020-01-01')['status'], 'needs_clarification')
        sample = extraction()
        sample['opening_cash'] = '$999999999999999'
        self.assertEqual(self.draft(sample, REQUEST + ' $999999999999999')['status'], 'needs_clarification')

    def test_gateway_draft_is_owner_only_and_saved_without_activation(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / 'ledger.sqlite', now=lambda: NOW)
            ledger.create_household('home', 0, 0)
            drafter = self.drafter()
            gateway = Gateway(ledger, Catalog(), require_plan=True, drafter=drafter)
            owner = Principal('home', 'owner', 'owner')
            actor = Principal('home', 'agent-a', 'agent')
            body = {'request': REQUEST, 'timezone': 'UTC', 'currency': 'USD', 'allow_model_processing': True}
            with self.assertRaises(Rejection):
                gateway.plan(actor, 'draft', body)
            drafter.provider.extract.assert_not_called()
            result = gateway.plan(owner, 'draft', body)
            self.assertEqual(result['status'], 'draft_ready')
            snapshot = gateway.plan(owner)
            self.assertIsNone(snapshot['plan'])
            self.assertIsNotNone(snapshot['draft'])
            with self.assertRaises(Rejection):
                gateway.propose(actor, {'items': [{'sku': 'mic-budget', 'quantity': 1}], 'request_key': 'fixture'})
            confirmed = gateway.plan(owner, 'confirm', {'plan': result['plan'], 'mode': 'activate',
                                                      'preview_hash': result['preview']['preview_hash']})
            self.assertIsNotNone(confirmed)
            with self.assertRaises(Rejection) as error:
                gateway.plan(owner, 'draft', body)
            self.assertEqual(error.exception.code, 'draft_initial_only')
            self.assertEqual(drafter.provider.extract.call_count, 1)
            gateway.drafter = None
            with self.assertRaises(Rejection) as error:
                gateway.plan(owner, 'draft', body)
            self.assertEqual(error.exception.code, 'draft_unavailable')

    def test_gateway_keeps_incomplete_draft_out_of_saved_plan(self):
        sample = deepcopy(extraction())
        sample['opening_cash'] = None
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / 'ledger.sqlite', now=lambda: NOW)
            ledger.create_household('home', 0, 0)
            gateway = Gateway(ledger, Catalog(), drafter=self.drafter(sample))
            owner = Principal('home', 'owner', 'owner')
            self.assertEqual(gateway.plan(owner, 'draft', {'request': REQUEST, 'timezone': 'UTC',
                             'currency': 'USD', 'allow_model_processing': True})['status'], 'needs_clarification')
            self.assertIsNone(gateway.plan(owner)['draft'])
