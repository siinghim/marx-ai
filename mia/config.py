# mia/config.py
from __future__ import annotations

import os
import re
from pathlib import Path
from dataclasses import dataclass, field

import yaml


@dataclass
class LLMConfig:
    provider: str = "deepseek"
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.2
    max_tokens: int = 1200


@dataclass
class EmbeddingConfig:
    model: str = "BAAI/bge-m3"
    device: str = "auto"


@dataclass
class IndexConfig:
    dir: str = "data/mia_index"
    topk: int = 5
    max_candidates: int = 50


@dataclass
class ChunkingConfig:
    size: int = 700
    overlap: int = 100


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8000


@dataclass
class SessionsConfig:
    max_history_turns: int = 20


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    index: IndexConfig = field(default_factory=IndexConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    sessions: SessionsConfig = field(default_factory=SessionsConfig)


def _interpolate_env(value: str) -> str:
    """Replace ${VAR} with os.environ[VAR]."""
    pattern = re.compile(r"\$\{(\w+)\}")
    if not isinstance(value, str):
        return value
    if pattern.search(value):
        def replacer(m):
            var_name = m.group(1)
            return os.environ.get(var_name, "")
        return pattern.sub(replacer, value)
    return value


def _apply_env(d: dict) -> dict:
    """Walk a nested dict and interpolate env vars in all string values."""
    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _apply_env(v)
        elif isinstance(v, str):
            result[k] = _interpolate_env(v)
        else:
            result[k] = v
    return result


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    path = Path(path)
    if not path.exists():
        return AppConfig()

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    raw = _apply_env(raw)

    llm = LLMConfig(**raw.get("llm", {}))
    embedding = EmbeddingConfig(**raw.get("embedding", {}))
    index = IndexConfig(**raw.get("index", {}))
    chunking = ChunkingConfig(**raw.get("chunking", {}))
    server = ServerConfig(**raw.get("server", {}))
    sessions = SessionsConfig(**raw.get("sessions", {}))

    return AppConfig(
        llm=llm,
        embedding=embedding,
        index=index,
        chunking=chunking,
        server=server,
        sessions=sessions,
    )
