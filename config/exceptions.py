"""
DRF exception handler: ensure JSON responses for API routes instead of Django HTML 500 pages.
"""
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    """
    Delegate to DRF first. For non-API exceptions (AttributeError, etc.), return JSON.
    """
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    logger.exception("Unhandled exception in API view")

    if settings.DEBUG:
        detail = f"{type(exc).__name__}: {exc}"
    else:
        detail = "Internal server error."

    return Response({"detail": detail}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
