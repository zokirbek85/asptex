from typing import Any


class AppException(Exception):
    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, "NOT_AUTHENTICATED")


class PermissionDeniedError(AppException):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, "PERMISSION_DENIED")


class NotFoundError(AppException):
    def __init__(self, resource: str, identifier: Any = None):
        msg = f"{resource} not found"
        if identifier is not None:
            msg += f": {identifier}"
        super().__init__(msg, "NOT_FOUND")
        self.resource = resource


class AlreadyExistsError(AppException):
    def __init__(self, resource: str, field: str | None = None):
        msg = f"{resource} already exists"
        super().__init__(msg, "ALREADY_EXISTS")
        self.field = field


class BusinessRuleViolationError(AppException):
    def __init__(self, message: str, code: str = "BUSINESS_RULE_VIOLATION"):
        super().__init__(message, code)


class NegativeStockBlockedError(BusinessRuleViolationError):
    def __init__(self, lot_number: str | None = None, owner_name: str | None = None):
        if lot_number and owner_name:
            msg = f"Insufficient stock: lot {lot_number}, owner {owner_name} would go negative"
        else:
            msg = "Operation would cause negative stock at owner level"
        super().__init__(msg, "NEGATIVE_STOCK_BLOCKED")


class LotClosedError(BusinessRuleViolationError):
    def __init__(self, lot_number: str):
        super().__init__(
            f"Lot {lot_number} is closed/blocked — movements are not allowed",
            "LOT_CLOSED",
        )


class PreviousDayNotClosedError(BusinessRuleViolationError):
    def __init__(self, date: str):
        super().__init__(
            f"Previous day ({date}) must be closed before opening a new report",
            "PREVIOUS_DAY_NOT_CLOSED",
        )


class ReportNotEditableError(BusinessRuleViolationError):
    def __init__(self, status: str):
        super().__init__(
            f"Report cannot be edited in status: {status}",
            "REPORT_NOT_EDITABLE",
        )
