import json
import base64
import random
import string


from ._connector import get, post
from app.modules.external.bitrix24.drive import create_folder_path, add_file as bitrix_add_file, add_subfolder, get_file, get_folder


def get_random_string(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))


def add_file(data):
    if 'foldername' not in data and 'customer_id' in data:
        data['foldername'] = f"Kunde {data['customer_id']}"

    file_folder_id = create_folder_path(374738, data['foldername'])
    if file_folder_id is None:
        return None

    return bitrix_add_file(file_folder_id, data)
