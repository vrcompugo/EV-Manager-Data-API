import datetime
import os
import sys

from app import db
from flask import request
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.modules.auth import get_auth_info, get_logged_in_user
from app.exceptions import ApiException
from .models.settings import Settings


def get_full_section_name(section, domain_raw=None):

    domain_raw = "keso.bitrix24.de"
    return f"{domain_raw}/{section}"


def get_settings(section=None, domain_raw=None):
    full_section = get_full_section_name(section, domain_raw)
    settings_object = db.session.query(Settings).filter(Settings.section == full_section).first()
    if settings_object is not None:
        return settings_object.data
    if full_section == "keso.bitrix24.de/general":
        if os.getenv('ENVIRONMENT') == "dev":
            return {
                "base_url": "https://api.korbacher-energiezentrum.de.ah.hbbx.de/"
            }
        if os.getenv('ENVIRONMENT') == "staging":
            return {
                "base_url": "https://staging.api.korbacher-energiezentrum.de.ah.hbbx.de/"
            }
        return {
            "base_url": "https://api.korbacher-energiezentrum.de/"
        }
    if full_section == "keso.bitrix24.de/offer/datasheet_pdf":
        data = {
            "financing_file_id": 769,
            "senec_340wp": 435,
            "glas_glas": 445,
            "senec_v3": 437,
            "senec_guarantee": 441,
            "symo": 433,
            "nibe_wp": 1378554  # https://keso.bitrix24.de/disk/downloadFile/1378554/?&ncc=1&filename=Nibe+Brauchwasser+Wa%CC%88rmepumpe.pdf,
        }
        return data
    if full_section == "keso.bitrix24.de/offer/summary_pdf":
        data = {
            "backside_file_id": 493
        }
        return data
    if full_section == "keso.bitrix24.de/external/bitrix24":
        data = {
            "url": "https://keso.bitrix24.de/rest/106/v38b9iovomrydti2/",
            "taxrate": 19,
            "select_lists": {
                "transaction_code": {
                    "3040": "E01",
					"3042": "E02",
					"3044": "E03",
					"3046": "ZD2",
					"3048": "E14",
					"3050": "E24"
                },
                "heating_type": {
                },
                "salutation": {
                    "HNR_DE_2": "mr",
                    "HNR_DE_1": "ms"
                },
                "mfr_category": {
                    "": "default",
                    "3978": "electric",
                    "3980": "roof",
                    "3982": "heating",
                    "3984": "service",
                    "4044": "holiday",
                    "4042": "roof_reconstruction_pv",
                    "4040": "roof_reconstruction",
                    "4038": "service_storage_pb",
                    "4034": "service_storage_li",
                    "4030": "service_pv_storage_li",
                    "4018": "service_pv_storage_pb",
                    "4016": "storage_swap",
                    "4014": "repair_electric",
                    "4012": "additional_roof",
                    "4010": "solar_edge_change_test",
                    "4054": "enpal_mvt",
                    "4056": "enpal_verbau",
                    "4074": "additional_electric"
                },
                "cloud_type": {
                    "234": "Zero",
                    "2438": "eCloud",
                    "2440": "Wärmecloud",
                    "262": "Spezial",
                    "4154": "Consumer",
                    "3598": "keine Auswahl"
                },
                "quote_type": {
                    "": "nicht ausgewählt",
                    "3912": "Photovoltaik",
                    "3914": "Photovoltaik und Dachsanierung",
                    "3916": "Dachsanierung",
                    "3932": "keine Auswahl",
                },
                "quote_type2": {
                    "4366": "Cloud/PV",
                    "4368": "Dachsanierung",
                    "4370": "Heizung",
                    "4372": "BlueGen",
                },
                "quote_type3": {
                    "": "nicht ausgewählt",
                    "3918": "keine Auswahl",
                    "3920": "Heizung Öl",
                    "3922": "Heizung Gas",
                    "3924": "Heizung WP",
                    "3926": "Heizung BWWP",
                    "3928": "Heizung Sonstiges",
                },
                "storage_size": {
                    "154": "Senec 2,5 Li",
                    "156": "Senec 5.0 Li",
                    "158": "Senec 7,5 Li",
                    "160": "Senec 10.0 Li",
                    "164": "Senec 20.0 Li",
                    "1638": "keine Auswahl"
                },
                "inverter_type": {
                    "166": "WR im SENEC",
                    "168": "Solar Edge (Optimierer laut Auslegung)",
                    "238": "Fremdwechselrichter (Fronius bevorzugt) oder 10 Jahre Garantie WR",
                    "1910": "keine Auswahl"
                },
                "pv_module": {
                    "176": "400 Watt Amerisolar black",
                    "4100": "380 Watt Amerisolar Black",
                    "2484": "320 Watt Amerisolar black",
                    "178": "Triple Black Module",
                    "240": "Sondermodul",
                    "1906": "keine Auswahl",
                    "174": "400 Watt Amerisolar blau",
                    "170": "280 Watt Amerisolar"
                },
                "extra_packages": {
                    "180": "Technik & Service (Anschlussgarantie, Technikpaket, Portal)",
                    "182": "Technik & Service MAX (Anschl. Garantie/Technikpaket & SOBmax)",
                    "242": "Complete (Wartung und Versicherung für 1 Jahr inkl.)",
                    "184": "EEG All-in-One (Anschlussgarantie, Technikpaket, SOB, 24 Monate Versicherung)",
                    "2558": "AEV Paket (Anschlussgarantie, Technikpaket, 24 Monate Versicherung)",
                    "1696": "keine Auswahl"
                },
                "extra_packages2": {
                    "4168": "ENW (Brick)",
                    "5604": "Wallbox Heidelberger Home Eco (11KW)",
                    "5606": "Wallbox Heidelberger Energie Control (11KW)",
                    "5606": "Wallbox SENEC pro S (11kW)",
                    "5610": "Wallbox SENEC 22kW Pro",
                    "186": "Wallbox 11 kW (SENEC) mit Kabel",
                    "4374": "Wallbox 22 kW (SENEC) mit Kabel",
                    "4148": "Senec Wechselrichtergarantie 20 Jahre",
                    "198": "Zählerschrank",
                    "4218": "Wärme Cloud Paket (zusätzlicher Zählerplatz für Wärme)",
                    "2488": "Notstrombox",
                    "2492": "Steuerpaket 1",
                    "244": "keine Auswahl",
                    "188": "SOB Max 40",
                    "190": "SOB Max 100",
                    "192": "SOB Max 500",
                    "194": "SOB Max 1000",
                    "196": "SOB Cockpit"
                },
                "bwwp": {
                    "246": "keine Auswahl",
                    "4194": "Nibe 160",
                    "4196": "Nibe 210",
                    "200": "Taglio 100",
                    "202": "Taglio 180",
                    "204": "ecoStar WT",
                    "206": "ecoStar 2.2 (zzgl. Pufferspeicher)"
                },
                "hwp": {
                    "1698": "keine Auswahl",
                    "4206": "Nibe WP",
                    "4208": "Nibe Hybrid",
                    "4134": "Ja",
                    "208": "ecoStar 4.4",
                    "210": "Waterkotte bis 9 kW (Bestand)",
                    "212": "Waterkotte bis 14 kW (Bestand)",
                    "216": "Waterkotte bis 22 kW (Bestand)",
                    "214": "Waterkotte bis 42 kW (Bestand)",
                    "218": "Wärmepumpe bis 8,1 kW (Neubau bis 180 pm)",
                    "248": "Wärmepumpe bis 8,1 kW (Neubau bis 250 pm)",
                    "250": "Wärmepumpe laut Aufnahmebogen zusammenstellen",
                    "252": "Inbetriebnahme",
                    "254": "Demontage und Entsorgung alte Heizung",
                    "256": "hydraulischer Abgleich"
                },
                "emove_packet": {
					"": "nicht ausgewählt",
					"2428": "emove Tarif Hybrid",
					"2430": "emove.drive I",
					"2432": "emove.drive II",
					"2434": "emove.drive III",
					"2446": "emove.drive ALL",
					"2436": "none"
                },
                "solar_edge_guarantee_extend": {
                    "2528": "Ja",
                    "2530": "Nein"
                },
                "dz4_customer": {
                    "": "nicht ausgewählt",
                    "4320": "kein DZ-4 Kunde",
                    "4322": "Ja, wurde geändert"
                },
                "tax_consultant": {
                    "2516": "Ja",
                    "2518": "Nein",
                },
                "storage_model": {
                    "264": "Senec Home 2.1",
                    "266": "Senec Uno Hybrid",
                    "268": "Senec Duo Hybrid",
                    "3624": "Blei",
                    "272": "kein Speicher"
                },
                "has_emove_package": {
                    "": "nicht ausgewählt",
                    "4118": "Ja",
                    "4120": "Nein"
                },
                "is_negative_cloud": {
                    "": "nicht ausgewählt",
                    "3036": "Ja",
                    "3038": "Nein"
                },
                "heating_quote_house_type": {
                    "": "nicht ausgewählt",
                    "6194": "Einfamilienhaus",
                    "6196": "Mehrfamilienhaus",
                },
                "heating_quote_house_build": {
                    "": "nicht ausgewählt",
                    '6198': '1940-1969',
                    '6200': '1970-1979',
                    '6202': '1980-1999',
                    '6204': '2000-2015',
                    '6206': '2016 und neuer',
                    '6208': 'new_building',
                },
                "old_heating_type": {
                    "": "nicht ausgewählt",
                    "6210": "gas",
                    "6212": "oil",
                    "6214": "heatpump",
                    "6216": "pellez",
                    "6218": "electro",
                    "6220": "nightofen",
                    "6222": "other"
                },
                "heating_quote_old_heating_build": {
                    "": "nicht ausgewählt",
                    "6224": "2-6_years",
                    "6226": "7-12_years",
                    "6228": "older"
                },
                "new_heating_type": {
                    "": "nicht ausgewählt",
                    "6230": "gas",
                    "6232": "heatpump",
                    "6234": "hybrid_gas"
                },
                "heating_quote_radiator_type": {
                    "": "nicht ausgewählt",
                    "6236": "floor_heating",
                    "6238": "mixed",
                    "6240": "radiator_heating"
                },
                "heating_quote_warm_water_type": {
                    "": "nicht ausgewählt",
                    "6242": "heater",
                    "6244": "separate"
                },
                "heating_quote_circulation_pump": {
                    "": False,
                    "6246": True,
                    "6248": False
                }
            },
            "product": {
                "units": {
                    "None": "Stück",
                    "1": "Meter",
                    "3": "Liter",
                    "5": "Gramm",
                    "7": "Kilogramm",
                    "9": "Stück",
                    "10": "Monate á",
                    "12": "kWp",
                    "14": "kWh",
                    "16": "AW",
                    "18": "m²",
                    "20": "m³"
                },
                "categories": {
                    "": None,
                    "Elektrik": 266,
                    "Optionen PV Anlage": 262,
                    "Extra Pakete": 292,
                    "PV Module": 260,
                    "Stromspeicher": 264,
                    "Brauchwasserwärmepumpe": 150,
                    "Wärmepumpe": 282,
                    "Heizung - WP": 218,
                    "Heizung - Gas": 238,
                    "Heizung - Öl": 216,
                    "Heizung - Optionen für Heizung": 220,
                    "Heizung - Optionen für Heizung Gas/Öl": 220,
                    "Heizung - Optionen für Heizung online": 302,
                    "Heizung - Solarthermie": 240,
                    "Online - Heizung - WP": 354,
                    "Online - Heizung - Gas": 350,
                    "Online - Heizung - Öl": 352,
                    "Online - Heizung - Hybrid Gas": 380,
                    "Online - Heizung - Solarthermie": 366,
                    "Online - Heizung - Zubehör": 358,
                    "Online - Heizung - Extra Optionen": 356,
                    "Online - Heizung - Extra Optionen - Gas": 360,
                    "Online - Heizung - Extra Optionen - Öl": 362,
                    "Online - Heizung - Extra Optionen - WP": 364,
                    "Erneuerbare Energie - Dach": 194,
                    "Brennstoffzelle": 298,
                    "online WP (Neu)": 306,
                    "Texte": 304,
                    "Dachsanierung online Bogen": 290,
                    "Optionen Heizung online": 302,
                    "Solarthermie online": 300
                }
            },
            "task": {
                "fields": {
                    "mfr_id": "ufAuto422491195439",
                    "etermin_id": "ufAuto219922666303",
                    "mfr_appointments": "ufAuto343721853755",
                    "etermin_appointments": "ufAuto513701476131"
                },
                "leading_users": {
                    "onur.berber.e360@gmail.com": "410",
                    "bernd.buechsenschuetz.kez@gmail.com": "70",
                    "dieter.hartmann.kez@gmail.com": "72",
                    "heiko.burzlaff.kez@gmail.com": "76",
                    "jason.hardy.kez@gmail.com": "100",
                    "joudi.daher.kez@gmail.com": "68",
                    "liviu.vasile.kez@gmail.com": "74",
                    "marco.gentsch.kez@gmail.com": "56",
                    "kbez330@gmail.com": "90",
                    "maurice.dobes.kez@gmail.com": "96",
                    "becker@korbacher-energiezentrum.de": "320",
                    "nebras.aboumoghdeb.kez@gmail.com": "58",
                    "rafat.alkuferi.kez@gmail.com": "62",
                    "rene.schroeder.kez@gmail.com": "298",
                    "roesner@energie360.de": "408",
                    "ronny.pokutta.kez@gmail.com": "64",
                    "volker.boemeke.kez@gmail.com": "98",
                    "mario.scherbaum.e360@gmail.com": "412"
                }
            },
            "deal": {
                "fields": {
                    "mfr_service_object_id": "UF_CRM_1612190018299",
                    "unique_identifier": "UF_CRM_5FA43F983EBAB",
                    "drive_insurance_folder": "UF_CRM_1612521127848",
                    "drive_rental_contract_folder": "UF_CRM_1612534834920",
                    "drive_rental_documents_folder": "UF_CRM_1612534862483",
                    "drive_cloud_folder": "UF_CRM_1612535045945",
                    "mfr_category": "UF_CRM_1612967946042",
                    "service_appointment_notes": "UF_CRM_1573029988665",
                    "service_appointment_date": "UF_CRM_1594740636",
                    "service_appointment_startdate": "UF_CRM_1614935800",
                    "service_appointment_enddate": "UF_CRM_1614935821",
                    "etermin_id": "UF_CRM_1614177772351",
                    "upload_link_roof": "UF_CRM_1600762711357",
                    "upload_link_electric": "UF_CRM_1600762741782",
                    "upload_link_heating": "UF_CRM_1600762727113",
                    "upload_link_invoices": "UF_CRM_1600762755535",
                    "upload_link_contract": "UF_CRM_1600762796533",
                    "upload_link_firstcall": "UF_CRM_1618302925",
                    "upload_link_heatingcontract": "UF_CRM_60A60FF556B0C",
                    "folder_id_heatingcontract": "UF_CRM_1621504031",
                    "aev_reseller": "UF_CRM_1615824273",
                    "cloud_number": "UF_CRM_1596703818172",
                    "cloud_contract_number": "UF_CRM_1596704551167",
                    "is_cloud_consumer": "UF_CRM_1597755099494",
                    "is_cloud_ecloud": "UF_CRM_1610466268",
                    "is_cloud_heatcloud": "UF_CRM_1610466287",
                    "cloud_type": "UF_CRM_1573027328",
                    "cloud_delivery_start": "UF_CRM_1578322109",
                    "fakturia_data": "UF_CRM_1623743780",
                    "contract_number": "UF_CRM_1596704551167",
                    "fakturia_contract_number": "UF_CRM_1622107557802",
                    "cloud_delivery_begin": "UF_CRM_1578322109",
                    "is_cloud_master_deal": "UF_CRM_1623835472",
                    "iban": "UF_CRM_1582292567",
                    "bic": "UF_CRM_1582292579",
                    "bank": "UF_CRM_1607947258",
                    "lightcloud_usage": "UF_CRM_1597757913754",
                    "heatcloud_usage": "UF_CRM_1597757931782",
                    "ecloud_usage": "UF_CRM_1607944188",
                    "sepa_mandate_since": "UF_CRM_1625467644466",
                    "storage_size": "UF_CRM_1573026960",
                    "inverter_type": "UF_CRM_1573027006",
                    "pv_module": "UF_CRM_1573027042",
                    "extra_packages": "UF_CRM_1573027085",
                    "extra_packages2": "UF_CRM_1573027121",
                    "bwwp": "UF_CRM_1573027184",
                    "hwp": "UF_CRM_1573027213",
                    "first_call_notes": "UF_CRM_1573029988665",
                    "construction_date": "UF_CRM_1573047800",
                    "count_modules": "UF_CRM_1579521015",
                    "emove_packet": "UF_CRM_1594062176",
                    "solar_edge_guarantee_extend": "UF_CRM_1601045329",
                    "quote_type": "UF_CRM_1612352327",
                    "quote_type2": "UF_CRM_1628242113",
                    "quote_type3": "UF_CRM_1612353277",
                    "dz4_customer": "UF_CRM_1627486165",
                    "tax_consultant": "UF_CRM_1600782915",
                    "storage_model": "UF_CRM_1573029656",
                    "cloud_monthly_cost": "UF_CRM_1612265225",
                    "cloud_yearly_usage": "UF_CRM_1585822072",
                    "has_emove_package": "UF_CRM_1620741780",
                    "emove_usage_inhouse": "UF_CRM_1620741150",
                    "emove_usage_outside": "UF_CRM_1620740831",
                    "is_negative_cloud": "UF_CRM_1607944340",
                    "cloud_runtime": "UF_CRM_1597758014166",
                    "power_meter_number": "UF_CRM_1585821761",
                    "counter_main": "UF_CRM_1585821761",
                    "heatcloud_power_meter_number": "UF_CRM_1597757955687",
                    "old_power_meter_numbers": "UF_CRM_1637842516",
                    "counter_heatcloud": "UF_CRM_1597757955687",
                    "counter_ecloud": "UF_CRM_1611239704",
                    "service_contract_number": "UF_CRM_1629883807207",
                    "insurance_contract_number": "UF_CRM_1629884046755",
                    "activation_date": "UF_CRM_1578322311",
                    "pv_kwp": "UF_CRM_1578671105",
                    "automatic_checked": "UF_CRM_1627383418",
                    "cloud_street": "UF_CRM_5DD4F51D40C8D",
                    "cloud_street_nb": "UF_CRM_5DD4F51D4CA3E",
                    "cloud_city": "UF_CRM_5DD4F51D57898",
                    "cloud_zip": "UF_CRM_5DD4F51D603E2",
                    "malo_id": "UF_CRM_1632220041088",
                    "construction_date2": "UF_CRM_1585237939",
                    "smartme_number": "UF_CRM_1605610632",
                    "smartme_number_heatcloud": "UF_CRM_1605610662",
                    "contracting_version": "UF_CRM_1639388034",
                    "netprovider": "UF_CRM_1607947330",
                    "netprovider_code": "UF_CRM_1581074754",
                    "energie_delivery_code": "UF_CRM_1597138326",
                    "transaction_code": "UF_CRM_1607947140",
                    "cloud_monthly_price": "UF_CRM_1612265225",
                    "bankowner": "UF_CRM_1644838647",
                    "malo_lightcloud": "UF_CRM_1632220041088",
                    "malo_heatcloud": "UF_CRM_1644838543",
                    "malo_ecloud": "UF_CRM_1644838574",
                    "malo_consumer1": "UF_CRM_1644838588",
                    "malo_consumer2": "UF_CRM_1644838598",
                    "malo_consumer3": "UF_CRM_1644838617",
                    "annual_statement_link": "UF_CRM_1646239276",
                    "delivery_first_name": "UF_CRM_1607945707",
                    "delivery_last_name": "UF_CRM_1607945716",
                    "delivery_street": "UF_CRM_1607945727",
                    "delivery_street_nb": "UF_CRM_1607945744",
                    "delivery_zip": "UF_CRM_1607945768",
                    "delivery_city": "UF_CRM_1607945776",
                    "delivery_counter_number": "UF_CRM_1607945817",
                    "delivery_counter_number2": "UF_CRM_1652437906170",
                    "delivery_counter_number3": "UF_CRM_1652437944091",
                    "delivery_usage": "UF_CRM_1610459059",
                    "cloud_delivery_begin_1": "UF_CRM_1648804042",
                    "cloud_number_1": "UF_CRM_1648804148",
                    "cloud_delivery_begin_2": "UF_CRM_1648804065",
                    "cloud_number_2": "UF_CRM_1648804168",
                    "cloud_delivery_begin_3": "UF_CRM_1648804078",
                    "cloud_number_3": "UF_CRM_1648804184",
                    "heating_quote_house_type": "UF_CRM_1650893500",
                    "heating_quote_house_build": "UF_CRM_1650893590",
                    "old_heating_type": "UF_CRM_1650893668",
                    "heating_quote_old_heating_build": "UF_CRM_1650893723",
                    "new_heating_type": "UF_CRM_1650893816",
                    "heating_quote_usage_mixed": "UF_CRM_1650893974",
                    "heating_quote_usage_oil": "UF_CRM_1650893974",
                    "heating_quote_usage_gas": "UF_CRM_1652876602",
                    "heating_quote_usage_pellets": "UF_CRM_1652876630",
                    "heating_quote_sqm": "UF_CRM_1650894021",
                    "heating_quote_radiator_type": "UF_CRM_1650894088",
                    "heating_quote_warm_water_type": "UF_CRM_1650894323",
                    "heating_quote_circulation_pump": "UF_CRM_1650894404",
                    "heating_quote_radiator_count": "UF_CRM_1650894425",
                    "heating_quote_shower_count": "UF_CRM_1650894452",
                    "heating_quote_bathtub_count": "UF_CRM_1650894476",
                    "heating_quote_people": "UF_CRM_1650894495",
                    "pdf_heatpump_auto_generate_link": "UF_CRM_1651497860",
                    "contracting_heatpump_link": "UF_CRM_1652867226"
                }
            },
            "quote": {
                "units": {
                    "None": "Stück",
                    "6": "Meter",
                    "112": "Liter",
                    "163": "Gramm",
                    "166": "Kilogramm",
                    "796": "Stück",
                    "101": "Monate á",
                    "123": "kWp",
                    "124": "kWh",
                    "125": "AW",
                    "126": "m²",
                    "127": "m³"
                },
                "fields": {
                    "unique_identifier": "UF_CRM_1607078985",
                    "history_id": "UF_CRM_1607079008",
                    "pdf_link": "UF_CRM_1607079246",
                    "quote_number": "UF_CRM_1607085112",
                    "special_conditions": "TERMS",
                    "expected_construction_week": "UF_CRM_1607444032"
                }
            },
            "lead": {
                "fields": {
                    "unique_identifier": "UF_CRM_1603895163",
                    "pdf_datasheets_link": "UF_CRM_1603981997",
                    "pdf_summary_link": "UF_CRM_1603982021",
                    "pdf_quote_summary_link": "UF_CRM_1603982035",
                    "pdf_contract_summary_link": "UF_CRM_1603982051",
                    "pdf_heatpump_auto_generate_link": "UF_CRM_1651676940",
                    "upload_link_roof": "UF_CRM_1603982144",
                    "upload_link_electric": "UF_CRM_1603982169",
                    "upload_link_heating": "UF_CRM_1603982160",
                    "upload_link_invoices": "UF_CRM_1603982179",
                    "upload_link_contract": "UF_CRM_1603982205",
                    "upload_link_firstcall": "UF_CRM_1618302626914",
                    "upload_link_heatingcontract": "UF_CRM_1621495505",
                    "salutation": "HONORIFIC",
                    "first_name": "NAME",
                    "street": "UF_CRM_5DD4020221169",
                    "street_nb": "UF_CRM_5DD402022E300",
                    "zip": "UF_CRM_5DD4020242167",
                    "city": "UF_CRM_5DD4020239456",
                    "aev_reseller": "UF_CRM_1615824261",
                    "collection_url": "UF_CRM_1620134803",
                    "zoom_appointment": "UF_CRM_1604498002",
                    "zoom_link": "UF_CRM_ZOOM_MEET_LINK",
                    "pv_quote_sum_net": "UF_CRM_1576184005",
                    "heating_quote_sum_net": "UF_CRM_1594627322",
                    "bluegen_quote_sum_net": "UF_CRM_1623241899",
                    "roof_reconstruction_quote_sum_net": "UF_CRM_1623241922",
                    "pv_kwp": "UF_CRM_1623246805",
                    "automatic_checked": "UF_CRM_1627383502",
                    "info_roof": "UF_CRM_1627383573",
                    "info_electric": "UF_CRM_1627383557",
                    "info_heating": "UF_CRM_1627383545",
                    "construction_week": "UF_CRM_1627383698",
                    "construction_year": "UF_CRM_1627384966",
                    "order_confirmation_date": "UF_CRM_1627383773",
                    "order_sign_date": "UF_CRM_1633684390348",
                    "contracting_version": "UF_CRM_1639388043",
                    "heatpump_survey_link": "UF_CRM_1651676940",
                    "interested_in": "UF_CRM_1652363669",
                    "comment": "UF_CRM_1652706710",
                    "contracting_heatpump_link": "UF_CRM_1652867586"
                }
            },
            "company": {
                "fields": {
                    "street": "UF_CRM_5DE18F4023B26",
                    "street_nb": "UF_CRM_5DE18F402C2CC",
                    "zip": "UF_CRM_5DE18F403BE8A",
                    "city": "UF_CRM_5DE18F4033826",
                    "mfr_id": "UF_CRM_1611663098516",
                    "mfr_service_object_id": "UF_CRM_1612189949145"
                }
            },
            "contact": {
                "fields": {
                    "salutation": "HONORIFIC",
                    "first_name": "NAME",
                    "street": "UF_CRM_1572950758",
                    "street_nb": "UF_CRM_1572950777",
                    "zip": "UF_CRM_1572963458",
                    "city": "UF_CRM_1572963448",
                    "fakturia_number": "UF_CRM_1611055654633",
                    "mfr_id": "UF_CRM_1611663069960",
                    "mfr_service_object_id": "UF_CRM_1612189860475",
                    "drive_myportal_folder": "UF_CRM_1612518385676",
                    "drive_abnahmen_folder": "UF_CRM_1612533349639",
                    "drive_internal_folder": "UF_CRM_1612533369175",
                    "drive_service_protocol_folder": "UF_CRM_1612533388171",
                    "drive_order_confirmation_folder": "UF_CRM_1612533409927",
                    "drive_orgamax_folder": "UF_CRM_1612533423669",
                    "drive_insurance_folder": "UF_CRM_1612533445604",
                    "drive_remote_care_folder": "UF_CRM_1612533596622",
                    "drive_rental_contract_folder": "UF_CRM_1612533461553",
                    "drive_rental_documents_folder": "UF_CRM_1612533480143",
                    "drive_cloud_folder": "UF_CRM_1612533500465",
                    "fakturia_iban": "UF_CRM_1624003459",
                    "fakturia_bic": "UF_CRM_1624003474",
                    "fakturia_owner": "UF_CRM_1624003488",
                    "sepa_mandate_since": "UF_CRM_1629210645",
                    "important_note": "UF_CRM_1573021516"
                }
            },
            "timeline_comment": {
                "fields": {
                }
            }
        }
        return data
    return {}


def set_settings(section, data, domain_raw=None):
    full_section = get_full_section_name(section, domain_raw)
    settings_object = db.session.query(Settings).filter(Settings.section == full_section).first()
    if settings_object is None:
        raise ApiException("settings not found", "Einstellungen wurden nicht gefunden", 500)
    settings_object.data = data
    db.session.commit()
    return settings_object.data


def add_item(data):
    item = db.session.query(Settings).filter(Settings.section == data["section"]).first()
    if item is not None:
        return None
    new_item = Settings()
    new_item = set_attr_by_dict(new_item, data, ["id"])
    db.session.add(new_item)
    db.session.commit()
    return new_item


def update_item(section, data):
    item = db.session.query(Settings).filter(Settings.section == section).first()
    if item is not None:
        updated_item = set_attr_by_dict(item, data, ["id"])
        db.session.commit()
        return updated_item


def import_test_data():
    pass
