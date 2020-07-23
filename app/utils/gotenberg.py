import requests
import os
from io import StringIO


def generate_pdf(content, output_path=None, content_footer=None, content_header=None, landscape=False, margins=[], wait_delay="0.1"):
    data = {
        "index.html": StringIO(content),
        "landscape": (None, landscape),
        "scale": (None, "1"),
        "waitDelay": (None, wait_delay),
        "waitTimeout": (None, 30)
    }
    if len(margins) == 0:
        data["marginBottom"] = (None, "1.4")
        data["marginLeft"] = (None, "0.3")
        data["marginRight"] = (None, "0.3")
        data["marginTop"] = (None, "0.3")
    else:
        data["marginTop"] = (None, margins[0])
        data["marginRight"] = (None, margins[1])
        data["marginBottom"] = (None, margins[2])
        data["marginLeft"] = (None, margins[3])
    if content_footer is not None:
        data["footer.html"] = StringIO(content_footer)

    gotenberg_url = os.getenv('GOTENBERG_URL') or "http://gotenberg:3000"

    result = requests.post(gotenberg_url + "/convert/html", files=data)
    if output_path is None:
        return result.content
    with open(output_path, "wb") as f:
        f.write(result.content)
    return None
