

def import_test_data():
    import random
    from sqlalchemy import or_
    from app import db
    from .services.customer_services import add_item
    from .models import Customer
    from barnum import gen_data

    salutations = ["Ms", "Mr"]
    titles = ["", "", "", "", "", "", "Dr."]

    for n in range(1000):
        gender = random.randint(0, 1)
        name = gen_data.create_name(full_name=True, gender="Male" if gender == 1 else "Female")
        title = random.choice(titles)
        city = gen_data.create_city_state_zip()
        customer = 1
        while customer is not None:
            customer_number = "K{}".format(random.randint(100000, 999999))
            lead_number = random.randint(100000, 999999)
            customer = db.session.query(Customer).filter(or_(
                Customer.customer_number == customer_number,
                Customer.lead_number == str(lead_number),
            )).first()

        add_item({
            "customer_number": customer_number,
            "lead_number": lead_number,
            "company": gen_data.create_company_name(),
            "salutation": salutations[gender],
            "title": title,
            "firstname": name[0],
            "lastname":  name[1],
            "email": gen_data.create_email(),
            "default_address": {
                "company": None,
                "salutation": salutations[gender],
                "title": title,
                "firstname": name[0],
                "lastname":  name[1],
                "street": gen_data.create_street(),
                "street_nb":"",
                "street_extra":None,
                "zip": city[2],
                "city": city[0]
            },
            "default_payment_account": {
                "type": "bankaccount",
                "data": {
                    "iban": "DE{}".format(random.randint(10000000000000000000, 99999999999999999999)),
                    "bank": gen_data.create_company_name(),
                    "bic": gen_data.create_pw(6, 0, 6, 0)
                }
            }
        })