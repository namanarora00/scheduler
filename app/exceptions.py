class ServiceException(Exception):
    """Base exception for service layer errors"""
    def __init__(self, message, error_code=None, status_code=400):
        self.message = message
        self.error_code = error_code or 'SERVICE_ERROR'
        self.status_code = status_code
        super().__init__(self.message)

    def __str__(self):
        return self.message

class AuthenticationError(ServiceException):
    """Raised when authentication fails"""
    def __init__(self, message="Authentication failed", error_code=None):
        super().__init__(
            message=message,
            error_code=error_code or 'AUTH_ERROR',
            status_code=401
        )

class AuthorizationError(ServiceException):
    """Raised when user doesn't have required permissions"""
    def __init__(self, message="Authorization failed", error_code=None):
        super().__init__(
            message=message,
            error_code=error_code or 'FORBIDDEN',
            status_code=403
        )

class ValidationError(ServiceException):
    """Raised when input validation fails"""
    def __init__(self, message="Validation failed", error_code=None):
        super().__init__(
            message=message,
            error_code=error_code or 'VALIDATION_ERROR',
            status_code=400
        )
    