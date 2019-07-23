import tempfile
import re
from io import StringIO
import uuid

from app import db
from app.modules.file.file_services import add_item , update_item, get_one_item

from ._connector import post, get
from ._association import find_association, associate_item


def filter_input(data):

    return data


def run_import(model, model_id, id):
    response = get("{}/Download/{}".format(model, id), raw=True)
    item_data = {
        "filename": get_filename_from_header(response),
        "content-type": response.headers.get("Content-Type"),
        "uuid": str(uuid.uuid4()),
        "model": model,
        "model_id": model_id,
        "file_content": response.content
    }
    item = find_association(model=model + "File", remote_id=id)
    if item is None:
        item = add_item(item_data)
        associate_item(model=model + "File", remote_id=id, local_id=item.id)
    else:
        item = update_item(id=item.local_id, data=item_data)
    return item


def get_filename_from_header(response):
    """
    Get filename from content-disposition
    """
    content_disposition = response.headers.get("Content-Disposition")
    print("cd:", content_disposition)
    if not content_disposition:
        return "unnamed"
    fname = re.findall('filename=(.+)', content_disposition)
    if len(fname) == 0:
        return "unnamed"
    return fname[0]
