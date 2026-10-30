"""Offline protocol/error checks using synthetic provider replies only."""

from copy import deepcopy
import io
import json
from pathlib import Path
import socket
import ssl
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

from goalguard.models import Gemini, ModelUnavailable, model_config


class Reply(io.BytesIO):
    code = 200


def answer(parts=None, **extra):
    return {"candidates": [{"content": {"role": "model", "parts": parts or [{"text": "Owner review required"}]},
                            "finishReason": "STOP"}], **extra}


class ModelTests(unittest.TestCase):
    def provider(self, value=None, error=None):
        provider = Gemini("synthetic-test-key", "fixture-model")
        provider._opener = Mock()
        if error is not None:
            provider._opener.open.side_effect = error
        else:
            provider._opener.open.return_value = Reply(json.dumps(value or {}).encode())
        return provider

    def test_configuration_uses_literal_values_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {}, clear=True):
            path = Path(directory) / "models.env"
            path.write_text("# local\nGEMINI_API_KEY='$(literal)'\nGEMINI_MODEL_A=fixture\n")
            self.assertEqual(model_config(path)["GEMINI_API_KEY"], "$(literal)")
            with patch.dict("os.environ", {"GEMINI_MODEL_A": "override"}):
                self.assertEqual(model_config(path)["GEMINI_MODEL_A"], "override")
            path.write_text("UNKNOWN=synthetic-private-value\n")
            with self.assertRaises(ValueError) as error:
                model_config(path)
            self.assertNotIn("synthetic-private-value", str(error.exception))
            self.assertEqual(model_config(Path(directory) / "missing")["GEMINI_API_KEY"], "")

    def test_invalid_credentials_model_or_timeout_fail_before_transport(self):
        for key, model, timeout in (("", "fixture", 60), ("has space", "fixture", 60),
                                    ("fixture", "../owner", 60), ("fixture", "ok", True),
                                    ("fixture", "ok", 9), ("fixture", "ok", 121)):
            with self.subTest(model=model, timeout=timeout), self.assertRaises(ValueError):
                Gemini(key, model, timeout=timeout)

    def test_generate_sends_only_declared_tools_and_parses_visible_parts(self):
        parts = [{"text": "hidden-fixture-thought", "thought": True},
                 {"functionCall": {"name": "get_catalog", "args": {}, "id": "call-fixture"},
                  "thoughtSignature": "opaque-fixture"}, {"text": "Owner review required"}]
        payload = answer(parts, usageMetadata={"totalTokenCount": 5, "promptTokenCount": 2,
                         "candidatesTokenCount": -1, "thoughtsTokenCount": True, "private": 99}, modelVersion="fixture-v1")
        provider = self.provider(payload)
        turn = provider.generate([], "system", [{"name": "get_catalog", "description": "catalog", "parameters": {}}], tools_enabled=False)
        self.assertEqual(turn.text, "Owner review required")
        self.assertEqual(turn.calls[0]["id"], "call-fixture")
        self.assertEqual(turn.usage, {"totalTokenCount": 5, "promptTokenCount": 2})
        self.assertEqual(turn.model_version, "fixture-v1")
        self.assertIn("thoughtSignature", turn.content["parts"][1])
        request = provider._opener.open.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(body["toolConfig"]["functionCallingConfig"]["mode"], "NONE")
        self.assertEqual(body["generationConfig"]["maxOutputTokens"], 2048)
        self.assertNotIn("synthetic-test-key", request.full_url)

    def test_generate_rejects_bad_candidates_and_call_shapes(self):
        invalid = [{}, {"candidates": []}, answer([{"functionCall": {"name": "x", "args": []}}]),
                   answer([{"functionCall": {"name": "x", "id": 1}}]), answer([None]),
                   {"candidates": [{"content": {"role": "user", "parts": []}}]},
                   {"candidates": [{"content": {"role": "model", "parts": "invalid"}}]}]
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(ModelUnavailable):
                self.provider(payload).generate([], "system", [])
        payload = answer()
        payload["candidates"][0]["finishReason"] = "MAX_TOKENS"
        with self.assertRaises(ModelUnavailable) as error:
            self.provider(payload).generate([], "system", [])
        self.assertEqual(error.exception.code, "model_incomplete_or_blocked")

    def test_extract_has_schema_no_tools_and_rejects_duplicates(self):
        provider = self.provider(answer([{"text": "hidden", "thought": True}, {"text": '{"cash":"$600"}'}],
                                        modelVersion="fixture", usageMetadata={"totalTokenCount": 4}))
        result = provider.extract("synthetic owner request", "system", {"type": "object"})
        self.assertEqual(result.value, {"cash": "$600"})
        body = json.loads(provider._opener.open.call_args.args[0].data)
        self.assertNotIn("tools", body)
        self.assertEqual(body["generationConfig"]["responseMimeType"], "application/json")
        for text in ('{"cash":1,"cash":2}', '[]', 'not-json'):
            with self.subTest(text=text), self.assertRaises(ModelUnavailable):
                self.provider(answer([{"text": text}])).extract("request", "system", {})
        for candidate in ({"parts": [{"functionCall": {}}]}, {"parts": None}):
            payload = answer()
            payload["candidates"][0]["content"] = deepcopy(candidate)
            with self.assertRaises(ModelUnavailable):
                self.provider(payload).extract("request", "system", {})

    def test_model_listing_filters_and_marks_pagination(self):
        provider = self.provider({"models": [
            {"name": "models/fixture", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/fixture", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/embedding", "supportedGenerationMethods": ["embedContent"]}], "nextPageToken": "next"})
        self.assertEqual(provider.list_models(), {"models": ["fixture"], "list_complete": False})
        for payload in ({}, {"models": [None]}, {"models": [{"name": 3}]}):
            with self.assertRaises(ModelUnavailable):
                self.provider(payload).list_models()

    def test_transport_errors_are_bounded_and_sanitized(self):
        errors = [(URLError(socket.gaierror(8, "synthetic-private-value")), "model_dns_unavailable"),
                  (URLError(TimeoutError()), "model_timeout"), (TimeoutError(), "model_timeout"),
                  (URLError(ssl.SSLError()), "model_tls_error"), (ssl.SSLError(), "model_tls_error"),
                  (URLError(ConnectionError()), "model_connection_closed"),
                  (ConnectionError(), "model_connection_closed"), (OSError(), "model_transport_error"),
                  (URLError("unclassified"), "model_transport_error")]
        for exception, code in errors:
            with self.subTest(code=code), self.assertRaises(ModelUnavailable) as error:
                self.provider(error=exception)._request_json(Request("https://example.invalid"))
            self.assertEqual(error.exception.code, code)
            self.assertNotIn("synthetic-private-value", str(error.exception))
        for status in (400, 401, 403, 404, 429, 500):
            error = HTTPError("https://example.invalid", status, "synthetic-private-value", {}, io.BytesIO())
            with self.subTest(status=status), self.assertRaises(ModelUnavailable) as raised:
                self.provider(error=error)._request_json(Request("https://example.invalid"))
            self.assertEqual(raised.exception.http_status, status)
            self.assertNotIn("synthetic-private-value", str(raised.exception))

    def test_response_size_and_json_shape_are_checked(self):
        for raw, code in ((b'x' * 524289, "model_response_too_large"), (b'[]', "model_malformed_response"),
                          (b'no-json', "model_malformed_response")):
            provider = self.provider()
            provider._opener.open.return_value = Reply(raw)
            with self.assertRaises(ModelUnavailable) as error:
                provider._request_json(Request("https://example.invalid"))
            self.assertEqual(error.exception.code, code)
