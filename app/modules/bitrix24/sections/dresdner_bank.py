from flask import Blueprint, render_template, request, make_response


def register_routes(api: Blueprint):

    @api.route("/dresdner/", methods=["GET", "POST"])
    def dresdner():
        if request.form.get("PLACEMENT") == "CRM_LEAD_DETAIL_TAB":
            return render_template("dresdner_bank/iframe.html")
        return render_template("dresdner_bank/iframe.html")
        return "No Placement"

    @api.route("/dresdner/install/", methods=["POST"])
    def dresdner_installer():
        return render_template("dresdner_bank/install.html")
