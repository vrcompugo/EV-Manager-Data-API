import os
import unittest

from flask import current_app
from flask_testing import TestCase

from manage import app
from app.modules.lead.models import Lead
from app.modules.lead.lead_services import lead_reseller_auto_assignment
from app import db


class TestApiException(TestCase):
    def create_app(self):
        return app

    def test_lead_reseller_auto_assignment(self):
        lead = db.session.query(Lead).get(3101)
        result = lead_reseller_auto_assignment(lead)
        self.assertEqual(result.reseller_id, 1)


if __name__ == '__main__':
    unittest.main()
