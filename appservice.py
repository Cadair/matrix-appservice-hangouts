# app_service.py:

import json
from urllib.parse import urljoin
from flask import Flask, jsonify, request

from client import MatrixClient

app = Flask(__name__)


ACCESS_TOKEN = "wfghWEGh3wgWHEf3478sHFWE"

client = MatrixClient("http://localhost:8008", ACCESS_TOKEN)


@app.route("/transactions/<transaction>", methods=["PUT"])
def on_receive_events(transaction):
    print(f"got transation {transaction}")
    events = request.get_json()["events"]
    for event in events:
        print("User: %s Room: %s" % (event["user_id"], event["room_id"]))
        print("Event Type: %s" % event["type"])
        print("Content: %s" % event["content"])
    if "logging" not in event['user_id']:
        client.send_message(event["room_id"], "Hello World")

    return jsonify({})


@app.route("/rooms/<alias>")
def query_alias(alias):
    print(f"Recieved request{alias}")
    alias_localpart = alias.split(":")[0][1:]
    endpoint = f"/createRoom?access_token={ACCESS_TOKEN}"

    content = json.dumps({"room_alias_name": alias_localpart})

    client._post(endpoint, content, client.v1_endpoint)

    return jsonify({})


@app.route("/users/<userid>")
def query_userid(userid):
    print(f"Revieved {userid}")
    return jsonify({})


if __name__ == "__main__":
    client.join_room("#logged_test1:localhost")
    app.run()

