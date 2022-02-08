"""
THIS MODULE IS NOT ALLOWED TO BE IMPORTED BY OTHER MODULES !!!!!!!!

This module is still synchronous, unfortunately.
However, the results.json file seems to be updated in real time, so this should only really be called once.
"""

import requests
import json
from functions import file_handler, my_format, css_selector, url_encode, insert_into_dict, soup_bowl
from webmeta import WebsiteMeta

result_json = ""
LOGIN_URL = r"https://icas.bau.edu.lb:8443/cas/login?service=https%3A%2F%2Fmoodle.bau.edu.lb%2Flogin%2Findex.php"
SECURE_URL = r"https://moodle.bau.edu.lb/my/"
SERIVCE_URL = r"https://moodle.bau.edu.lb/lib/ajax/service.php"

api_payload = [
    {
        "index": 0,
        "methodname": "message_popup_get_popup_notifications",
        "args": {
            "limit": 20,
            "offset": 0,
            "useridto": "20663"
        }
    }
]

courses_payload = [
    {
        "index": 0,
        "methodname": "core_course_get_enrolled_courses_by_timeline_classification",
        "args": {
            "offset": 0,
            "limit": 0,
            "classification": "all",
            "sort": "fullname",
            "customfieldname": "",
            "customfieldvalue": ""
        }
    }
]
with requests.Session() as Session:
    service_headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.7113.93 Safari/537.36",
        'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/jxl,image/webp,*/*;q=0.8",
        'Accept-Language': "en-US,en;q=0.5",
        'Accept-Encoding': "gzip, deflate, br",
        'Referer': "https://moodle.bau.edu.lb/message/output/popup/notifications.php",
        'DNT': "1",
        'Connection': "keep-alive",
        'Upgrade-Insecure-Requests': "1",
        'Sec-Fetch-Dest': "document",
        'Sec-Fetch-Mode': "navigate",
        'Sec-Fetch-Site': "same-origin",
        'Sec-Fetch-User': "?1",
        'Sec-GPC': "1"
    }
    courses_querystring = {
        "service": "https://moodle.bau.edu.lb/login/index.php"}
    login_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.7113.93 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/jxl,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://icas.bau.edu.lb:8443",
        "DNT": "1",
        "Connection": "keep-alive",
        "Referer": r"https://icas.bau.edu.lb:8443/cas/login?service=https%3A%2F%2Fmoodle.bau.edu.lb%2Flogin%2Findex.php",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Sec-GPC": "1"}

    api_headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.7113.93 Safari/537.36",
        'Accept': "application/json, text/javascript, */*; q=0.01",
        'Accept-Language': "en-US,en;q=0.5",
        'Accept-Encoding': "gzip, deflate, br",
        'Content-Type': "application/json",
        'X-Requested-With': "XMLHttpRequest",
        'Origin': "https://moodle.bau.edu.lb",
        'DNT': "1",
        'Connection': "keep-alive",
        'Referer': "https://moodle.bau.edu.lb/my/",
        # 'Cookie': "MoodleSession=bnmceob122qsilkle4iqj2nsvu; BNES_MoodleSession=eA7cedJkx2sqRLiU1yZBleUUCLVzGKRLv+uNNazIb25Y7AmDI8GOHXXADsmVbmSzHi2Cm3kXHmgAUxO1NfVrFT9jvdY+Lp1Yfc81DRIOiJadqJT0nTgwOA==",
        'Sec-Fetch-Dest': "empty",
        'Sec-Fetch-Mode': "cors",
        'Sec-Fetch-Site': "same-origin",
        'Sec-GPC': "1"
    }

    page = Session.get(url=LOGIN_URL)
    my_format("HTML exists  ", f"{bool(page.text)}")
    execution = css_selector(page.text, "[name=execution]", "value")
    my_format("execution string: ", execution)
    login = Session.post(LOGIN_URL,
                         data=url_encode(
                             {"username": WebsiteMeta.username,
                              "password": WebsiteMeta.password,
                              "execution": fr"{execution}", "_eventId": "submit",
                              "geolocation": ""}),
                         headers=login_headers, params=courses_querystring)
    cookie_jar: dict = Session.cookies.get_dict()
    my_format("cookies list: ", cookie_jar)
    my_format(
        "desired cookies",
        f"{[cookie_jar['MoodleSession'], cookie_jar['BNES_MoodleSession']]}")
    moodle_session, bnes_moodle_session = cookie_jar['MoodleSession'], cookie_jar['BNES_MoodleSession']
    service_headers, api_headers = insert_into_dict(
        service_headers, 10,
        ("Cookie",
         fr"MoodleSession={moodle_session}; BNES_MoodleSession={bnes_moodle_session}")), insert_into_dict(api_headers, 10, ("Cookie",
                                                                                                                            fr"MoodleSession={moodle_session}; BNES_MoodleSession={bnes_moodle_session}"))
    r = Session.get(SECURE_URL, headers=service_headers)
    my_format("Reached secure page : ", f"{r.url == SECURE_URL}")
    moodle_html = soup_bowl(r.text)
    my_format("Got Moodle HTML :", f"{'notifications' in r.text}")
    my_format("Cookies in service headers: ",
              f"{json.dumps(service_headers,indent=4)}")
    sesskey = moodle_html.select("[name=sesskey]")[0]["value"]
    my_format("Payload json object: ", api_payload)
    api_querystring = {"sesskey": sesskey,
                       "info": "message_popup_get_popup_notifications"}
    courses_querystring = {
        "sesskey": sesskey, "info": "core_course_get_enrolled_courses_by_timeline_classification"}
    api_response = Session.post(url=SERIVCE_URL,
                                headers=service_headers,
                                json=api_payload,
                                params=api_querystring
                                )
    result_json = api_response.json()
    file_handler("results.json", "w", text=json.dumps(
        api_response.json(), indent=4))
    courses = Session.post(url=SERIVCE_URL,
                           headers=service_headers,
                           json=courses_payload,
                           params=courses_querystring)
    required_json = courses.json()
    if required_json:
        file_handler("courses.json", "w", json.dumps(required_json, indent=4))
