from app.models import OfferV2


def get_offer_by_offer_number(offer_number):
    offer = OfferV2.query.filter(OfferV2.number == offer_number).first()
    return offer
