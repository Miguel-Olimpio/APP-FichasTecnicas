"""Nomes de arquivo seguros e normalização de texto para chaves."""

from __future__ import annotations

import re


def normalize_name_key(name: object) -> str:
    return str(name or "").strip().lower()


def safe_filename(name: object) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_- "
    clean = "".join(ch for ch in str(name) if ch in allowed).strip().replace(" ", "_")
    return clean or "produto"


def pdf_filename_stem(nome_normalizado: str, timestamp: str) -> str:
    base = safe_filename(nome_normalizado) or "produto"
    return f"{base}_{timestamp}"
