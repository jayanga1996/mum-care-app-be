"""
DRF exception handler: ensure JSON responses for API routes instead of Django HTML 500 pages.
"""
from __future__ import annotations

import logging
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
    1054: "Unknown column: run `python manage.py migrate`.",
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

    return Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
