# app_service.py:

from urllib.parse import urljoin
import json, requests  # we will use this later
from flask import Flask, jsonify, request

from client import post, send_message

app = Flask(__name__)


@app.route("/transactions/<transaction>", methods=["PUT"])
def on_receive_events(transaction):
    print(f"got transation {transaction}")
    events = request.get_json()["events"]
    for event in events:
        print("User: %s Room: %s" % (event["user_id"], event["room_id"]))
        print("Event Type: %s" % event["type"])
        print("Content: %s" % event["content"])
    send_message(event["room_id"], "Hello World")

    return jsonify({})


@app.route("/rooms/<alias>")
def query_alias(alias):
    print(f"Recieved request{alias}")
    alias_localpart = alias.split(":")[0][1:]
    endpoint = "/createRoom?access_token=wfghWEGh3wgWHEf3478sHFWE"

    content = json.dumps({"room_alias_name": alias_localpart})

    post(endpoint, content)

    return jsonify({})


@app.route("/users/<userid>")
def query_userid(userid):
    print(f"Revieved {userid}")
    return jsonify({})


if __name__ == "__main__":
    app.run()
