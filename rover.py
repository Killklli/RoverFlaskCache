"""Call data for parsing the site."""
import json
import os
import xml.etree.ElementTree as ET
from collections import defaultdict

import requests
from bs4 import BeautifulSoup


def login(username, password, session: requests.Session(), org):
    """Log into the Rover Website."""
    # Make sure we clear our cookies if we're signing back in
    session.cookies.clear()
    # Load the login page and parse it into usable data
    page = session.get("https://spotteddogtech.com/" + org + "/login.aspx?ReturnUrl=%2f" + org + "%2fHome.aspx")
    soup = BeautifulSoup(page.content, features="html.parser")
    # Set the auth headers for an ASP app
    data = {
        "dnn$ctr$Login$Login_DNN$txtUsername": username,
        "dnn$ctr$Login$Login_DNN$txtPassword": password,
        "__EVENTTARGET": "dnn$ctr$Login$Login_DNN$cmdLogin",
    }
    data["__VIEWSTATE"] = soup.select_one("#__VIEWSTATE")["value"]
    data["__VIEWSTATEGENERATOR"] = soup.select_one("#__VIEWSTATEGENERATOR")["value"]
    data["__EVENTVALIDATION"] = soup.select_one("#__EVENTVALIDATION")["value"]
    # Post the login using our session object so we retain the logged in session.
    session.post("https://spotteddogtech.com/" + org + "/login.aspx?ReturnUrl=%2f" + org + "%2fHome.aspx", data=data)


def update_calls(username, password, session: requests.Session(), org):
    """Update the calls in the database."""
    # Load the AlarmLog page.
    rover_data = BeautifulSoup(
        session.get("https://spotteddogtech.com/" + org + "/Rover/AlarmLog.aspx").text, features="html.parser"
    ).find_all("roverdata")
    # If we didn't get any xml data back re-log in.
    if len(rover_data) <= 0:
        login(username, password, session, org)
    else:
        # For all of the call data append it to our global call store and add the incident id as the key
        all_calls = {}
        for call in rover_data:
            call_dict = etree_to_dict(ET.fromstring(str(call)))["roverdata"]
            all_calls[call_dict.get("incidentnumber")] = call_dict

        # Verify the json file exists
        if not os.path.exists("calls.json"):
            with open("calls.json", "w") as writer:
                writer.write("{}")

        # Read our existing json file
        with open("calls.json", "r") as read_file:
            loaded_calls = json.loads(read_file.read())

        for call in all_calls:
            # Check if our call already exists
            if loaded_calls.get(call):
                # If our call does exist, verify if it matches what we already have and if it does not update it.
                if loaded_calls.get(call) != all_calls.get(call):
                    loaded_calls[call] = all_calls[call]
            # Else just append it cause we don't have it.
            else:
                loaded_calls[call] = all_calls[call]
        # Write the json data back to a file.
        with open("calls.json", "w") as writer:
            writer.write(json.dumps(loaded_calls))


def etree_to_dict(t):
    """Convert XML data to a dict object."""
    d = {t.tag: {} if t.attrib else None}
    # Convert all the tags to a list
    children = list(t)
    # If we still have sub data back recursively map the data back
    if children:
        dd = defaultdict(list)
        # Recursion call to add it as another value
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    # If its an attribute just add it as an attribute
    if t.attrib:
        d[t.tag].update(("@" + k, v) for k, v in t.attrib.items())
    # If we're containing text just append the text to the related child
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]["#text"] = text
        else:
            d[t.tag] = text
    # Return our dictonary
    return d
