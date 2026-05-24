from __future__ import annotations

from app.services.healthcheck import LiciHealthcheckService

service = LiciHealthcheckService()


def health_full() -> dict:
    return service.full()
