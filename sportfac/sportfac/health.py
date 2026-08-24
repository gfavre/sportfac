"""Health checks shared by the public status endpoint (sportfac.urls) and the
superadmin dashboard (backend.views.health_views). Each check is self-contained and
never raises past run_checks() - a health check that crashes instead of reporting
"this component is down" defeats its own purpose, and would otherwise fall through to
Django's generic 500 handling (itself not safe to rely on here - see the
2026-08-24 incident notes in TECH_DEBT.md about request-time tenant resolution).

Deliberately dependency-free beyond what's already required in production (redis) -
disk/memory/load use the standard library (shutil.disk_usage, /proc/meminfo, os.getloadavg)
rather than adding psutil for this alone.
"""
import logging
import os
import shutil

from django.conf import settings
from django.core.cache import cache
from django.db import connection


logger = logging.getLogger(__name__)

OK = "ok"
WARNING = "warning"
CRITICAL = "critical"

DISK_WARNING_FREE_PERCENT = 15
DISK_CRITICAL_FREE_PERCENT = 5
MEMORY_WARNING_FREE_PERCENT = 15
MEMORY_CRITICAL_FREE_PERCENT = 5
LOAD_WARNING_RATIO = 1.0  # load average (1 min) per CPU core
LOAD_CRITICAL_RATIO = 2.0
# The Celery worker here runs at concurrency=1 (see registrations/tasks.py comments on
# why) - even a modest backlog means real delay, so these are deliberately conservative
# compared to a typical multi-worker setup.
QUEUE_WARNING_LENGTH = 20
QUEUE_CRITICAL_LENGTH = 100


def _check_database():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return OK, {}
    except Exception as exc:  # noqa: BLE001 - a health check must never itself crash
        return CRITICAL, {"error": str(exc)}


def _check_cache():
    try:
        key = "healthcheck-probe"
        cache.set(key, "1", timeout=5)
        return (OK if cache.get(key) == "1" else CRITICAL), {}
    except Exception as exc:  # noqa: BLE001
        return CRITICAL, {"error": str(exc)}


def _check_broker():
    broker_url = getattr(settings, "BROKER_URL", None)
    if not broker_url:
        return OK, {"note": "no BROKER_URL configured"}
    try:
        import redis

        redis.from_url(broker_url, socket_connect_timeout=2, socket_timeout=2).ping()
    except Exception as exc:  # noqa: BLE001
        return CRITICAL, {"error": str(exc)}

    detail = {}
    try:
        # sportfac.celery.app is already configured with this tenant's own
        # broker_url/key_prefix (see sportfac/celery.py) - channel._size() is the same
        # thing kombu's own queue_declare(passive=True) reports as message_count,
        # called directly to avoid its passive-declare erroring on a queue nothing has
        # bound yet (shouldn't happen with a running worker, but a health check
        # shouldn't assume that either).
        from sportfac.celery import app as celery_app

        queue_name = celery_app.conf.task_default_queue
        with celery_app.connection_or_acquire() as conn:
            queue_length = conn.default_channel._size(queue_name)
        detail = {"queue": queue_name, "queue_length": queue_length}
    except Exception as exc:  # noqa: BLE001
        detail = {"queue_length_error": str(exc)}

    queue_length = detail.get("queue_length", 0)
    if queue_length >= QUEUE_CRITICAL_LENGTH:
        return CRITICAL, detail
    if queue_length >= QUEUE_WARNING_LENGTH:
        return WARNING, detail
    return OK, detail


def _check_disk():
    path = settings.MEDIA_ROOT if os.path.isdir(settings.MEDIA_ROOT) else "/"
    try:
        usage = shutil.disk_usage(path)
    except Exception as exc:  # noqa: BLE001
        return CRITICAL, {"error": str(exc)}
    free_percent = usage.free / usage.total * 100
    detail = {
        "free_percent": round(free_percent, 1),
        "free_gb": round(usage.free / 1024**3, 1),
        "total_gb": round(usage.total / 1024**3, 1),
    }
    if free_percent < DISK_CRITICAL_FREE_PERCENT:
        return CRITICAL, detail
    if free_percent < DISK_WARNING_FREE_PERCENT:
        return WARNING, detail
    return OK, detail


def _check_memory():
    try:
        meminfo = {}
        with open("/proc/meminfo") as f:
            for line in f:
                key, _, rest = line.partition(":")
                meminfo[key] = int(rest.strip().split()[0])  # kB
    except FileNotFoundError:
        return OK, {"note": "unavailable on this platform"}
    except Exception as exc:  # noqa: BLE001
        return CRITICAL, {"error": str(exc)}

    total = meminfo.get("MemTotal")
    available = meminfo.get("MemAvailable", meminfo.get("MemFree"))
    if not total or available is None:
        return OK, {"note": "unavailable on this platform"}

    free_percent = available / total * 100
    detail = {
        "free_percent": round(free_percent, 1),
        "available_mb": round(available / 1024),
        "total_mb": round(total / 1024),
    }
    if free_percent < MEMORY_CRITICAL_FREE_PERCENT:
        return CRITICAL, detail
    if free_percent < MEMORY_WARNING_FREE_PERCENT:
        return WARNING, detail
    return OK, detail


def _check_load():
    try:
        load1, load5, load15 = os.getloadavg()
    except (OSError, AttributeError):
        return OK, {"note": "unavailable on this platform"}
    cpu_count = os.cpu_count() or 1
    ratio = load1 / cpu_count
    detail = {
        "load1": round(load1, 2),
        "load5": round(load5, 2),
        "load15": round(load15, 2),
        "cpu_count": cpu_count,
    }
    # A load average up to the core count means the box is fully busy, not overloaded -
    # every core has something to do, nothing is queueing yet. Queueing (processes
    # waiting for a free core) is what actually signals trouble, and that only starts
    # past that point - hence strict ">" rather than ">=": load == cpu_count is still ok.
    if ratio > LOAD_CRITICAL_RATIO:
        return CRITICAL, detail
    if ratio > LOAD_WARNING_RATIO:
        return WARNING, detail
    return OK, detail


CHECKS = {
    "database": _check_database,
    "cache": _check_cache,
    "broker": _check_broker,
    "disk": _check_disk,
    "memory": _check_memory,
    "load": _check_load,
}


def run_checks():
    """Run every check. Never lets one raise past this function."""
    results = {}
    for name, check in CHECKS.items():
        try:
            level, detail = check()
        except Exception as exc:  # noqa: BLE001 - last-resort net
            logger.exception("Health check %r crashed", name)
            level, detail = CRITICAL, {"error": str(exc)}
        results[name] = {"level": level, "detail": detail}
    return results


def overall_level(results):
    levels = {r["level"] for r in results.values()}
    if CRITICAL in levels:
        return CRITICAL
    if WARNING in levels:
        return WARNING
    return OK
