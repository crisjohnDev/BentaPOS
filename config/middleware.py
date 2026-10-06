
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings


logger = logging.getLogger("django")


class ErrorHandlingMiddleware:
    """
    Global Django error-handling middleware.

    Catches unexpected exceptions, logs the full traceback,
    and returns a friendly 500 response.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        try:
            response = self.get_response(request)

            return response

        except Exception as exception:

            # Log complete traceback
            logger.exception(
                "Unhandled exception while processing %s %s",
                request.method,
                request.path,
            )

            # API request
            if request.path.startswith("/api/"):

                return JsonResponse(
                    {
                        "success": False,
                        "error": "Internal server error.",
                    },
                    status=500,
                )

            # Development mode
            if settings.DEBUG:

                raise exception

            # Production mode
            return render(
                request,
                "errors/500.html",
                status=500,
            )

    def process_exception(self, request, exception):

        logger.exception(
            "Unhandled exception in %s %s",
            request.method,
            request.path,
        )

        return None
