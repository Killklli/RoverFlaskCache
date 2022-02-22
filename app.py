"""Main flask UI app."""
import json
import os
import threading
import time

import requests
from flask import Flask, jsonify, request

from emergency_reporting import er_login, get_er_calls
from rover import login, return_public_calls, update_calls

# Set up flask app and required env vars
app = Flask(__name__)
username = os.environ["username"]
password = os.environ["password"]
rover_org = os.environ["rover_org"]
api_keys = os.environ["api_keys"]
er_username = os.environ["er_username"]
er_password = os.environ["er_password"]


def authenticate(request):
    headers = request.headers
    auth = headers.get("X-Api-Key")
    # Check if we have an X-Api-Key auth header to authenticate with
    if auth in api_keys:
        return True
    else:
        return False


@app.route("/call_stats", methods=["GET"])
def stats():
    """Publically readable call stats."""
    if authenticate(request):
        return return_public_calls()
    return jsonify({"message": "ERROR: Unauthorized"}), 401


@app.route("/call_data", methods=["GET"])
def data():
    """All usable call data."""
    if authenticate(request):
        with open("calls.json", "r") as read_file:
            return read_file.read(), 200
    return jsonify({"message": "ERROR: Unauthorized"}), 401


@app.route("/add_losap", methods=["POST"])
def losap():
    # Needs User Header
    # Needs body like {year: 2021, qualified: 1, points: 1, notes: "test"}
    if authenticate(request):
        user = request.headers.get("User")
        print(f"https://secure.emergencyreporting.com/v6/admin/api/user/{user}/losap/history/new")
        header = {
            "Referer": "https://secure.emergencyreporting.com/v6/admin/losap/users",
            "Origin": "https://secure.emergencyreporting.com/",
        }
        resp = session.post(
            f"https://secure.emergencyreporting.com/v6/admin/api/user/{user}/losap/history/new",
            json=request.json,
            headers=header,
        )
        if resp.status_code != 200:
            return jsonify({"message": "ERROR: Something went wrong"}), resp.status_code
        else:
            return jsonify({"message": "Success"}), 200
    return jsonify({"message": "ERROR: Unauthorized"}), 401


@app.route("/get_users", methods=["GET"])
def users():
    if authenticate(request):
        resp = session.get("https://secure.emergencyreporting.com/v6/admin/api/users")
        if resp.status_code != 200:
            return jsonify({"message": "ERROR: Something went wrong"}), resp.status_code
        else:
            return jsonify({"message": "Success"}), 200
    return jsonify({"message": "ERROR: Unauthorized"}), 401


@app.route("/get_er_calls", methods=["GET"])
def er_calls():
    if authenticate(request):
        return get_er_calls(er_username, er_password, session)
    return jsonify({"message": "ERROR: Unauthorized"}), 401


@app.route("/edit_responders", methods=["POST"])
def edit_call_responders():
    # Edit the incident https://secure.emergencyreporting.com/nfirs/edit_incident.asp
    # iid: 64666594

    # https://secure.emergencyreporting.com/nfirs/formbasic4_2.asp
    # eid: 64474161
    # method: EDIT
    # redirectto: formbasic4.asp
    # thisappid:
    # thisappmethod:
    # otherpids: 997008
    # nonApparatusPersonnelLastUpdatedByUserID:
    # nonApparatusPersonnelLastUpdatedDateTime:
    # shouldShowPersonnelUpdatedDialog: true
    # othernumberofpeople: 1
    pass


if __name__ == "__main__":
    # Log into Rover site
    session = requests.Session()
    session.cookies.clear()
    login(username, password, session, rover_org)
    er_login(er_username, er_password, session)

    # Update the call stats every minute
    def call_thread():
        """Threaded function to call the Rover site every five minutes."""
        while True:
            update_calls(username, password, session, rover_org)
            time.sleep(300)

    threading.Thread(target=call_thread).start()

    # Start flask
    app.run()
