from __future__ import annotations

import difflib
from collections.abc import Mapping, Sequence


def parse_model(ref: str) -> tuple[str, str]:
    provider, separator, model = ref.partition("/")
    if not separator or not provider or not model:
        raise ValueError(f"Modelo invalido, esperado 'provider/model': {ref!r}")
    return provider, model


def closest_model(ref: str, available: Sequence[str]) -> str:
    if ref in available:
        return ref
    matches = difflib.get_close_matches(ref, list(available), n=1, cutoff=0.5)
    if not matches:
        raise LookupError(f"Nenhum modelo proximo de {ref!r}")
    return matches[0]


def default_model(provider: str, catalog: Mapping) -> str:
    models = catalog.get(provider, {}).get("models", {})
    if not models:
        raise KeyError(provider)
    for model_id, meta in models.items():
        if isinstance(meta, dict) and meta.get("default"):
            return model_id
    return next(iter(models))
