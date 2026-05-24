from __future__ import annotations

from app.services.observability import ObservabilityService

service = ObservabilityService()


def observability_status() -> dict:
    return service.status()
