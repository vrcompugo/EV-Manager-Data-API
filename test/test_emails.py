import os
import unittest

from flask import current_app
from flask_testing import TestCase

from manage import app
from app.modules.lead.models import Lead
from app.modules.lead.lead_services import send_welcome_email
from app import db


class TestApiException(TestCase):
    def create_app(self):
        return app

    def test_lead_welcome_email(self):
        lead = db.session.query(Lead).get(241)
        result = send_welcome_email(lead)
        self.assertEqual(result, True)


if __name__ == '__main__':
    unittest.main()
