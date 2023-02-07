from calendar import month
import json
from datetime import datetime, timedelta
from dateutil.parser import parse

from app import db

from app.modules.settings import get_settings, set_settings
from app.utils.error_handler import error_handler
from app.models import PowerMeter, PowerMeterMeasurement

from ._connector import get


def run_cron_import():
    config = get_settings("external/smartme")
    print("import values smartme")
    if config is None:
        print("no config for smartme import")
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
            if "CounterReading" not in device:
                print("error counter reading")
                print(json.dumps(device, indent=2))
                continue
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

        config = get_settings("external/smartme")
        if config is not None:
            config["last_import_datetime"] = str(last_import_datetime)
        set_settings("external/smartme", config)


def get_device_by_datetime(smartme_number, datetime_item):
    account = None
    device = get("/DeviceBySerial", parameters={ "serial": smartme_number})
    if device is None or device.get("Id") in [None, "", 0]:
        account = "2"
        device = get("/DeviceBySerial", parameters={ "serial": smartme_number}, account=account)
    if device is None or device.get("Id") in [None, "", 0]:
        account = "3"
        device = get("/DeviceBySerial", parameters={ "serial": smartme_number}, account=account)
    if device is None or device.get("Id") in [None, "", 0]:
        account = "4"
        device = get("/DeviceBySerial", parameters={ "serial": smartme_number}, account=account)
    if device is None or device.get("Id") in [None, "", 0]:
        return None
    print(account)
    data = get(f"/MeterValues/{device['Id']}", parameters={ "date": str(datetime_item) }, account=account)
    if data is not None:
        requested_date = normalize_date(datetime_item)
        responded_date = normalize_date(data.get("Date"))
        if requested_date != responded_date:
            if responded_date <= requested_date:
                for i in range(10):
                    requested_date2 = requested_date + timedelta(days=i * 10)
                    data2 = get(f"/MeterValues/{device['Id']}", parameters={ "date": str(requested_date2) }, account=account)
                    if data2 is not None:
                        responded_date2 = normalize_date(data2.get("Date"))
                        if responded_date2 > requested_date:
                            if normalize_date(data.get("Date")) < datetime(2002,1,1):
                                print("prop2",data2)
                                return data2
                            kwh_diff = data2.get("CounterReading") - data.get("CounterReading", 0)
                            days_diff = (responded_date2 - responded_date).days
                            days_to_add = (requested_date - responded_date).days
                            new_reading = data.get("CounterReading", 0) + days_to_add * (kwh_diff / days_diff)
                            data["CounterReading"] = new_reading
                            data["Date"] = str(requested_date)
                            return data
        if normalize_date(data.get("Date")) < datetime(2002,1,1):
            print("problem", data.get("Date"))
            return data
    return data


def normalize_date(value):
    if isinstance(value, datetime):
        return parse(value.strftime("%Y-%m-%d"))
    return parse(parse(value).strftime("%Y-%m-%d"))