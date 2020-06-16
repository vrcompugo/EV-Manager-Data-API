from app.models import OfferV2
from app.modules.settings.settings_services import get_one_item as get_settings
from app.modules.cloud.services.calculation import cloud_offer_items_by_pv_offer as cloud_offer

from ._utils import base_offer_data, add_item_to_offer, add_optional_item_to_offer


def cloud_offer_items_by_pv_offer(offer: OfferV2):
    return cloud_offer(offer=offer)
