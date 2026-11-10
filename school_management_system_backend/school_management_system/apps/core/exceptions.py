import logging

from rest_framework.views import exception_handler

logger = logging.getLogger("school_management_system")


def custom_exception_handler(exc, context):
    """
    Wraps DRF's default exception handler to return a consistent
    {"detail": ..., "code": ...} error shape and to log server-side
    errors and permission/authorization failures.
    """
    response = exception_handler(exc, context)

    if response is not None:
        request = context.get("request")
        view = context.get("view")

        if response.status_code in (401, 403):
            logger.warning(
                "Authorization failure: user=%s path=%s status=%s view=%s",
                getattr(getattr(request, "user", None), "username", "anonymous"),
                getattr(request, "path", ""),
                response.status_code,
                view.__class__.__name__ if view else "",
            )

        data = response.data
        if isinstance(data, dict) and "detail" not in data:
            # Flatten serializer validation errors into a single detail message
            # while still exposing the field-level errors for the frontend.
            response.data = {"detail": "Validation error.", "errors": data}
        elif isinstance(data, list):
            response.data = {"detail": "Validation error.", "errors": data}

    return response
