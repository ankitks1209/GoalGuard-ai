"""Offline transport checks; no real sockets or credentials."""

import io
import json
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

from goalguard.gateway import Principal
from goalguard.http_tools import NoRedirect, ScopedHTTPGateway
from goalguard.ledger import Rejection


class Reply(io.BytesIO):
    def __init__(self, value, status=200, *, raw=None):
        super().__init__(json.dumps(value).encode() if raw is None else raw)
        self.code = status


class HTTPToolTests(unittest.TestCase):
    def gateway(self, response=None, error=None):
        gateway = ScopedHTTPGateway('agent-a', 'a' * 40)
        gateway._opener = Mock()
        if error:
            gateway._opener.open.side_effect = error
        else:
            gateway._opener.open.return_value = response or Reply({})
        return gateway

    def test_credentials_scope_port_and_redirects(self):
        for actor, token, port in (('owner', 'a' * 40, 8765), ('agent-a', 'short', 8765),
                                    ('agent-a', 'a b' * 20, 8765), ('agent-a', 'a' * 40, True),
                                    ('agent-a', 'a' * 40, 0), ('agent-a', 'a' * 40, 65536)):
            with self.assertRaises(ValueError):
                ScopedHTTPGateway(actor, token, port=port)
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.invalid'))

    def test_owner_routes_are_rejected_before_io(self):
        gateway = self.gateway()
        for method, path in (('POST', '/v1/approve'), ('GET', '/v1/plan'),
                             ('GET', 'https://example.invalid'), ('GET', '/v1/purchases/id/audit')):
            with self.assertRaises(Rejection):
                gateway.request(method, path)
        gateway._opener.open.assert_not_called()

    def test_proposal_and_catalog_results_are_allowlisted(self):
        gateway = self.gateway(Reply({'decision': 'reserved', 'purchase': {'id': 'fixture', 'state': 'reserved',
                                      'amount_cents': 100, 'permit': 'private-fixture'}, 'bills': ['private-fixture']}))
        actor = Principal('demo-home', 'agent-a', 'agent')
        result = gateway.propose(actor, {'items': [], 'request_key': 'fixture'})
        self.assertEqual(result['decision'], 'reserved')
        self.assertNotIn('private-fixture', json.dumps(result))
        req = gateway._opener.open.call_args.args[0]
        self.assertEqual(req.full_url, 'http://127.0.0.1:8765/v1/proposals')
        self.assertEqual(json.loads(req.data)['request_key'], 'fixture')
        gateway = self.gateway(Reply({'products': []}))
        self.assertEqual(gateway.catalog.public(), [])
        with self.assertRaises(TimeoutError):
            self.gateway(Reply({'products': 'invalid'})).catalog.public()
        malformed = self.gateway()
        malformed.request = Mock(return_value={'products': 'invalid'})
        with self.assertRaises(Rejection):
            malformed.catalog.public()

    def test_uncertain_responses_preserve_retry_semantics(self):
        cases = [Reply({}, 500), Reply({}, raw=b'x' * 262145), Reply({}, raw=b'not-json'),
                 Reply([], 200), Reply({}, 403)]
        for response in cases:
            with self.subTest(status=response.code), self.assertRaises(TimeoutError):
                self.gateway(response).request('POST', '/v1/proposals', {})
        with self.assertRaises(TimeoutError):
            self.gateway(Reply({'decision': 'pending'})).propose(Principal('demo-home', 'agent-a', 'agent'), {})
        with self.assertRaises(ConnectionError):
            self.gateway(error=URLError('synthetic-fixture')).request('GET', '/v1/catalog')
        broken = Reply({})
        broken.read = Mock(side_effect=OSError('synthetic-fixture'))
        with self.assertRaises(ConnectionError):
            self.gateway(broken).request('GET', '/v1/catalog')

    def test_http_denial_and_purchase_scope(self):
        error = HTTPError('http://127.0.0.1', 403, '', {}, io.BytesIO(b'{"reason":"forbidden"}'))
        self.assertEqual(self.gateway(error=error).request('GET', '/v1/catalog')['reason'], 'forbidden')
        gateway = self.gateway(Reply({'id': 'fixture-id', 'state': 'reserved'}))
        actor = Principal('demo-home', 'agent-a', 'agent')
        self.assertEqual(gateway.inspect(actor, 'fixture-id')['id'], 'fixture-id')
        for identity, role in (('agent-b', 'agent'), ('owner', 'owner')):
            with self.assertRaises(Rejection):
                gateway.propose(Principal('demo-home', identity, role), {})
        for purchase in ('../owner', '', None, 'x' * 129):
            with self.assertRaises(Rejection):
                gateway.inspect(actor, purchase)

    def test_fingerprint_accepts_only_sku_and_integer_quantity(self):
        catalog = self.gateway().catalog
        items = [{'sku': 'fixture', 'quantity': 1}]
        self.assertEqual(catalog.quote(items).cart_hash, catalog.quote(items).cart_hash)
        for invalid in (None, [], [{}], [{'sku': 'x', 'quantity': True}],
                        [{'sku': 'x', 'quantity': 101}], [{'sku': 'x', 'quantity': 1, 'price': 1}]):
            with self.assertRaises(Rejection):
                catalog.quote(invalid)
