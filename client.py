from time import time
import json

import requests
from flask import jsonify

from urllib.parse import urljoin, quote
import os.path

BASE_URL = "http://localhost:8008"
API_ENDPOINT = "_matrix/client/api/v1/"


def get_url(endpoint, api_endpoint):
    end = urljoin(api_endpoint, endpoint)
    target = urljoin(BASE_URL, end)
    return target


def post(endpoint, content, api_endpoint=None):
    """
    Send a post request to endpoint with content.
    """
    if not api_endpoint:
        api_endpoint = API_ENDPOINT
    target = get_url(endpoint, api_endpoint)

    print(f"post {content} to {target}")

    headers = {"Content-Type":"application/json"}

    resp = requests.post(target, json.dumps(content), headers=headers)
    print(resp, resp.content)


def get(endpoint, params=None, api_endpoint=None):
    if not api_endpoint:
        api_endpoint = API_ENDPOINT
    target = get_url(endpoint, api_endpoint)

    resp = requests.get(target, params)
    print(resp.content)
    return resp.content


def put(endpoint, data, api_endpoint=None):
    if not api_endpoint:
        api_endpoint = API_ENDPOINT
    target = get_url(endpoint, api_endpoint)

    print(f"Putting {data} to {target}")
    resp = requests.put(target, json.dumps(data))
    print(resp, resp.content)



def get_text_body(text, msgtype="m.text"):
    return {
        "msgtype": msgtype,
        "body": text
    }


def send_message(room_id, message):
    """
    Send message
    """
    transaction = quote(str(int(time() * 1000)))
    room_id = quote(room_id)
    event_type = quote("m.room.message")

    path = f"rooms/{room_id}/send/{event_type}?access_token=wfghWEGh3wgWHEf3478sHFWE"
    message = get_text_body(message)
    print(f"Sending {message} to {path}")

    post(path, message, api_endpoint="_matrix/client/r0/")


def get_room_id(room_alias):
    api_endpoint = "_matrix/client/r0/"
    room_alias = quote(room_alias)

    get("directory/room/{room_alias}", api_endpoint=api_endpoint)

