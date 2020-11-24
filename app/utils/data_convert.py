def street_to_street_with_nb(street):
    if street is None:
        return "", ""
    last_space = street.rfind(" ")
    return street[:last_space].strip(), street[last_space:].strip()


def internationalize_phonenumber(phonenumber):
    if phonenumber is None or phonenumber == "":
        return ""
    if phonenumber[:2] == "00":
        return phonenumber
    if phonenumber[:1] == "+":
        return "00" + phonenumber[1:]
    if phonenumber[:1] == "0":
        return "0049" + phonenumber[1:]
    return phonenumber
