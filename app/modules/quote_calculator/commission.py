from app.exceptions import ApiException


def calculate_commission_data(quote_data, data, quote_key=""):
    if quote_key == "pv_quote":
        if data["data"].get(f"{quote_key}_special_offer_technik_service", False) is True and "technik_service_packet" in data["data"]["extra_options"]:
            technik_and_service_produkt = {
                "NAME": "Sonderaktion Technik und Service Paket",
                "DESCRIPTION": f"",
                "DESCRIPTION_TYPE": "text",
                "quantity": 1,
                "PRICE": -4260,
                "total_price": -4260
            }
            if 272 in data["assigned_user"]["UF_DEPARTMENT"]:
                technik_and_service_produkt["PRICE"] = -4047.67
                technik_and_service_produkt["total_price"] = -4047.67
            quote_data["products"].append(technik_and_service_produkt)
            quote_data["subtotal_net"] = quote_data["subtotal_net"] + technik_and_service_produkt["total_price"]
    quote_data["calculated"]["unchanged_total_net"] = quote_data["subtotal_net"]

    if data["data"].get(f"{quote_key}_price_increase_percent", None) is not None and data["data"].get(f"{quote_key}_price_increase_percent", None) != "":
        data["data"][f"{quote_key}_price_increase_percent"] = float(data["data"][f"{quote_key}_price_increase_percent"])
        data["data"][f"{quote_key}_price_increase_euro"] = round(quote_data["calculated"]["unchanged_total_net"] * data["data"][f"{quote_key}_price_increase_percent"] / 100, 2)
        if data["data"][f"{quote_key}_price_increase_percent"] > 10:
            data["data"][f"{quote_key}_price_increase_percent"] = 10
            data["data"][f"{quote_key}_price_increase_euro"] = round(quote_data["calculated"]["unchanged_total_net"] * data["data"][f"{quote_key}_price_increase_percent"] / 100, 2)

    if 272 in data["assigned_user"]["UF_DEPARTMENT"]:
        data["data"][f"{quote_key}_price_increase_percent"] = 16.8
        data["data"][f"{quote_key}_price_increase_euro"] = round(quote_data["calculated"]["unchanged_total_net"] * data["data"][f"{quote_key}_price_increase_percent"] / 100, 2)

    quote_data["subtotal_net"] = 0
    for product in quote_data["products"]:
        if product["PRICE"] is not None:
            if data["data"].get(f"{quote_key}_price_increase_percent", None) is not None and data["data"].get(f"{quote_key}_price_increase_percent", None) != "":
                product["PRICE"] = float(product["PRICE"]) * (1 + float(data["data"][f"{quote_key}_price_increase_percent"]) / 100)
            product["total_price"] = float(product["PRICE"]) * float(product["quantity"])
            quote_data["subtotal_net"] = quote_data["subtotal_net"] + product["total_price"]
    quote_data["calculated"]["after_increase_total_net"] = quote_data["subtotal_net"]
    if data["data"].get(f"{quote_key}_discount_euro", None) is not None and data["data"].get(f"{quote_key}_discount_euro", None) != "" and float(data["data"][f"{quote_key}_discount_euro"]) > 0:
        data["data"][f"{quote_key}_discount_percent"] = round((float(data["data"][f"{quote_key}_discount_euro"]) / quote_data["subtotal_net"]) * 100, 2)
        if quote_key == "pv_quote":
            if data["data"][f"{quote_key}_discount_percent"] > 15:
                data["data"][f"{quote_key}_discount_percent"] = 15
                data["data"][f"{quote_key}_discount_euro"] = round(quote_data["subtotal_net"] * (data["data"][f"{quote_key}_discount_percent"] / 100), 2)
        else:
            if data["data"][f"{quote_key}_discount_percent"] > 5:
                data["data"][f"{quote_key}_discount_percent"] = 5
                data["data"][f"{quote_key}_discount_euro"] = round(quote_data["subtotal_net"] * (data["data"][f"{quote_key}_discount_percent"] / 100), 2)
        quote_data["products"].append({
            "NAME": "Nachlass",
            "DESCRIPTION": f"",
            "DESCRIPTION_TYPE": "text",
            "quantity": 1,
            "PRICE": -float(data["data"][f"{quote_key}_discount_euro"]),
            "total_price": -float(data["data"][f"{quote_key}_discount_euro"])
        })
        quote_data["subtotal_net"] = quote_data["subtotal_net"] - float(data["data"][f"{quote_key}_discount_euro"])
        quote_data["calculated"]["after_discount_total_net"] = quote_data["calculated"]["unchanged_total_net"] - float(data["data"][f"{quote_key}_discount_euro"])
    else:
        quote_data["calculated"]["after_discount_total_net"] = quote_data["calculated"]["unchanged_total_net"]

    quote_data["calculated"]["commission_total_net"] = quote_data["subtotal_net"]
    quote_data["calculated"]["discountable_subtotal_net"] = quote_data["calculated"]["after_increase_total_net"]

    quote_data["calculated"]["effective_internal_discount_rate"] = (1 - quote_data["calculated"]["commission_total_net"] / quote_data["calculated"]["unchanged_total_net"]) * 100
    quote_data["calculated"]["commission_rate"] = get_commission_rate(quote_data=quote_data, data=data, quote_key=quote_key)

    quote_data["calculated"]["unchanged_commission_value"] = quote_data["calculated"]["unchanged_total_net"] * (quote_data["calculated"]["commission_rate"] / 100)
    quote_data["calculated"]["after_increase_commission_value"] = quote_data["calculated"]["unchanged_commission_value"] + (quote_data["calculated"]["after_increase_total_net"] - data["calculated"]["unchanged_total_net"]) / 2
    quote_data["calculated"]["after_discount_commission_value"] = quote_data["calculated"]["after_discount_total_net"] * (quote_data["calculated"]["commission_rate"] / 100)
    quote_data["calculated"]["commission_value"] = quote_data["calculated"]["commission_total_net"] * (quote_data["calculated"]["commission_rate"] / 100)
    if quote_data["calculated"]["commission_total_net"] > quote_data["calculated"]["unchanged_total_net"]:
        if 272 in data["assigned_user"]["UF_DEPARTMENT"]:
            quote_data["calculated"]["commission_value"] = (
                quote_data["calculated"]["commission_value"]
                + quote_data["calculated"]["commission_total_net"] - quote_data["calculated"]["unchanged_total_net"]
            )
        else:
            quote_data["calculated"]["commission_value"] = (
                quote_data["calculated"]["commission_value"]
                + (quote_data["calculated"]["commission_total_net"] - quote_data["calculated"]["unchanged_total_net"]) / 2
            )

    quote_data["total_net"] = quote_data["subtotal_net"]


