from __future__ import annotations

import sentry_sdk
from prometheus_client import Counter, Gauge, Histogram, start_http_server


SIGNALS_DETECTED = Counter("signals_detected_total", "Topilgan signallar soni")
SIGNALS_DELIVERED = Counter("signals_delivered_total", "Yetkazilgan signallar soni")
SIGNALS_FAILED = Counter("signals_failed_total", "Yetkazilmagan signallar soni")
ACTIVE_MONITORS = Gauge("active_monitors", "Faol Telethon monitoring sessiyalari")
TELETHON_EVENTS = Counter("telethon_events_total", "Qabul qilingan Telethon eventlar soni")
SIGNAL_LATENCY = Histogram("signal_processing_seconds", "Signalni qayta ishlash vaqti")


def setup_sentry(dsn: str | None, environment: str) -> None:
    if not dsn:
        return
    sentry_sdk.init(dsn=dsn, environment=environment, traces_sample_rate=0.1)


def start_metrics_server(port: int) -> None:
    start_http_server(port)
