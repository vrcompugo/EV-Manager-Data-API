

def apply_filters(app):
    app.jinja_env.filters['dateformat'] = dateformat
    app.jinja_env.filters['datetimeformat'] = datetimeformat
    app.jinja_env.filters['numberformat'] = numberformat
    app.jinja_env.filters['currencyformat'] = currencyformat
    app.jinja_env.filters['percentformat'] = percentformat


def dateformat(value, format='%d.%m.%Y'):
    return value.strftime(format)


def datetimeformat(value, format='%d.%m.%Y %H:%M'):
    return value.strftime(format)


def numberformat(value, format='de', digits=2):
    baseformat = '{:.' + str(digits) + 'f}'
    if(format == "de"):
        return baseformat.format(float(value)).replace(",", "X").replace(".", ",").replace("X", ".")
    return str(value)


def currencyformat(value, format='de', digits=2):
    if value is None:
        return ""
    value = round(float(value), 2)
    return numberformat(value, format, digits=digits) + u"\N{euro sign}"


def percentformat(value, format='de', digits=0):
    value = float(value)
    return numberformat(value, format, digits=digits) + "%"
