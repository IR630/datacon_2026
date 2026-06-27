"""Vision table recovery placeholder."""

from __future__ import annotations


class VisionTableRecoveryAgent:
    def recover(self, image_path: str) -> dict:
        return {
            "image_path": image_path,
            "status": "not_configured",
            "message": "Configure a vision model before using table recovery.",
        }

