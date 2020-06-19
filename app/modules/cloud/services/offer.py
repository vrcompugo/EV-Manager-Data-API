from app.models import OfferV2, Reseller
from app.modules.auth.auth_services import get_logged_in_user


def get_offer_by_offer_number(offer_number):
    user = get_logged_in_user()
    reseller = Reseller.query.filter(Reseller.user_id == user["id"]).first()
    offer = OfferV2.query\
        .filter(OfferV2.number == offer_number)\
        .filter(OfferV2.offer_group == "cloud-offer")\
        .filter(OfferV2.reseller_id == reseller.id)\
        .first()
    return offer
