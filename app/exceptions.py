
class ApiException(Exception):

    code = ""
    message = ""
    http_status = 500
    data = None

    def __init__(self, code, message, http_status, data=None) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        self.data = data
        super().__init__(message)


class NotFoundError(Exception):
    pass
