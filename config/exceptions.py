"""
DRF exception handler: ensure JSON responses for API routes instead of Django HTML 500 pages.
"""
from __future__ import annotations

import logging
import re
import traceback
from typing import Optional

from django.conf import settings
from django.db.utils import OperationalError as DjangoOperationalError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)

# MySQL / MariaDB errno → short fix hints (mysqlclient / PyMySQL use (code, message))
_MYSQL_DB_HINTS = {
    1045: "Login denied: fix DB_USER / DB_PASSWORD in .env and grant privileges on DB_NAME.",
    1049: "Unknown database: create the database or fix DB_NAME in .env.",
    2003: "Cannot connect to MySQL: check DB_HOST, DB_PORT, MySQL is running, and firewall/security groups allow this host.",
    2013: "Lost connection to MySQL server during query (timeout / server restart / proxy).",
    1146: "Table does not exist: run `python manage.py migrate` on this server.",
    1054: "Unknown column — schema out of date; see `unknown_column` in this response and follow `fix` if present.",
    1364: "Field doesn't have a default value: often fixed by running migrations.",
}


def _database_error_hint(exc: BaseException) -> Optional[str]:
    """Safe, generic hints for OperationalError (no secrets)."""
    if not isinstance(exc, DjangoOperationalError):
        return None
    args = getattr(exc, "args", ())
    if args and isinstance(args[0], int):
        code = args[0]
        if code in _MYSQL_DB_HINTS:
            return _MYSQL_DB_HINTS[code]
    msg = str(exc).lower()
    if "doesn't exist" in msg or "does not exist" in msg:
        return "Missing table or database object — run `python manage.py migrate` and ensure DB_NAME exists."
    if "access denied" in msg:
        return "MySQL rejected credentials — update DB_USER / DB_PASSWORD in .env."
    if "can't connect" in msg or "could not connect" in msg:
        return "Cannot reach MySQL — check DB_HOST, DB_PORT, and that mysqld is listening."
    return "Database error — verify MySQL is up and .env DB_* values match this environment."


def _parse_mysql_unknown_column(exc: BaseException) -> Optional[str]:
    """Extract bare column name from MySQL error text (errno 1054)."""
    text = str(exc)
    m = re.search(r"Unknown column\s+['`]([^'`]+)['`]", text, re.I)
    if not m:
        return None
    raw = m.group(1).strip()
    # May be `table.column` or `db`.`table`.`column`
    if "." in raw:
        return raw.split(".")[-1]
    return raw


def _fix_hint_for_unknown_column(column: str) -> Optional[str]:
    if column == "phm_area_id":
        return (
            "Pull latest backend, then run: python manage.py migrate "
            "(areas/0007 + 0008 add phm_area_id if it is missing). "
            "Alternative: python manage.py repair_midwife_phm_column"
        )
    return None


def api_exception_handler(exc, context):
    """
    Delegate to DRF first. For non-API exceptions (AttributeError, etc.), return JSON.
    Always include exc_type so production clients can report e.g. OperationalError vs ValueError.
    """
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    tb = traceback.format_exc()
    logger.error("Unhandled exception in API view\n%s", tb)

    exc_type = type(exc).__name__
    expose = getattr(settings, "DEBUG", False) or getattr(settings, "EXPOSE_API_ERRORS", False)

    if expose:
        detail = f"{exc_type}: {exc}"
    else:
        detail = "Internal server error."

    body = {"detail": detail, "exc_type": exc_type}
    if expose:
        body["exc_message"] = str(exc)

    hint = _database_error_hint(exc)
    if hint:
        body["hint"] = hint

    if isinstance(exc, DjangoOperationalError):
        uk = _parse_mysql_unknown_column(exc)
        if uk:
            body["unknown_column"] = uk
            fix = _fix_hint_for_unknown_column(uk)
            if fix:
                body["fix"] = fix

    return Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
