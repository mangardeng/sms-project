class AuditLogMiddleware:
    """
    Records 401/403 responses on API endpoints to the AuditLog table.
    This gives a persistent, queryable record of unauthorized access
    attempts (e.g. a parent trying to view a student they are not
    linked to, or a teacher trying to grade a class outside their
    assignment) as required by the security design (see 3.15 / 4.15).
    """

    SENSITIVE_PREFIX = "/api/"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.path.startswith(self.SENSITIVE_PREFIX) and response.status_code in (401, 403):
            # Imported lazily to avoid touching the DB / app registry at import time.
            from apps.core.models import log_action

            log_action(
                user=getattr(request, "user", None),
                action="access_denied",
                description=f"{response.status_code} response",
                ip_address=self._get_client_ip(request),
                path=request.path,
                method=request.method,
            )

        return response

    @staticmethod
    def _get_client_ip(request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
