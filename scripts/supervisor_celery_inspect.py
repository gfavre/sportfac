#!/usr/bin/env python3
"""Run `celery inspect active/reserved/stats` for every tenant's Celery worker, using
each tenant's own supervisor conf environment and working directory.

Why this exists: `workon <venv>` alone only switches PATH to that venv's binaries - it
does not set DJANGO_SETTINGS_MODULE, PYTHONPATH, DB_*, SECRET_KEY, etc. Django needs all
of those just to import settings (celery's app building touches django.conf:settings),
so a bare `workon project; celery -A sportfac inspect active` fails with
"Module 'sportfac' has no attribute 'celery'" - not because the app is missing, but
because settings import blew up first and celery's loader reports that as a generic
attribute error.

This reads the exact `environment=`/`directory=`/`command=` supervisor already uses for
each "*_worker" program (from the real .conf files - one source of truth, no retyping
secrets into a second script) and runs celery with that.

Usage:
    python3 supervisor_celery_inspect.py /path/to/supervisor/conf.d/*.conf
    python3 supervisor_celery_inspect.py --conf-dir /path/to/supervisor/conf.d
"""
import argparse
import configparser
import glob
import os
import re
import shlex
import subprocess


def parse_environment(raw: str) -> dict:
    """Supervisor's `environment=KEY='val',KEY2="val2",...` format."""
    env = {}
    for key, val in re.findall(r"""([A-Za-z_][A-Za-z0-9_]*)=("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|[^,]*)""", raw):
        val = val.strip()
        if val[:1] in ("'", '"') and val[-1:] == val[:1]:
            val = val[1:-1]
        env[key] = val
    return env


def find_worker_sections(config):
    return [s for s in config.sections() if s.startswith("program:") and s.endswith("_worker")]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("conf_files", nargs="*", help="supervisor .conf files (globs your shell expands)")
    parser.add_argument("--conf-dir", help="directory to glob *.conf from instead")
    args = parser.parse_args()

    conf_files = list(args.conf_files)
    if args.conf_dir:
        conf_files += sorted(glob.glob(os.path.join(args.conf_dir, "*.conf")))
    if not conf_files:
        parser.error("no conf files given - pass paths/globs or --conf-dir")

    for path in conf_files:
        config = configparser.RawConfigParser()
        config.read(path)
        for section in find_worker_sections(config):
            name = section.split(":", 1)[1]
            print(f"\n{'#' * 60}\n{name}\n{'#' * 60}")

            raw_env = config.get(section, "environment", fallback="")
            env = {**os.environ, **parse_environment(raw_env)}
            directory = config.get(section, "directory", fallback=None)
            command = config.get(section, "command", fallback="")
            if not command:
                print(f"  (no command= found in [{section}], skipping)")
                continue
            celery_bin = shlex.split(command)[0]

            for sub in ("active", "reserved", "stats"):
                # celery's default inspect timeout is 1s - too tight in practice, "stats"
                # especially (it gathers more than active/reserved) can miss it even when
                # the worker is healthy and responds fine to a longer wait.
                subprocess.run(
                    [celery_bin, "-A", "sportfac", "inspect", sub, "--timeout", "10"], cwd=directory, env=env
                )


if __name__ == "__main__":
    main()
