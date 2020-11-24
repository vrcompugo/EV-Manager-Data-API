def street_to_street_with_nb(street):
    if street is None:
        return "", ""
    last_space = street.rfind(" ")
    return street[:last_space].strip(), street[last_space:].strip()
