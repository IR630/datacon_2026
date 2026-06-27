"""Provider-neutral LLM client."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class LLMNotConfigured(RuntimeError):
    pass


def _load_dotenv(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _load_api_txt(path: str | Path = "api.txt") -> dict[str, str]:
    api_path = Path(path)
    if not api_path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in api_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
        elif "YANDEX_API_KEY" not in values:
            values["YANDEX_API_KEY"] = line
    return values


@dataclass
class LLMSettings:
    provider: str = "disabled"
    model: str = ""
    base_url: str = ""
    api_key: str = ""
    api_key_source: str = ""
    yandex_folder_id: str = ""
    temperature: float = 0.0
    max_output_tokens: int = 1024

    @classmethod
    def from_env(cls) -> "LLMSettings":
        _load_dotenv()
        api_txt = _load_api_txt(os.environ.get("YANDEX_API_KEY_FILE", "api.txt"))

        yandex_api_key = os.environ.get("YANDEX_API_KEY", "") or api_txt.get("YANDEX_API_KEY", "")
        openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        provider = os.environ.get("LLM_PROVIDER", "")
        if not provider:
            provider = "yandex" if yandex_api_key else "disabled"

        if provider == "yandex":
            api_key = yandex_api_key or openai_api_key
            api_key_source = "YANDEX_API_KEY/api.txt" if yandex_api_key else "OPENAI_API_KEY"
            model = os.environ.get("LLM_MODEL", "") or api_txt.get("LLM_MODEL", "") or "deepseek-v4-flash"
            base_url = os.environ.get("OPENAI_BASE_URL", "") or "https://ai.api.cloud.yandex.net/v1"
        else:
            api_key = openai_api_key
            api_key_source = "OPENAI_API_KEY" if openai_api_key else ""
            model = os.environ.get("LLM_MODEL", "")
            base_url = os.environ.get("OPENAI_BASE_URL", "")

        return cls(
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            api_key_source=api_key_source,
            yandex_folder_id=os.environ.get("YANDEX_FOLDER_ID", "") or api_txt.get("YANDEX_FOLDER_ID", ""),
            temperature=float(os.environ.get("LLM_TEMPERATURE", "0") or 0),
            max_output_tokens=int(os.environ.get("LLM_MAX_OUTPUT_TOKENS", "1024") or 1024),
        )

    def resolved_model(self) -> str:
        if self.provider != "yandex":
            return self.model
        if self.model.startswith("gpt://"):
            return self.model
        if not self.yandex_folder_id:
            raise LLMNotConfigured("YANDEX_FOLDER_ID is empty")
        model_name = self.model or "deepseek-v4-flash"
        return f"gpt://{self.yandex_folder_id}/{model_name}"

    def sanitized_summary(self) -> dict[str, Any]:
        model = self.model or ("deepseek-v4-flash" if self.provider == "yandex" else "")
        resolved = ""
        if self.provider == "yandex" and self.yandex_folder_id:
            model_name = model.rsplit("/", 1)[-1] if model.startswith("gpt://") else model
            resolved = f"gpt://<folder_id>/{model_name}"
        elif self.provider != "yandex":
            resolved = model
        return {
            "provider": self.provider,
            "model": model,
            "resolved_model": resolved,
            "base_url": self.base_url,
            "api_key_present": bool(self.api_key),
            "api_key_source": self.api_key_source,
            "yandex_folder_id_present": bool(self.yandex_folder_id),
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
        }


class LLMClient:
    def __init__(self, settings: LLMSettings | None = None) -> None:
        self.settings = settings or LLMSettings.from_env()

    def _openai_client(self) -> Any:
        if self.settings.provider in {"", "disabled", "none"}:
            raise LLMNotConfigured("LLM_PROVIDER is disabled")
        if self.settings.provider not in {"openai", "openai_compatible", "yandex"}:
            raise LLMNotConfigured(f"Unsupported LLM_PROVIDER={self.settings.provider!r}")
        try:
            from openai import OpenAI
        except Exception as exc:
            raise LLMNotConfigured("openai package is not installed") from exc
        if not self.settings.api_key:
            name = "YANDEX_API_KEY" if self.settings.provider == "yandex" else "OPENAI_API_KEY"
            raise LLMNotConfigured(f"{name} is empty")

        kwargs: dict[str, Any] = {"api_key": self.settings.api_key}
        if self.settings.base_url:
            kwargs["base_url"] = self.settings.base_url
        if self.settings.provider == "yandex" and self.settings.yandex_folder_id:
            kwargs["project"] = self.settings.yandex_folder_id
        return OpenAI(**kwargs)

    def complete_text(self, messages: list[dict[str, str]], max_output_tokens: int | None = None) -> str:
        client = self._openai_client()
        model = self.settings.resolved_model()
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=self.settings.temperature,
            max_tokens=max_output_tokens or self.settings.max_output_tokens,
        )
        return resp.choices[0].message.content or ""

    def complete_json(self, messages: list[dict[str, str]], schema: dict[str, Any] | None = None) -> Any:
        client = self._openai_client()
        model = self.settings.resolved_model()
        if not model:
            raise LLMNotConfigured("LLM_MODEL is empty")

        response_format: dict[str, Any] = {"type": "json_object"}
        if schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {"name": "selt_extract", "schema": schema, "strict": True},
            }
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_output_tokens,
            response_format=response_format,
        )
        return resp.choices[0].message.content or ""
