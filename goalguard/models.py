"""Minimal Gemini generateContent adapter. No payment or database capabilities."""

from copy import deepcopy
from dataclasses import dataclass
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import socket
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from .http_tools import NoRedirect


MODEL_KEYS = ("GEMINI_API_KEY", "GEMINI_MODEL_A", "GEMINI_MODEL_B")


def model_config(path: Path):
    values = {}
    if path.exists():
        for number, line in enumerate(path.read_text().splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator or key.strip() not in MODEL_KEYS:
                raise ValueError(f"Unsupported model configuration on line {number}; values not logged.")
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            values[key.strip()] = value
    return {key: os.environ.get(key) or values.get(key, "") for key in MODEL_KEYS}


class ModelUnavailable(Exception):
    def __init__(self, code, *, http_status=None):
        self.code = code
        self.http_status = http_status
        super().__init__(code)  # Never include provider bodies, headers or keys.


@dataclass(frozen=True)
class ModelTurn:
    content: dict
    calls: tuple
    text: str
    usage: dict
    model_version: str | None


@dataclass(frozen=True)
class StructuredTurn:
    value: dict
    usage: dict
    model_version: str | None


class Gemini:
    provider = "gemini"

    def __init__(self, api_key, model, *, timeout=60, max_output_tokens=2048):
        if not isinstance(api_key, str) or not api_key or any(c.isspace() for c in api_key):
            raise ValueError("Configure GEMINI_API_KEY privately in .env.models.")
        if not isinstance(model, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", model):
            raise ValueError("Configure a valid Gemini model ID.")
        if type(timeout) is not int or not 10 <= timeout <= 120:
            raise ValueError("Model request timeout must be 10 to 120 seconds.")
        self.model = model
        self._api_key = api_key
        self.timeout_seconds = timeout
        self.max_output_tokens = max_output_tokens
        self._opener = build_opener(ProxyHandler({}), NoRedirect())

    def _request_json(self, request):
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                raw = response.read(524_289)
        except HTTPError as error:
            code = {400: "model_request_rejected", 401: "model_auth_failed", 403: "model_access_denied",
                    404: "model_not_available", 429: "model_rate_limited"}.get(error.code, "model_http_error")
            status = error.code
            error.close()
            raise ModelUnavailable(code, http_status=status) from None
        except URLError as error:
            if isinstance(error.reason, socket.gaierror):
                code = "model_dns_unavailable"
            elif isinstance(error.reason, TimeoutError):
                code = "model_timeout"
            elif isinstance(error.reason, ssl.SSLError):
                code = "model_tls_error"
            elif isinstance(error.reason, ConnectionError):
                code = "model_connection_closed"
            else:
                code = "model_transport_error"
            raise ModelUnavailable(code) from None
        except TimeoutError:
            raise ModelUnavailable("model_timeout") from None
        except ssl.SSLError:
            raise ModelUnavailable("model_tls_error") from None
        except (ConnectionError, HTTPException):
            raise ModelUnavailable("model_connection_closed") from None
        except OSError:
            raise ModelUnavailable("model_transport_error") from None
        if len(raw) > 524_288:
            raise ModelUnavailable("model_response_too_large")
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError
            return data
        except (ValueError, TypeError):
            raise ModelUnavailable("model_malformed_response") from None

    def list_models(self):
        """One metadata request, no generation, shopping task or gateway access."""
        request = Request("https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000",
                          headers={"x-goog-api-key": self._api_key})
        data = self._request_json(request)
        models = data.get("models")
        if not isinstance(models, list):
            raise ModelUnavailable("model_malformed_response")
        names = []
        for model in models:
            if not isinstance(model, dict) or not isinstance(model.get("name"), str):
                raise ModelUnavailable("model_malformed_response")
            name = model["name"].removeprefix("models/")
            if ("generateContent" in model.get("supportedGenerationMethods", [])
                    and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", name)):
                names.append(name)
        return {"models": sorted(set(names)), "list_complete": not bool(data.get("nextPageToken"))}

    def extract(self, request_text, system, schema):
        """One schema-guided extraction request, with no tools or conversation state."""
        body = {"contents": [{"role": "user", "parts": [{"text": request_text}]}],
                "systemInstruction": {"parts": [{"text": system}]},
                "generationConfig": {"temperature": 0, "candidateCount": 1,
                                     "maxOutputTokens": 4096,
                                     "responseMimeType": "application/json",
                                     "responseJsonSchema": schema}}
        request = Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            data=json.dumps(body, allow_nan=False).encode(), method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self._api_key})
        data = self._request_json(request)
        try:
            candidate, = data.get("candidates", [])
            if candidate.get("finishReason") not in {None, "STOP"}:
                raise ModelUnavailable("model_incomplete_or_blocked")
            parts = candidate["content"]["parts"]
            if not isinstance(parts, list) or any("functionCall" in p for p in parts):
                raise ValueError
            visible = "".join(p["text"] for p in parts if not p.get("thought") and "text" in p)
            def unique_object(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("Duplicate structured-output field.")
                    result[key] = value
                return result
            value = json.loads(visible, object_pairs_hook=unique_object)
            if not isinstance(value, dict):
                raise ValueError
            usage = {k: v for k, v in data.get("usageMetadata", {}).items()
                     if k in {"promptTokenCount", "candidatesTokenCount", "thoughtsTokenCount", "totalTokenCount"}
                     and type(v) is int and v >= 0}
            version = data.get("modelVersion")
            return StructuredTurn(value, usage, version if isinstance(version, str) else None)
        except (ValueError, KeyError, TypeError, AttributeError):
            raise ModelUnavailable("model_invalid_structured_output") from None

    def generate(self, contents, system, tools, *, tools_enabled=True):
        declarations = [{"name": t["name"], "description": t["description"],
                         "parametersJsonSchema": t["parameters"]} for t in tools]
        body = {"contents": contents, "systemInstruction": {"parts": [{"text": system}]},
                "generationConfig": {"temperature": 0, "maxOutputTokens": self.max_output_tokens,
                                     "candidateCount": 1}}
        if declarations:
            body["tools"] = [{"functionDeclarations": declarations}]
            body["toolConfig"] = {"functionCallingConfig": {"mode": "AUTO" if tools_enabled else "NONE"}}
        request = Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            data=json.dumps(body, allow_nan=False).encode(), method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self._api_key})
        data = self._request_json(request)
        try:
            candidate, = data.get("candidates", [])
            if candidate.get("finishReason") not in {None, "STOP"}:
                raise ModelUnavailable("model_incomplete_or_blocked")
            content = deepcopy(candidate["content"])
            if content.get("role") != "model" or not isinstance(content.get("parts"), list):
                raise ValueError
            calls, text = [], []
            for part in content["parts"]:
                if not isinstance(part, dict):
                    raise ValueError
                if "functionCall" in part:
                    call = part["functionCall"]
                    if (not isinstance(call, dict) or not isinstance(call.get("name"), str)
                            or not isinstance(call.get("args", {}), dict)):
                        raise ValueError
                    if "id" in call and not isinstance(call["id"], str):
                        raise ValueError
                    calls.append({"name": call["name"], "args": call.get("args", {}),
                                  **({"id": call["id"]} if "id" in call else {})})
                if not part.get("thought") and isinstance(part.get("text"), str):
                    text.append(part["text"])
            usage = {k: v for k, v in data.get("usageMetadata", {}).items()
                     if k in {"promptTokenCount", "candidatesTokenCount", "thoughtsTokenCount", "totalTokenCount"}
                     and type(v) is int and v >= 0}
            version = data.get("modelVersion")
            if not isinstance(version, str):
                version = None
            # Keep the complete content (including opaque thought signatures) in
            # memory for protocol continuation. Never store hidden thought parts.
            return ModelTurn(content, tuple(calls), "\n".join(text), usage, version)
        except (ValueError, KeyError, TypeError, AttributeError):
            raise ModelUnavailable("model_malformed_response") from None
