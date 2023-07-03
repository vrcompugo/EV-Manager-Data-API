from .synergy import calculate_synergy_wi as calculate_synergy_wi_current
from .synergy import calculate_synergy_wi2 as calculate_synergy_wi2_current
from .synergy import generate_synergy_pdf as generate_synergy_pdf_current

from .synergy_until_30_06_2023 import calculate_synergy_wi as calculate_synergy_wi_30_06_23
from .synergy_until_30_06_2023 import calculate_synergy_wi2 as calculate_synergy_wi2_30_06_23
from .synergy_until_30_06_2023 import generate_synergy_pdf as generate_synergy_pdf_30_06_23

def calculate_synergy_wi(data):
    if data.get('old_price_calculation') == 'yogoO96xeqmngNwplted' :
        return calculate_synergy_wi_30_06_23(data)
    return calculate_synergy_wi_current(data)

def calculate_synergy_wi2(return_data):
    if return_data.get('data').get('old_price_calculation') == 'yogoO96xeqmngNwplted' :
        return calculate_synergy_wi2_30_06_23(return_data)
    return calculate_synergy_wi2_current(return_data)

def generate_synergy_pdf(lead_id, data, only_pages=None):
    if data.get('data').get('old_price_calculation') == 'yogoO96xeqmngNwplted' :
        return generate_synergy_pdf_30_06_23(lead_id, data, only_pages)
    return generate_synergy_pdf_current(lead_id, data, only_pages)