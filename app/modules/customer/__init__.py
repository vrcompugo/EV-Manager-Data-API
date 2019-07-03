from .services.customer_services import add_item


def import_test_data():
    add_item({"customer_number": "4210986771", "lead_number": "1680004417", "company": None, "salutation": "Ms", "title": "Dr",
        "firstname": "Lonnard", "lastname": "Christer", "email": "lchrister0@facebook.com",
        "default_address": {"company": None, "salutation": "Ms", "title": "Dr","firstname": "Lonnard", "lastname": "Christer", 
                            "street":"Monument","street_nb":"6","street_extra":None,"zip":"77185","city":"Yushugou"},
        "default_payment_account": {
            "type": "bankaccount",
            "data": {"iban":"DE11331442208766320806","bank":"Natural Gas Distribution","bic":"XLHSKPYO"}
        }
    })
    add_item({"customer_number": "8881865254", "lead_number": "4228472052", "company": None, "salutation": "Mr", "title": "",
     "firstname": "Way", "lastname": "Carcas", "email": "wcarcas1@npr.org",
        "default_address": {"company": None, "salutation": "Mr", "title": "", "firstname": "Way", "lastname": "Carcas", 
                            "street":"Esker","street_nb":"991","street_extra":None,"zip":"39903","city":"Pingtan"},
        "default_payment_account": {
            "type": "bankaccount",
            "data": {"iban":"DE77672872374771042077","bank":"Metal Fabrications","bic":"KYNDBMKY"}
        }
    })
    add_item({"customer_number": "6726196830", "lead_number": "1625010680", "company": None, "salutation": "Mr", "title": "",
     "firstname": "Blaine", "lastname": "Arbuckel", "email": "barbuckel2@angelfire.com",
        "default_address": {"company": None, "salutation": "Mr", "title": "", "firstname": "Blaine", "lastname": "Arbuckel", 
                            "street":"Esker","street_nb":"49","street_extra":"Road","zip":"43388","city":"Tingzhou"},
        "default_payment_account": {
            "type": "bankaccount",
            "data": {"iban":"DE32723251150874210543","bank":"Banks","bic":"RCDFZIXQ"}
        }
    })
    add_item({"customer_number": "2171244003", "lead_number": "8256941782", "company": "Photobug", "salutation": "Ms",
     "title": "", "firstname": "Harbert", "lastname": "Borsnall", "email": "hborsnall3@bbb.org",
        "default_address": {"company": "Photobug", "salutation": "Ms", "title": "", "firstname": "Harbert", "lastname": "Borsnall", 
                            "street":"Derek","street_nb":"1","street_extra":None,"zip":"26100","city":"El Corozal"},
        "default_payment_account": {
            "type": "bankaccount",
            "data": {"iban":"DE09643521297002916543","bank":"Medical/Dental Instruments","bic":"YNYVOEMB"}
        }
    })
    add_item({"customer_number": "4751047442", "lead_number": "3125092426", "company": None, "salutation": "Ms", "title": "",
     "firstname": "Randell", "lastname": "Aleixo", "email": "raleixo4@home.pl",
        "default_address": {"company": None, "salutation": "Ms", "title": "", "firstname": "Randell", "lastname": "Aleixo", 
                            "street":"Buena Vista","street_nb":"5","street_extra":None,"zip":"13577","city":"Gonayiv"},
        "default_payment_account": {
            "type": "bankaccount",
            "data": {"iban":"DE30764889448898742946","bank":"Natural Gas Distribution","bic":"CORHPBLV"}
        }
    })
    add_item({"customer_number": "4766825748", "lead_number": "6108409320", "company": "Jetpulse", "salutation": "Ms",
     "title": "Dr", "firstname": "Nicko", "lastname": "Altamirano", "email": "naltamirano5@webs.com",
        "default_address": {"company": "Jetpulse", "salutation": "Ms", "title": "Dr", "firstname": "Nicko", "lastname": "Altamirano", 
                            "street":"Transport","street_nb":"42","street_extra":None,"zip":"17466","city":"Racine"},
        "default_payment_account": {
            "type": "bankaccount",
            "data": {"iban":"DE71220078726827758609","bank":"n/a","bic":"AGFFIOUB"}
        }
    })
    add_item({"customer_number": "6744019511", "lead_number": "5293939017", "company": None, "salutation": "Mr", "title": "",
     "firstname": "Arron", "lastname": "Lovelace", "email": "alovelace6@about.com",
        "default_address": {"company": None, "salutation": "Mr", "title": "", "firstname": "Arron", "lastname": "Lovelace", 
                            "street":"Charing Cross","street_nb":"70","street_extra":"Center","zip":"74291","city":"Jiazhi"},
        "default_payment_account": {
            "type": "bankaccount",
            "data": {"iban":"DE29722131772140957071","bank":"Major Chemicals","bic":"BLKFXBPX"}
        }
    })
    add_item({"customer_number": "6005624423", "lead_number": "7694130202", "company": None, "salutation": "Mr", "title": "Dr",
     "firstname": "Kelbee", "lastname": "Sells", "email": "ksells7@smugmug.com",
        "default_address": {"company": None, "salutation": "Mr", "title": "Dr", "firstname": "Kelbee", "lastname": "Sells", 
                            "street":"Mitchell","street_nb":"3","street_extra":None,"zip":"18953","city":"Darkton"},
        "default_payment_account": {
            "type": "bankaccount",
            "data": {"iban":"DE10215359052558119302","bank":"Business Services","bic":"LNKHLKYE"}
        }
    })
    add_item({"customer_number": "9951272568", "lead_number": "4659830586", "company": "Twitternation", "salutation": "Mr",
     "title": "", "firstname": "Kippie", "lastname": "Moodycliffe", "email": "kmoodycliffe8@state.tx.us",
        "default_address": {"company": "Twitternation", "salutation": "Mr", "title": "", "firstname": "Kippie", "lastname": "Moodycliffe", 
                            "street":"Ludington","street_nb":"5392","street_extra":None,"zip":"77218","city":"Dawusu"},
        "default_payment_account": {
            "type": "bankaccount",
            "data": {"iban":"DE51129102444957773306","bank":"","bic":"BOGATWXX"}
        }
    })
    add_item({"customer_number": "1262700477", "lead_number": "3153235899", "company": None, "salutation": "Mr", "title": "Dr",
     "firstname": "Ivor", "lastname": "Humburton", "email": "ihumburton9@tripadvisor.com",
        "default_address": {"company": None, "salutation": "Mr", "title": "Dr", "firstname": "Ivor", "lastname": "Humburton", 
                            "street":"Boyd","street_nb":"8954","street_extra":None,"zip":"40913","city":"Skibbereen"},
        "default_payment_account": {
            "type": "bankaccount",
            "data": {"iban":"DE00104290428739983073","bank":"","bic":"MEEWXQIE"}
        }
    })
