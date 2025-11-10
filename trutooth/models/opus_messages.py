from __future__ import annotations
"""Stub for Opus messages handling (codec wrapper).

This file is a placeholder for the Opus encoder/decoder abstraction shown in
the diagram. It intentionally has no external audio dependencies; integrate
real encoding libraries when implementing audio paths.
"""
from typing import Any


class OpusMessages:
    def encode(self, pcm: bytes) -> bytes:
        """Encode raw PCM to Opus (stub)."""
        # TODO: integrate an actual Opus encoder
        return pcm

    def decode(self, opus_payload: bytes) -> bytes:
        """Decode Opus payload to PCM (stub)."""
        # TODO: integrate an actual Opus decoder
        return opus_payload
