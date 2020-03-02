
fields = {
    "SOURCE_ID": {
        "1": "DAA",
        "2": "WattFox",
        "3": "Senec",
        "OTHER": "other",
    },
    "UF_CRM_1576169522": {
        "": "nicht ausgewählt",
        "1042": "0%",
        "1044": "bis 5%",
        "1046": "bis 8%",
        "1048": "bis 10%",
        "1050": "bis 15%",
        "1052": "bis 20%",
        "1054": "manuell",
        "1056": "Sondervereinbarung",
        "1876": "keine Auswahl"
    },
    "UF_CRM_5DF8B0188EF78": {
        "": "nicht ausgewählt",
        "1540": "0%",
        "1542": "bis 5%",
        "1544": "bis 8%",
        "1546": "bis 10%",
        "1548": "bis 15%",
        "1550": "bis 20%",
        "1552": "manuell",
        "1554": "Sondervereinbarung",
        "1874": "keine Auswahl"
    },
    "UF_CRM_1576184116": {
        "": "nicht ausgewählt",
        "1512": "Nachlass wie im CRM beschrieben eingehalten",
        "1514": "über Nachlass hinaus verkauft",
        "1516": "kein zus. Auftrag generiert",
        "1866": "keine Auswahl"
    },
    "UF_CRM_1576184383": {
        "": "nicht ausgewählt",
        "1518": "Wärmepumpe (ecoStar) verkauft",
        "1520": "keine ecoStar verkauft",
        "1856": "keine Auswahl"
    },
    "UF_CRM_5DF8B018DA5E6": {
        "": "nicht ausgewählt",
        "1562": "Wärmepumpe (ecoStar) verkauft",
        "1564": "keine ecoStar verkauft",
        "1854": "keine Auswahl"
    },
    "UF_CRM_1576184446": {
        "": "nicht ausgewählt",
        "1522": "Barzahler",
        "1524": "Dresdner Bank",
        "1846": "keine Auswahl"
    },
    "UF_CRM_5DF8B018E971A": {
        "": "nicht ausgewählt",
        "1566": "Barzahler",
        "1568": "Dresdner Bank",
        "1844": "keine Auswahl"
    }
}


def convert_field_value_from_remote(field, data):
    if field in fields and data[field] in fields[field]:
        return fields[field][data[field]]
    return None


def convert_field_value_to_remote(field, data):
    if field in fields:
        inv_map = {v: k for k, v in fields[field].items()}
        if value in inv_map:
            return inv_map[data[field]]
    return None


def convert_field_euro_from_remote(field, data):
    if data[field] is None or data[field] == "":
        return 0
    value = str(data[field])
    if value.find("|") < 0:
        print("wrong format error: ", value)
        return 0
    return float(value[:value.find("|")])
