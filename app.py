"""Main flask UI app."""
import json
import os
import threading
import time

import requests
from dateutil import parser
from flask import Flask, jsonify, request

from rover import login, update_calls

# Set up flask app and required env vars
app = Flask(__name__)
username = os.environ["username"]
password = os.environ["password"]
rover_org = os.environ["rover_org"]
api_key = os.environ["api_key"]


@app.route("/call_stats")
def stats():
    """Publically readable call stats."""
    with open("calls.json", "r") as read_file:
        calls = {}
        call_data = json.loads(read_file.read())
        # With the loaded json file and take the call answer time and convert it into a usable timestamp
        for call in call_data:
            date = parser.parse(call_data[call]["times"].get("callanswertime")).strftime("%m/%d/%Y")
            # If we already have the timestamp in the call response just append the call
            if calls.get(date):
                calls[date].append(call_data[call]["incidenttype"])
            # Just add the call if we don't already have it
            else:
                calls[date] = [call_data[call]["incidenttype"]]
        return json.dumps(calls), 200


@app.route("/call_data")
def data():
    """All usable call data."""
    headers = request.headers
    auth = headers.get("X-Api-Key")
    # Check if we have an X-Api-Key auth header to authenticate with
    if auth == api_key:
        with open("calls.json", "r") as read_file:
            return read_file.read(), 200
    else:
        return jsonify({"message": "ERROR: Unauthorized"}), 401


if __name__ == "__main__":
    # Start flask
    app.run()
    # Log into Rover site
    session = requests.Session()
    login(username, password, session, rover_org)

    # Update the call stats every minute
    def call_thread():
        """Threaded function to call the Rover site every minute."""
        while True:
            update_calls(username, password, session, rover_org)
            time.sleep(60)

    threading.Thread(target=call_thread).start()
