"""Live mode: chat completions forwarded to Azure OpenAI. The key stays on the server."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from workshop_kit.shell.config import settings

logger = logging.getLogger("llm_proxy.live")

# Logical model names accepted from the clients, mapped to the configured deployments.
ROLE_SETTINGS = {
    "default": "azure_openai_chat_deployment",
    "chat": "azure_openai_chat_deployment",
    "judge": "azure_openai_judge_deployment",
    "fallback": "azure_openai_fallback_deployment",
    "reranking": "azure_openai_reranking_deployment",
}


class LiveError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def missing_settings() -> list[str]:
    required = {
        "AZURE_OPENAI_API_KEY": settings.azure_openai_api_key,
        "AZURE_OPENAI_ENDPOINT": settings.azure_openai_endpoint,
        "AZURE_OPENAI_CHAT_DEPLOYMENT": settings.azure_openai_chat_deployment,
    }
    return [name for name, value in required.items() if not value]


def deployment_for(model: str | None) -> str:
    name = (model or "default").lower()
    for role, attribute in ROLE_SETTINGS.items():
        if role in name:
            deployment = getattr(settings, attribute)
            if deployment:
                return deployment
            if role == "fallback":
                raise LiveError(503, "live mode: AZURE_OPENAI_FALLBACK_DEPLOYMENT is not configured")
            break
    return settings.azure_openai_chat_deployment


def _url(deployment: str) -> tuple[str, bool]:
    parsed = urllib.parse.urlsplit(settings.azure_openai_endpoint.strip())
    path = parsed.path.rstrip("/")
    query = urllib.parse.parse_qs(parsed.query)
    # The unified v1 API takes the deployment as the model; the classic API puts it in the path.
    if path.endswith("/openai/v1"):
        return f"{parsed.scheme}://{parsed.netloc}{path}/chat/completions", True
    # The endpoint may be the resource root or a full operation URL copied from the portal.
    base = f"{parsed.scheme}://{parsed.netloc}"
    version = urllib.parse.quote((query.get("api-version") or [settings.azure_openai_api_version])[0])
    return f"{base}/openai/deployments/{urllib.parse.quote(deployment)}/chat/completions?api-version={version}", False


def chat(
    messages: list[dict[str, Any]],
    model: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    temperature: float | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    missing = missing_settings()
    if missing:
        raise LiveError(503, "live mode unavailable: missing settings " + ", ".join(missing))
    deployment = deployment_for(model)
    url, v1 = _url(deployment)
    payload: dict[str, Any] = {"messages": messages}
    if v1:
        payload["model"] = deployment
    if tools:
        payload["tools"] = tools
        # Recent reasoning models only accept function tools on chat completions without reasoning.
        payload["reasoning_effort"] = "none"
    if temperature is not None:
        payload["temperature"] = temperature
    try:
        return _post(url, payload, deployment, timeout)
    except LiveError as exc:
        if "reasoning_effort" in payload and exc.status_code == 400 and "reasoning_effort" in exc.detail:
            payload.pop("reasoning_effort")
            return _post(url, payload, deployment, timeout)
        raise


def _post(url: str, payload: dict[str, Any], deployment: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "api-key": settings.azure_openai_api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        logger.warning("azure call failed deployment=%s code=%s", deployment, exc.code)
        status = exc.code if exc.code in {400, 429} else 502
        raise LiveError(status, f"azure openai error {exc.code}: {body}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.warning("azure call unreachable deployment=%s", deployment)
        raise LiveError(502, f"azure openai unreachable: {getattr(exc, 'reason', exc)}") from exc
