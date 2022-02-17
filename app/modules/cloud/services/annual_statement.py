import datetime
from flask import render_template

from app.modules.settings import get_settings
from app.modules.external.bitrix24.products import get_product
from app.utils.gotenberg import gotenberg_pdf


def generate_annual_statement_pdf(data, statement, return_string=False):
    config = get_settings(section="offer/pdf")
    config_general = get_settings(section="general")
    if data is not None:
        if "datetime" not in data:
            data["datetime"] = datetime.datetime.now()
        data["heading"] = "Angebot/Leistungsverzeichnis"
        foreword_product = get_product("Vortext: Angebot PV", "Texte")
        if foreword_product is not None:
            data["foreword"] = foreword_product["DESCRIPTION"]
            data["foreword_type"] = foreword_product["DESCRIPTION_TYPE"]

        appendix_product = get_product("Nachtext Angebot 8 Tage", "Texte")
        if appendix_product is not None:
            data["appendix"] = appendix_product["DESCRIPTION"]
            data["appendix_type"] = appendix_product["DESCRIPTION_TYPE"]
        header_content = render_template(
            "cloud2/annual_statement/header.html",
            base_url=config_general["base_url"],
            data=data,
            statement=statement
        )
        footer_content = render_template(
            "cloud2/annual_statement/footer.html",
            base_url=config_general["base_url"],
            data=data,
            statement=statement
        )
        content = render_template(
            "cloud2/annual_statement/index.html",
            base_url=config_general["base_url"],
            data=data,
            statement=statement
        )
        data["datetime"] = str(data["datetime"])
        if return_string:
            return content
        pdf = gotenberg_pdf(
            content,
            content_header=header_content,
            content_footer=footer_content,
            landscape=False)
        return pdf
    return None