def get_commission_rate(quote_data, data, quote_key):
    if quote_key == "pv_quote":
        if 23 in data["assigned_user"]["UF_DEPARTMENT"]:
            if quote_data["calculated"]["effective_internal_discount_rate"] <= 0:
                return 6
            if 0 < quote_data["calculated"]["effective_internal_discount_rate"] <= 5:
                return 5
            if 5 < quote_data["calculated"]["effective_internal_discount_rate"] <= 8:
                return 4
            if 8 < quote_data["calculated"]["effective_internal_discount_rate"] <= 10:
                return 3.5
            if 10 < quote_data["calculated"]["effective_internal_discount_rate"] <= 15:
                return 3
        else:
            if quote_data["calculated"]["effective_internal_discount_rate"] <= 0:
                return 10
            if 0 < quote_data["calculated"]["effective_internal_discount_rate"] <= 5:
                return 8.5
            if 5 < quote_data["calculated"]["effective_internal_discount_rate"] <= 8:
                return 7.5
            if 8 < quote_data["calculated"]["effective_internal_discount_rate"] <= 10:
                return 6.5
            if 10 < quote_data["calculated"]["effective_internal_discount_rate"] <= 15:
                return 5
    if 23 in data["assigned_user"]["UF_DEPARTMENT"]:
        if quote_data["calculated"]["effective_internal_discount_rate"] <= 0:
            return 2.5
        if 0 < quote_data["calculated"]["effective_internal_discount_rate"] <= 5:
            return 2
    if quote_data["calculated"]["effective_internal_discount_rate"] <= 0:
        return 4.25
    if 0 < quote_data["calculated"]["effective_internal_discount_rate"] <= 5:
        return 3.75
