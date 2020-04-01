import requests
import os
from io import StringIO


def generate_pdf(content, output_path=None, content_footer=None, content_header=None):
    data = {
        "index.html": StringIO(content),
        "marginBottom": (None, "1.4"),
        "marginLeft": (None, "0.3"),
        "marginRight": (None, "0.3"),
        "marginTop": (None, "0.3"),
        "scale": (None, "1")
    }
    if content_footer is not None:
        data["footer.html"] = StringIO(content_footer)

    gotenberg_url = os.getenv('GOTENBERG_URL') or "http://gotenberg:3000"

    result = requests.post(gotenberg_url + "/convert/html", files=data)
    if output_path is None:
        return result.content
    with open(output_path, "wb") as f:
        f.write(result.content)
    return None
