import json
from datetime import datetime

from app import db

from app.modules.settings import get_settings, set_settings
from app.utils.error_handler import error_handler
from app.models import PowerMeter, PowerMeterMeasurement

from ._connector import get


def run_cron_import():
    config = get_settings("external/smartme2")
    print("import values smartme2")
    if config is None:
        print("no config for smartme2 import")
        return None
    now = datetime.now()
    if "last_import_datetime" in config:
        last_import = datetime.strptime(config["last_import_datetime"], "%Y-%m-%d %H:%M:%S.%f")
        if last_import.month == now.month:
            return
    last_import_datetime = now
    devices = get("/Devices")
    if len(devices) > 0:
        for device in devices:
            print(device["Name"])
            power_meter = PowerMeter.query.filter(PowerMeter.number == str(device["Serial"])).first()
            if power_meter is None:
                power_meter = PowerMeter(
                    label=device["Name"],
                    number=str(device["Serial"]),
                    device_energy_type=device["DeviceEnergyType"],
                    family_type=device["FamilyType"]
                )
                db.session.add(power_meter)
                db.session.commit()
            power_meter_measurement = PowerMeterMeasurement(
                power_meter_id=power_meter.id,
                datetime=device["ValueDate"],
                value=device["CounterReading"],
                raw=device
            )
            db.session.add(power_meter_measurement)
            db.session.commit()

        config = get_settings("external/smartme2")
        if config is not None:
            config["last_import_datetime"] = str(last_import_datetime)
        set_settings("external/smartme2", config)