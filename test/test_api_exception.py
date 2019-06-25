import os
import unittest

from flask import current_app
from flask_testing import TestCase

from manage import app
from app.exceptions import ApiException
from app.decorators import api_response


def test_service(case):
    if case == "unkown":
        raise Exception("not found")
    if case == "not found":
        raise ApiException("not_found", "item not found", 400)
    if case == "not found":
        raise ApiException("not_found", "item not found", 400)
    return True

@api_response
def test_route(case):
    test_service(case)
    return {"status": "success", "message": "OK"}, 200

class TestApiException(TestCase):
    def create_app(self):
        return app

    def test_ok(self):
        response, status_code = test_route("ok")
        self.assertEqual(status_code, 200)
        self.assertEqual(response["status"], "success")

    def test_unkown(self):
        response, status_code = test_route("unkown")
        self.assertEqual(status_code, 500)
        self.assertEqual(response["status"], "error")

    def test_not_found(self):
        response, status_code = test_route("not found")
        self.assertEqual(status_code, 400)
        self.assertEqual(response["code"], "not_found")
        self.assertEqual(response["status"], "error")


if __name__ == '__main__':
    unittest.main()
