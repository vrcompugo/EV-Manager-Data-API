from calendar import month
import json
from datetime import datetime, timedelta
from dateutil.parser import parse

from app import db

from app.modules.settings import get_settings, set_settings
from app.utils.error_handler import error_handler
from app.models import PowerMeter, PowerMeterMeasurement
from app.modules.external.smartme.powermeter_measurement import get_device_by_datetime as smart2_get_device_by_datetime

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


def get_device_by_datetime(smartme_number, datetime):
    device = get("/DeviceBySerial", parameters={ "serial": smartme_number})
    if device is None:
        data = smart2_get_device_by_datetime(smartme_number, datetime)
    else:
        data = get(f"/MeterValues/{device['Id']}", parameters={ "date": str(datetime) })
    if data is not None:
        requested_date = normalize_date(datetime)
        responded_date = normalize_date(data.get("Date"))
        if requested_date != responded_date:
            if responded_date <= requested_date:
                for i in range(10):
                    requested_date2 = requested_date + timedelta(days=i * 10)
                    if device is None:
                        data2 = smart2_get_device_by_datetime(smartme_number, requested_date2)
                    else:
                        data2 = get(f"/MeterValues/{device['Id']}", parameters={ "date": str(requested_date2) })
                    if data2 is not None:
                        responded_date2 = normalize_date(data2.get("Date"))
                        if responded_date2 > requested_date:
                            print(requested_date2, responded_date2)
                            kwh_diff = data2.get("CounterReading") - data.get("CounterReading")
                            days_diff = (responded_date2 - responded_date).days
                            days_to_add = (requested_date - responded_date).days
                            new_reading = data.get("CounterReading") + days_to_add * (kwh_diff / days_diff)
                            data["CounterReading"] = new_reading
                            data["Date"] = str(requested_date)
                            return data

                print(responded_date)
                print("---------")
    return data


def normalize_date(datetime):
    return parse(parse(datetime).strftime("%Y-%m-%d"))