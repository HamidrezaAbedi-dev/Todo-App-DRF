from rest_framework.exceptions import APIException

class CustomValidationException(APIException):
    """
    Return API errors in a consistent response format.
    """

    status_code = 400
    default_code = "invalid_request"

    def __init__(self, code, message, details=None):
        error = {
            "code": code,
            "message": message,
        }

        if details is not None:
            error["details"] = details

        super().__init__({
            "success": False,
            "error": error,
        })