class AppError(Exception):
    status_code = 500

    def __init__(self, message: str, code: str = "error"):
        self.message = message
        self.code = code


class NotFoundError(AppError):
    status_code = 404

    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, "not_found")


class ConflictError(AppError):
    status_code = 409

    def __init__(self, message: str = "状态冲突"):
        super().__init__(message, "conflict")


class InvalidError(AppError):
    status_code = 422

    def __init__(self, message: str = "参数非法"):
        super().__init__(message, "invalid")
