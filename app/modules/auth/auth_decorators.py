from .auth_services import *

full_permission_list = []


class token_required(object):

    permission = None

    def __init__(self, permission = None):
        self.permission = permission
        full_permission_list.append(permission)

    def __call__(self, f):
        def decorated(*args, **kwargs):
            logged_in_user = get_logged_in_user(request)
            if logged_in_user is not None:
                if self.permission is None or \
                        self.permission in logged_in_user["permissions"] or \
                        "all" in logged_in_user["permissions"]:
                    return f(*args, **kwargs)
                raise ApiException("invalid_permission", "Invalid Permission.", 401)
            raise ApiException("invalid_token", "Invalid Token. Please log in again.", 401)

        return decorated
