

def apply_filters(app):
    app.jinja_env.filters['textfilter'] = textfilter
    app.jinja_env.filters['boolformat'] = boolformat
    app.jinja_env.filters['dateformat'] = dateformat
    app.jinja_env.filters['datetimeformat'] = datetimeformat
    app.jinja_env.filters['numberformat'] = numberformat
    app.jinja_env.filters['currencyformat'] = currencyformat
    app.jinja_env.filters['percentformat'] = percentformat


def textfilter(value):
    if value is None:
        return ""
    return str(value)


def boolformat(value):
    if value is not None and value is True:
        return "Ja"
    return "Nein"


def dateformat(value, format='%d.%m.%Y'):
    if value is None:
        return ""
    return value.strftime(format)


def datetimeformat(value, format='%d.%m.%Y %H:%M'):
    return value.strftime(format)


def numberformat(value, format='de', digits=2):
    if value is None:
        return ""
    value = float(value)
    baseformat = '{:,.' + str(digits) + 'f}'
    if(format == "de"):
        return baseformat.format(float(value)).replace(",", "X").replace(".", ",").replace("X", ".")
    return str(value)


def currencyformat(value, format='de', digits=2):
    if value is None:
        return ""
    value = round(float(value), 2)
    return numberformat(value, format, digits=digits) + u" \N{euro sign}"


def percentformat(value, format='de', digits=0):
    return numberformat(value, format, digits=digits) + "%"
