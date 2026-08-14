#!/usr/bin/env python3
"""Load-test the /api/activities/ course-listing endpoint (ActivityViewSet).

Standalone script, run directly with python3 (not via `manage.py shell` like
the other scripts in this directory) - it only talks HTTP, no Django/DB
access needed, so it can be pointed at a live tenant domain from any machine.

This endpoint is not gated by the registration period (no
`registration_open_required`, and its cache/queryset don't check
REGISTRATION_OPENED) - it can be load-tested with the period closed, no need
to reopen registrations first.

The tenant's KEPCHUP_LIMIT_BY_SCHOOL_YEAR setting decides which query param
the endpoint actually filters on server-side: --mode birth_date is wasted
traffic (ignored) on a school-year tenant, and vice-versa. Coppet doesn't
override this setting, so it uses the base.py default: school year (--mode
year), range 1-12 (KEPCHUP_YEAR_NAMES: 1P..11S,12R) - not age/birth_date.

Usage:
    python3 loadtest_activities.py https://coppet.kepchup.ch --concurrency 50 --duration 60

Examples:
    # Quick smoke test
    python3 loadtest_activities.py https://coppet.kepchup.ch --mode year --concurrency 5 --duration 10

    # Mimic ~400 requests/minute (Coppet is school-year based, not age-based)
    python3 loadtest_activities.py https://coppet.kepchup.ch --mode year --concurrency 30 --duration 120

    # Hit the bare endpoint with no query params, instead of varying year/birth_date
    python3 loadtest_activities.py https://coppet.kepchup.ch --mode none
"""
import argparse
import random
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from datetime import date
from datetime import timedelta


def build_url(base_url, birth_date=None, year=None):
    url = base_url.rstrip("/") + "/api/activities/"
    params = {}
    if birth_date:
        params["birth_date"] = birth_date
    if year:
        params["year"] = year
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return url


def random_birth_date():
    # Spread of realistic school-age birth dates, so requests also exercise the
    # per-request Python-side eligibility filtering, not just the cached payload.
    start = date.today() - timedelta(days=365 * 14)
    end = date.today() - timedelta(days=365 * 4)
    return (start + timedelta(days=random.randint(0, (end - start).days))).isoformat()


def do_request(url, timeout):
    started = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": "sportfac-loadtest"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read()
            return {"status": response.status, "elapsed": time.monotonic() - started, "size": len(body), "error": None}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "elapsed": time.monotonic() - started, "size": 0, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001 - report every failure mode, not just HTTP errors
        return {"status": None, "elapsed": time.monotonic() - started, "size": 0, "error": str(exc)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("base_url", help="e.g. https://coppet.kepchup.ch")
    parser.add_argument("--concurrency", type=int, default=20, help="concurrent workers (default: 20)")
    parser.add_argument("--duration", type=int, default=60, help="seconds to run (default: 60)")
    parser.add_argument("--timeout", type=float, default=10.0, help="per-request timeout in seconds (default: 10)")
    parser.add_argument(
        "--mode",
        choices=["birth_date", "year", "none"],
        default="birth_date",
        help="vary requests by birth_date/year (exercises per-request filtering) or hit the bare endpoint",
    )
    args = parser.parse_args()

    stop_at = time.monotonic() + args.duration
    results = []
    results_lock = threading.Lock()

    def worker():
        while time.monotonic() < stop_at:
            if args.mode == "birth_date":
                url = build_url(args.base_url, birth_date=random_birth_date())
            elif args.mode == "year":
                url = build_url(args.base_url, year=random.randint(1, 12))
            else:
                url = build_url(args.base_url)
            result = do_request(url, args.timeout)
            with results_lock:
                results.append(result)

    print(
        f"Hitting {args.base_url}/api/activities/ (mode={args.mode}) with {args.concurrency} workers "
        f"for {args.duration}s..."
    )
    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(worker) for _ in range(args.concurrency)]
        for future in as_completed(futures):
            future.result()  # re-raise any worker crash
    total_time = time.monotonic() - start

    if not results:
        print("No requests completed.")
        return

    latencies = sorted(r["elapsed"] for r in results)
    errors = [r for r in results if r["error"] or (r["status"] and r["status"] >= 400)]

    def pct(p):
        return latencies[min(int(len(latencies) * p), len(latencies) - 1)]

    print()
    print(f"Total requests: {len(results)}")
    print(f"Requests/min:   {len(results) / total_time * 60:.0f}")
    print(f"Errors:         {len(errors)} ({len(errors) / len(results) * 100:.1f}%)")
    mean_latency = sum(latencies) / len(latencies)
    print("Latency min/avg/p50/p95/p99/max (ms):")
    print(
        f"  {latencies[0] * 1000:.0f} / {mean_latency * 1000:.0f} / "
        f"{pct(0.50) * 1000:.0f} / {pct(0.95) * 1000:.0f} / {pct(0.99) * 1000:.0f} / {latencies[-1] * 1000:.0f}"
    )

    if errors:
        print()
        print("Sample errors:")
        for r in errors[:10]:
            print(f"  status={r['status']} error={r['error']}")


if __name__ == "__main__":
    main()
