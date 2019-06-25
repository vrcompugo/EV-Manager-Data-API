
class ApiException(Exception):

    code = ""
    message = ""
    http_status = 500

    def __init__(self, code, message, http_status) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class NotFoundError(Exception):
    pass