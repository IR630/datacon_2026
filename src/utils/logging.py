"""Tiny logging helpers for CLI output."""

from __future__ import annotations


def warn(message: str) -> None:
    print(f"[warn] {message}")


def info(message: str) -> None:
    print(f"[info] {message}")

