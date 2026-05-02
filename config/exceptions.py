"""
DRF exception handler: ensure JSON responses for API routes instead of Django HTML 500 pages.
"""
import logging
import traceback

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


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

    return Response(body, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
