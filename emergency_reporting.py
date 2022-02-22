import json
import re

from bs4 import BeautifulSoup
from flask import jsonify


def er_login(er_username, er_password, session):
    page = session.get("https://secure.emergencyreporting.com/", allow_redirects=True)
    soup = BeautifulSoup(page.content, features="html.parser")
    result = dict(re.findall(r"(\w*)=(\".*?\"|\S*)", soup.find_all("meta")[0]["content"]))["URL"].replace("'", "")
    soup = BeautifulSoup(session.get(result).content, features="html.parser")
    script = soup.find("script", text=lambda text: text and "var SETTINGS" in text)
    settings_dict = {}
    for line in script.text.split("\n"):
        if "var SETTINGS" in line:
            settings_dict = json.loads(line.replace("var SETTINGS = ", "").replace(";", ""))

    data = {"request_type": "RESPONSE", "signInName": er_username, "password": er_password}
    tenant = settings_dict["hosts"]["tenant"]
    stateproperties = settings_dict["transId"]
    policy = settings_dict["hosts"]["policy"]
    csrf = settings_dict["csrf"]
    headers = {"x-csrf-token": csrf}
    session.post(
        f"https://login.emergencyreporting.com{tenant}/SelfAsserted?tx={stateproperties}&p={policy}",
        data=data,
        headers=headers,
    )
    tokens = session.get(
        f"https://login.emergencyreporting.com/login.emergencyreporting.com/{policy}/api/CombinedSigninAndSignup/confirmed?csrf_token={csrf}&tx={stateproperties}&p={policy}",
        allow_redirects=True,
    )
    soup = BeautifulSoup(tokens.content, features="html.parser")
    session_data = {"state": "/", "code": soup.find(id="code")["value"], "id_token": soup.find(id="id_token")["value"]}
    header = {"Referer": "https://login.emergencyreporting.com/", "Origin": "https://login.emergencyreporting.com/"}
    session.post(
        f"https://secure.emergencyreporting.com/session.php", allow_redirects=True, data=session_data, headers=header
    )


def get_er_calls(er_username, er_password, session):
    resp = session.get("https://secure.emergencyreporting.com/nfirs/main_results.asp")
    if resp.status_code != 200:
        er_login(er_username, er_password, session)
        return jsonify({"message": "ERROR: Unauthorized"}), resp.status_code
    soup = BeautifulSoup(resp.content, features="html.parser")
    calls = []
    item: BeautifulSoup
    tr = soup.find_all("tr")

    for item in tr:
        try:
            if item["style"] == "background: #F8F9FD;" or item["style"] == "background: #EFEEE4;":
                children = item.findChildren("td")
                call_data = {
                    "incident_id": children[0].find("strong").text,
                    "er_id": children[0]["onclick"].replace("javascript:sendForm('", "").replace("');", ""),
                }
                calls.append(call_data)
        except:
            pass
    return json.dumps(calls), resp.status_code
