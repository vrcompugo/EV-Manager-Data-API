from datetime import datetime
from flask import Markup


def apply_filters(app):
    app.jinja_env.filters['nltobr'] = nltobr
    app.jinja_env.filters['textfilter'] = textfilter
    app.jinja_env.filters['boolformat'] = boolformat
    app.jinja_env.filters['dateformat'] = dateformat
    app.jinja_env.filters['datetimeformat'] = datetimeformat
    app.jinja_env.filters['addressblock'] = addressblock
    app.jinja_env.filters['addressblock2'] = addressblock2
    app.jinja_env.filters['numberformat'] = numberformat
    app.jinja_env.filters['currencyformat'] = currencyformat
    app.jinja_env.filters['percentformat'] = percentformat
    app.jinja_env.filters['nl2br'] = nl2br


def nl2br(value):
    return textfilter(value).replace("\n", "<br>\n")


def textfilter(value):
    if value is None:
        return ""
    return str(value)


def boolformat(value):
    if value is not None and value is True:
        return "Ja"
    return "Nein"


def dateformat(value, format='%d.%m.%Y'):
    if value is None or value == "":
        return ""
    if type(value) == str:
        value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
    return value.strftime(format)


def datetimeformat(value, format='%d.%m.%Y %H:%M'):
    if value is None or value == "":
        return ""
    if type(value) == str:
        value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
    return value.strftime(format)


def numberformat(value, format='de', digits=2):
    if value is None:
        return ""
    value = float(value)
    if digits is None:
        if round(value) == value:
            return str(round(value)).replace(",", "X").replace(".", ",").replace("X", ".")
        return str(value).replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        baseformat = '{:,.' + str(digits) + 'f}'
    if(format == "de"):
        return baseformat.format(value).replace(",", "X").replace(".", ",").replace("X", ".")
    return str(value)


def currencyformat(value, format='de', digits=2):
    if value is None:
        return ""
    value = round(float(value), 2)
    return numberformat(value, format, digits=digits) + u" \N{euro sign}"


def percentformat(value, format='de', digits=0):
    return numberformat(value, format, digits=digits) + "%"


def addressblock2(address):
    text = ""
    if address["company"] is not None and address["company"] != "":
        text = text + address["company"] + "\n"
    if address["lastname"] is not None and address["lastname"] != "":
        text = text + f"{address['firstname']} {address['lastname']}\n"
    text = text + f"{address['street']} {address['street_nb']}\n"
    text = text + f"{address['zip']} {address['city']}\n"
    return text


def addressblock(address):
    text = ""
    if address.company is not None and address.company != "":
        text = text + address.company + "\n"
    if address.lastname is not None and address.lastname != "":
        text = text + f"{address.firstname} {address.lastname}\n"
    text = text + f"{address.street} {address.street_nb}\n"
    text = text + f"{address.zip} {address.city}\n"
    return text


def nltobr(text):
    if text is None:
        return ""
    return Markup(text.replace("\n", "<br>\n"))
