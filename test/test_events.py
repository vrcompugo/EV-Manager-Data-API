import os
import unittest

from flask import current_app
from flask_testing import TestCase

from manage import app, db
from app.modules.events.event_services import add_trigger, run_trigger, add_action


class TestEventCycle(TestCase):
    def create_app(self):
        return app

    def test_event_success(self):
        action  = add_action({
            "triggers": ["test_event","asd"],
            "action": "test",
            "config": {
                "result": "success"
            }
        })
        trigger = add_trigger({
            "name": "test_event",
            "data": {}
        })
        run_trigger(trigger)
        self.assertEqual(trigger.status == "done", True)
        db.session.delete(action)
        db.session.commit()

    def test_event_error(self):
        action  = add_action({
            "triggers": ["test_event","asd"],
            "action": "test",
            "config": {
                "result": "error"
            }
        })
        trigger = add_trigger({
            "name": "test_event",
            "data": {}
        })
        run_trigger(trigger)
        self.assertEqual(trigger.status == "error", True)
        db.session.delete(trigger)
        db.session.delete(action)
        db.session.commit()

    def test_event_lead_update(self):
        trigger = add_trigger({
            "name": "lead_updated",
            "data": {
                "lead_id": 241,
                "old_data":{
                    "status": "contacted"
                },
                "new_data":{
                    "status": "won"
                }
            }
        })
        run_trigger(trigger)
        self.assertEqual(trigger.status == "done", True)
        db.session.commit()

    def test_event_lead_export(self):
        trigger = add_trigger({
            "name": "lead_exported",
            "data": {
                "lead_id": 241,
                "operation": "add",
                "source": "nocrm.io"
            }
        })
        run_trigger(trigger)
        self.assertEqual(trigger.status == "done", True)
        db.session.commit()

if __name__ == '__main__':
    unittest.main()
