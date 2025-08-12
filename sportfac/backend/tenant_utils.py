# tenants/services.py
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from tempfile import NamedTemporaryFile

from django.core.management import call_command
from django.db import connection

from activities.models import Course
from registrations.models import Child

from .models import YearTenant


# ---- Constants (avoid magic strings) -----------------------------------------
SCHOOLS_APP_LABEL = "schools"
CHILD_MODEL_LABEL = "registrations.Child"
ACTIVITIES_APP_LABEL = "activities"
PAYROLL_FUNCTION_MODEL_LABEL = "payroll.Function"


@contextmanager
def using_tenant(tenant: YearTenant):
    """
    Temporarily switch the DB connection to a given tenant, then restore it.

    Args:
        tenant: Target YearTenant to activate for the duration of the context.
    """
    previous = getattr(connection, "tenant", None)
    if previous is None:
        connection.set_schema_to_public()
    connection.set_tenant(tenant)
    try:
        yield
    finally:
        if previous is None:
            connection.set_schema_to_public()
        else:
            connection.set_tenant(previous)


def _dump_labels_to_tempfile(labels) -> str:
    """
    Dump one or more app/model labels to a temporary JSON file.

    Args:
        labels: Django dumpdata labels (e.g. ["app"], ["app.Model"]).

    Returns:
        Absolute path to the created temporary JSON file.
    """
    tmp = NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    call_command("dumpdata", *labels, output=tmp.name)
    return tmp.name


def _load_fixture(filepath: str) -> None:
    """
    Load a Django JSON fixture file.

    Args:
        filepath: Absolute path to the JSON file created by dumpdata.
    """
    call_command("loaddata", filepath)


def copy_labels(
    labels: list[str],
    source: YearTenant,
    destination: YearTenant,
    logger=None,
) -> None:
    """
    Copy DB rows for the given labels from source tenant to destination.

    Args:
        labels: List of app/model labels to copy.
        source: Source tenant.
        destination: Destination tenant.
        logger: Optional logger.
    """
    log = logger or logging.getLogger(__name__)
    with using_tenant(source):
        path = _dump_labels_to_tempfile(labels)
        log.debug("Dumped %s from %s to %s", labels, source.schema_name, path)
    try:
        with using_tenant(destination):
            _load_fixture(path)
            log.debug("Loaded %s into %s", labels, destination.schema_name)
    finally:
        try:
            os.remove(path)
        except OSError:
            log.warning("Could not remove temp file: %s", path)


def copy_children(
    source: YearTenant,
    destination: YearTenant,
    *,
    set_status_imported: bool = True,
    logger=None,
) -> None:
    """
    Copy schools and children from source to destination; mark imported if desired.

    Args:
        source: Source tenant.
        destination: Destination tenant.
        set_status_imported: If True, set Child.status to STATUS.imported after copy.
        logger: Optional logger.
    """
    log = logger or logging.getLogger(__name__)
    copy_labels([SCHOOLS_APP_LABEL], source, destination, log)
    copy_labels([CHILD_MODEL_LABEL], source, destination, log)

    if set_status_imported:
        with using_tenant(destination):
            Child.objects.all().update(status=Child.STATUS.imported)
            log.debug("Marked all children as imported in %s", destination.schema_name)


def copy_activities(
    source: YearTenant,
    destination: YearTenant,
    *,
    reset_course_counters: bool = True,
    logger=None,
) -> None:
    """
    Copy activities from source to destination; reset derived counters if desired.

    Args:
        source: Source tenant.
        destination: Destination tenant.
        reset_course_counters: If True, set courses to uptodate=False and nb_participants=0.
        logger: Optional logger.
    """
    log = logger or logging.getLogger(__name__)
    copy_labels([ACTIVITIES_APP_LABEL], source, destination, log)

    if reset_course_counters:
        with using_tenant(destination):
            Course.objects.all().update(uptodate=False, nb_participants=0)
            log.debug("Reset course counters in %s", destination.schema_name)


def copy_payroll_functions(
    source: YearTenant,
    destination: YearTenant,
    logger=None,
) -> None:
    """
    Copy payroll functions from source to destination.

    Args:
        source: Source tenant.
        destination: Destination tenant.
        logger: Optional logger.
    """
    log = logger or logging.getLogger(__name__)
    copy_labels([PAYROLL_FUNCTION_MODEL_LABEL], source, destination, log)
