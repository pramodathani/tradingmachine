"""
Daily broker login for tradingmachine.

Logs in to every broker whose credentials are held in the MongoDB `settings` collection and records the access token each broker returns in the MongoDB `last_login` collection.
Broker access tokens expire at the end of the trading day, so this module is meant to be run once every morning before the market opens.
"""

import argparse
import base64
import hashlib
import hmac
import json
import ssl
import sys
import time
from datetime import datetime
from urllib.parse import parse_qs
from urllib.parse import urlparse

import pymongo
import pyotp
import requests
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from utilities.configuration import mongodb_configuration

REQUEST_TIMEOUT_SECONDS = 90
PAGE_LOAD_PAUSE_SECONDS = 2
REDIRECT_WAIT_SECONDS = 30


class BrokerLoginError(Exception):
    """
    Raised when a broker refuses a login or does not return an access token.
    """


def open_mongodb_database():
    """
    Open the tradingmachine MongoDB database that holds the broker credentials and access tokens.

    Args:
        None.

    Returns:
        pymongo.database.Database: The tradingmachine database named by the environment configuration.
    """
    client = pymongo.MongoClient(mongodb_configuration["connection_string"])
    return client[mongodb_configuration["database"]]


def read_broker_settings(mongodb_database, broker_name):
    """
    Read one broker's credentials from the `settings` collection.

    Args:
        mongodb_database (pymongo.database.Database): The tradingmachine database.
        broker_name (str): Name of the broker, for example "zerodha".

    Returns:
        dict: The broker's credential fields, without the MongoDB identifier.

    Raises:
        BrokerLoginError: If the broker has no document in the `settings` collection.
    """
    settings = mongodb_database["settings"].find_one({"broker_name": broker_name}, {"_id": 0})
    if settings is None:
        raise BrokerLoginError(f"No credentials for {broker_name} in the settings collection.")
    return settings


def save_last_login(mongodb_database, broker_name, login_details):
    """
    Record a broker's fresh access token in the `last_login` collection.

    Args:
        mongodb_database (pymongo.database.Database): The tradingmachine database.
        broker_name (str): Name of the broker, for example "zerodha".
        login_details (dict): The access token, and any further session values the broker needs on later calls.

    Returns:
        None.
    """
    document = {"broker_name": broker_name}
    document.update(login_details)
    document["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    mongodb_database["last_login"].replace_one({"broker_name": broker_name}, document, upsert=True)


def logged_in_today(mongodb_database, broker_name):
    """
    Report whether a broker already has an access token issued earlier on today's date.

    Args:
        mongodb_database (pymongo.database.Database): The tradingmachine database.
        broker_name (str): Name of the broker, for example "zerodha".

    Returns:
        bool: True when the broker's stored token was issued today, False otherwise.
    """
    document = mongodb_database["last_login"].find_one({"broker_name": broker_name})
    if document is None:
        return False
    last_login = document.get("last_login")
    if not last_login:
        return False
    return last_login[:10] == datetime.now().strftime("%Y-%m-%d")


def start_headless_chrome():
    """
    Start a headless Chrome browser for the brokers whose login runs through a web page.

    Args:
        None.

    Returns:
        selenium.webdriver.Chrome: A running headless Chrome driver, which the caller is responsible for quitting.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return Chrome(options=chrome_options)


class HostnameCheckRelaxedAdapter(requests.adapters.HTTPAdapter):
    """
    A requests transport adapter that verifies the server certificate but does not require its name to match the host being called.

    The certificate must still chain to a trusted authority and still must be in date. Only the name check is dropped, so a self signed or untrusted certificate is still refused.
    """

    def init_poolmanager(self, connections, maxsize, block=False, **pool_arguments):
        """
        Build the connection pool with a TLS context whose hostname check is switched off.

        Args:
            connections (int): Number of connection pools to cache.
            maxsize (int): Number of connections to keep in each pool.
            block (bool): Whether to block when the pool is full.
            **pool_arguments: Further arguments passed on to the pool manager.

        Returns:
            None.
        """
        context = ssl.create_default_context()
        context.check_hostname = False
        pool_arguments["ssl_context"] = context
        pool_arguments["assert_hostname"] = False
        return super().init_poolmanager(connections, maxsize, block, **pool_arguments)


def generate_one_time_password(totp_secret):
    """
    Generate a time based one time password, waiting out the current thirty second window first if the code is about to expire.

    A broker rejects a code that expires between this process generating it and the broker checking it, which shows up as an intermittent "invalid TOTP" failure on an otherwise correct login.

    Args:
        totp_secret (str): The broker account's TOTP secret, as held in the settings collection.

    Returns:
        str: A one time password with at least four seconds of life left in it.
    """
    seconds_until_boundary = 30 - (datetime.now().second % 30)
    if seconds_until_boundary <= 3:
        time.sleep(seconds_until_boundary + 1)
    return pyotp.TOTP(totp_secret).now()


def login_to_dhan(settings):
    """
    Log in to Dhan with the client identifier, the login PIN and a time based one time password.

    Args:
        settings (dict): Dhan's credentials, which must contain client_id, pin and totp_secret.

    Returns:
        dict: The Dhan access token, under the key "access_token".

    Raises:
        BrokerLoginError: If Dhan rejects the login or returns no access token.
    """
    response = requests.post(
        "https://auth.dhan.co/app/generateAccessToken",
        params={
            "dhanClientId": settings["client_id"],
            "pin": settings["pin"],
            "totp": generate_one_time_password(settings["totp_secret"]),
        },
        headers={"Content-Type": "application/json"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code >= 300:
        raise BrokerLoginError(f"Dhan refused the login with status {response.status_code}: {response.text}")
    access_token = response.json().get("accessToken")
    if access_token is None:
        raise BrokerLoginError(f"Dhan returned no access token: {response.text}")
    return {"access_token": access_token}


def login_to_flattrade(settings):
    """
    Log in to Flattrade by opening an authentication session, exchanging the credentials for a request code and exchanging that code for a token.

    Args:
        settings (dict): Flattrade's credentials, which must contain username, password, api_key, api_secret and totp_secret.

    Returns:
        dict: The Flattrade access token, under the key "access_token", and the account identifier the token exchange reports, under the key "uid" when it gives one. The websocket connect message sends the account identifier as both uid and actid, so it is stored alongside the token rather than asked for again.

    Raises:
        BrokerLoginError: If Flattrade rejects the login or returns no access token.
    """
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.5",
        "Host": "authapi.flattrade.in",
        "Origin": "https://auth.flattrade.in",
        "Referer": "https://auth.flattrade.in/",
    }

    response = requests.post("https://auth.flattrade.in/auth/session", headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    if response.status_code != 200:
        raise BrokerLoginError(f"Flattrade would not open a session, status {response.status_code}: {response.text}")
    session_identifier = response.text

    response = requests.post(
        "https://auth.flattrade.in/ftauth",
        json={
            "UserName": settings["username"],
            "Password": hashlib.sha256(settings["password"].encode()).hexdigest(),
            "App": "",
            "ClientID": "",
            "Key": "",
            "APIKey": settings["api_key"],
            "PAN_DOB": generate_one_time_password(settings["totp_secret"]),
            "Sid": session_identifier,
            "Override": "",
        },
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        raise BrokerLoginError(f"Flattrade refused the login with status {response.status_code}: {response.text}")
    authentication = response.json()
    query_parameters = parse_qs(urlparse(authentication.get("RedirectURL", "")).query)
    if "code" not in query_parameters:
        blocking_message = authentication.get("emsg") or authentication.get("stat")
        raise BrokerLoginError(f"Flattrade issued no request code. The reason it gave was {blocking_message}.")
    request_code = query_parameters["code"][0]

    response = requests.post(
        "https://authapi.flattrade.in/trade/apitoken",
        json={
            "api_key": settings["api_key"],
            "request_code": request_code,
            "api_secret": hashlib.sha256((settings["api_key"] + request_code + settings["api_secret"]).encode()).hexdigest(),
        },
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        raise BrokerLoginError(f"Flattrade would not exchange the request code, status {response.status_code}: {response.text}")
    token_response = response.json()
    access_token = token_response.get("token")
    if not access_token:
        raise BrokerLoginError(f"Flattrade returned no access token: {response.text}")
    login_details = {"access_token": access_token}
    if token_response.get("client"):
        login_details["uid"] = token_response.get("client")
    return login_details


def login_to_fyers(settings):
    """
    Log in to Fyers by requesting a login one time password, verifying it together with the login PIN and exchanging the resulting authorisation code for a token.

    Args:
        settings (dict): Fyers' credentials, which must contain app_id, secret_key, fy_id, pin and totp_secret, and may contain redirect_uri.

    Returns:
        dict: The Fyers access token, under the key "access_token".

    Raises:
        BrokerLoginError: If Fyers rejects any step of the login or returns no access token.
    """
    application_identifier = settings["app_id"]
    if "-" in application_identifier:
        application_name, application_type = application_identifier.split("-")
    else:
        application_name, application_type = application_identifier, "100"
    headers = {
        "Accept": "application/json",
        "Content-Type": "text/plain",
    }

    response = requests.post(
        "https://api-t2.fyers.in/vagator/v2/send_login_otp_v2",
        json={
            "fy_id": base64.b64encode(settings["fy_id"].encode()).decode(),
            "app_id": "2",
        },
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code != 200 or response.json().get("request_key") is None:
        raise BrokerLoginError(f"Fyers would not send a login one time password: {response.text}")
    request_key = response.json()["request_key"]

    response = requests.post(
        "https://api-t2.fyers.in/vagator/v2/verify_otp",
        json={
            "otp": generate_one_time_password(settings["totp_secret"]),
            "request_key": request_key,
        },
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code != 200 or response.json().get("request_key") is None:
        raise BrokerLoginError(f"Fyers would not verify the one time password: {response.text}")
    request_key = response.json()["request_key"]

    response = requests.post(
        "https://api-t2.fyers.in/vagator/v2/verify_pin_v2",
        json={
            "identifier": base64.b64encode(settings["pin"].encode()).decode(),
            "identity_type": "pin",
            "request_key": request_key,
        },
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code != 200 or response.json().get("data", {}).get("access_token") is None:
        raise BrokerLoginError(f"Fyers would not verify the login PIN: {response.text}")
    headers["Authorization"] = f"Bearer {response.json()['data']['access_token']}"

    response = requests.post(
        "https://api-t1.fyers.in/api/v3/token",
        json={
            "fyers_id": settings["fy_id"],
            "app_id": application_name,
            "redirect_uri": settings.get("redirect_uri", "https://localhost"),
            "appType": application_type,
            "code_challenge": "",
            "state": "None",
            "scope": "",
            "nonce": "",
            "response_type": "code",
            "create_cookie": True,
        },
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    authorisation_code = None
    if response.status_code in (200, 308):
        authorisation = response.json() if response.content else {}
        authorisation_code = authorisation.get("data", {}).get("auth")
        if authorisation_code is None:
            authorisation_code = parse_qs(urlparse(authorisation.get("Url", "")).query).get("auth_code", [None])[0]
    if authorisation_code is None:
        raise BrokerLoginError(f"Fyers issued no authorisation code: {response.text}")

    response = requests.post(
        "https://api-t1.fyers.in/api/v3/validate-authcode",
        json={
            "grant_type": "authorization_code",
            "appIdHash": hashlib.sha256(f"{application_identifier}:{settings['secret_key']}".encode()).hexdigest(),
            "code": authorisation_code,
        },
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        raise BrokerLoginError(f"Fyers would not validate the authorisation code, status {response.status_code}: {response.text}")
    access_token = response.json().get("access_token")
    if access_token is None:
        raise BrokerLoginError(f"Fyers returned no access token: {response.text}")
    return {"access_token": access_token}


def login_to_groww(settings):
    """
    Log in to Groww by presenting the long lived token together with a time based one time password.

    Args:
        settings (dict): Groww's credentials, which must contain totp_token and totp_secret.

    Returns:
        dict: The Groww access token, under the key "access_token".

    Raises:
        BrokerLoginError: If Groww rejects the login or returns no access token.
    """
    response = requests.post(
        "https://api.groww.in/v1/token/api/access",
        json={
            "key_type": "totp",
            "totp": generate_one_time_password(settings["totp_secret"]),
        },
        headers={
            "Authorization": f"Bearer {settings['totp_token']}",
            "Content-Type": "application/json",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code >= 300:
        raise BrokerLoginError(f"Groww refused the login with status {response.status_code}: {response.text}")
    body = response.json()
    payload = body.get("payload", body)
    access_token = payload.get("token")
    if access_token is None:
        raise BrokerLoginError(f"Groww returned no access token: {response.text}")
    return {"access_token": access_token}


def login_to_indmoney(settings):
    """
    Log in to IND Money with the client identifier, the MPIN and a time based one time password.

    Args:
        settings (dict): IND Money's credentials, which must contain client_id, mpin and totp_secret.

    Returns:
        dict: The IND Money access token, under the key "access_token".

    Raises:
        BrokerLoginError: If IND Money rejects the login or returns no access token.
    """
    response = requests.post(
        "https://api.indstocks.com/generate/token",
        json={
            "mpin": settings["mpin"],
            "totp": generate_one_time_password(settings["totp_secret"]),
        },
        headers={
            "x-api-key": settings["client_id"],
            "Content-Type": "application/json",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        raise BrokerLoginError(f"IND Money refused the login with status {response.status_code}: {response.text}")
    access_token = response.json().get("token")
    if access_token is None:
        raise BrokerLoginError(f"IND Money returned no access token: {response.text}")
    return {"access_token": access_token}


def login_to_kotak(settings):
    """
    Log in to Kotak Securities by trading the mobile number and a time based one time password for a session, then confirming that session with the MPIN.

    Args:
        settings (dict): Kotak's credentials, which must contain api_key, mobile_number, ucc_code, totp_secret and mpin.

    Returns:
        dict: The Kotak access token under the key "access_token", together with the session identifier under "sid" and the account's API host under "base_url".

    Raises:
        BrokerLoginError: If Kotak rejects either step of the login or returns no access token.
    """
    headers = {
        "Authorization": settings["api_key"],
        "neo-fin-key": "neotradeapi",
        "Content-Type": "application/json",
    }

    response = requests.post(
        "https://mis.kotaksecurities.com/login/1.0/tradeApiLogin",
        data=json.dumps({
            "mobileNumber": settings["mobile_number"],
            "ucc": settings["ucc_code"],
            "totp": generate_one_time_password(settings["totp_secret"]),
        }),
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code != 200 or "data" not in response.json():
        raise BrokerLoginError(f"Kotak refused the login with status {response.status_code}: {response.text}")
    session = response.json()["data"]

    headers["Auth"] = session["token"]
    headers["sid"] = session["sid"]
    response = requests.post(
        "https://mis.kotaksecurities.com/login/1.0/tradeApiValidate",
        data=json.dumps({"mpin": settings["mpin"]}),
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code >= 300 or "data" not in response.json():
        raise BrokerLoginError(f"Kotak would not validate the MPIN, status {response.status_code}: {response.text}")
    validated_session = response.json()["data"]
    if "token" not in validated_session:
        raise BrokerLoginError(f"Kotak returned no access token: {response.text}")
    return {
        "access_token": validated_session["token"],
        "sid": validated_session["sid"],
        "base_url": validated_session["baseUrl"],
    }


def login_to_shoonya(settings):
    """
    Log in to Shoonya by driving its web login page in a headless browser and exchanging the authorisation code it redirects with for a token.

    Args:
        settings (dict): Shoonya's credentials, which must contain vendor_code, ucc_code, password, totp_secret and api_secret.

    Returns:
        dict: The Shoonya access token, under the key "access_token".

    Raises:
        BrokerLoginError: If the login page does not redirect with an authorisation code, or Shoonya returns no access token.
    """
    driver = start_headless_chrome()
    try:
        driver.get(f"https://trade.shoonya.com/OAuthlogin/investor-entry-level/login?api_key={settings['vendor_code']}&route_to={settings['ucc_code']}")
        time.sleep(PAGE_LOAD_PAUSE_SECONDS)
        driver.find_element(By.XPATH, '//*[@id="lgnusrid"]').send_keys(settings["ucc_code"])
        driver.find_element(By.XPATH, '//*[@id="lgnpwd"]').send_keys(settings["password"])
        driver.find_element(By.XPATH, '//*[@id="lgnotp"]').send_keys(generate_one_time_password(settings["totp_secret"]))
        driver.find_element(By.XPATH, '//*[@id="app"]/div[9]/div/div/div[2]/div/div[2]/form/button').click()
        try:
            WebDriverWait(driver, REDIRECT_WAIT_SECONDS).until(lambda browser: "code=" in browser.current_url)
        except TimeoutException:
            raise BrokerLoginError(f"Shoonya did not redirect with an authorisation code. The last page was {driver.current_url}.")
        authorisation_code = parse_qs(urlparse(driver.current_url).query)["code"][0]
    finally:
        driver.quit()

    checksum = hashlib.sha256((settings["vendor_code"] + settings["api_secret"] + authorisation_code).encode()).hexdigest()
    response = requests.post(
        "https://api.shoonya.com/NorenWClientAPI/GenAcsTok",
        data="jData=" + json.dumps({
            "code": authorisation_code,
            "checksum": checksum,
            "uid": settings["ucc_code"],
        }),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code >= 300:
        raise BrokerLoginError(f"Shoonya would not exchange the authorisation code, status {response.status_code}: {response.text}")
    access_token = response.json().get("susertoken")
    if access_token is None:
        raise BrokerLoginError(f"Shoonya returned no access token: {response.text}")
    return {"access_token": access_token}


def login_to_stoxkart(settings):
    """
    Log in to Stoxkart by driving its web login page in a headless browser and signing the request token it redirects with.

    Args:
        settings (dict): Stoxkart's credentials, which must contain api_key, api_secret, ucc_code, api_password and totp_secret.

    Returns:
        dict: The Stoxkart access token, under the key "access_token".

    Raises:
        BrokerLoginError: If the login page does not redirect with a request token, or Stoxkart returns no access token.
    """
    driver = start_headless_chrome()
    try:
        driver.get(f"https://superrtrade.stoxkart.com/login?api_key={settings['api_key']}")
        time.sleep(PAGE_LOAD_PAUSE_SECONDS)
        driver.find_element(By.XPATH, '//*[@id=":R19la6jatm:"]').send_keys(settings["ucc_code"])
        driver.find_element(By.XPATH, '//*[@id=":Rkqla6jatm:"]').send_keys(settings["api_password"])
        driver.find_element(By.XPATH, '//*[@id="__next"]/div[2]/div[1]/div/form/div/div[3]/button').click()
        time.sleep(PAGE_LOAD_PAUSE_SECONDS)
        driver.find_element(By.XPATH, "/html/body/div[2]/div[3]/div/div/div/div[2]/div[1]/input").send_keys(generate_one_time_password(settings["totp_secret"]))
        driver.find_element(By.XPATH, "/html/body/div[2]/div[3]/div/div/div/div[3]/button[1]").click()
        try:
            WebDriverWait(driver, REDIRECT_WAIT_SECONDS).until(lambda browser: "request_token=" in browser.current_url)
        except TimeoutException:
            raise BrokerLoginError(f"Stoxkart did not redirect with a request token. The last page was {driver.current_url}.")
        request_token = parse_qs(urlparse(driver.current_url).query)["request_token"][0]
    finally:
        driver.quit()

    signature = hmac.new(
        (settings["api_key"] + request_token).encode(),
        settings["api_secret"].encode(),
        hashlib.sha256,
    ).hexdigest()
    response = requests.post(
        "https://openapi.stoxkart.com/auth/token",
        data=json.dumps({
            "api_key": settings["api_key"],
            "signature": signature,
            "req_token": request_token,
        }),
        headers={"Content-Type": "application/json"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code >= 300:
        raise BrokerLoginError(f"Stoxkart would not exchange the request token, status {response.status_code}: {response.text}")
    body = response.json()
    access_token = body.get("data", body).get("access_token")
    if access_token is None:
        raise BrokerLoginError(f"Stoxkart returned no access token: {response.text}")
    return {"access_token": access_token}


def login_to_wisdom_capital(settings):
    """
    Log in to Wisdom Capital by posting the application key and secret to its session endpoint.

    Wisdom Capital serves this endpoint under a certificate issued to another company, so the request goes through an adapter that verifies the certificate chain but not the hostname.

    Args:
        settings (dict): Wisdom Capital's credentials, which must contain api_key and api_secret.

    Returns:
        dict: The Wisdom Capital access token, under the key "access_token".

    Raises:
        BrokerLoginError: If Wisdom Capital rejects the login or returns no access token.
    """
    session = requests.Session()
    session.mount("https://trade.wisdomcapital.in", HostnameCheckRelaxedAdapter())
    response = session.post(
        "https://trade.wisdomcapital.in/interactive/user/session",
        json={
            "appKey": settings["api_key"],
            "secretKey": settings["api_secret"],
        },
        headers={"Content-Type": "application/json"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code >= 300:
        raise BrokerLoginError(f"Wisdom Capital refused the login with status {response.status_code}: {response.text}")
    access_token = (response.json().get("result") or {}).get("token")
    if access_token is None:
        raise BrokerLoginError(f"Wisdom Capital returned no access token: {response.text}")
    return {"access_token": access_token}


def login_to_zerodha(settings):
    """
    Log in to Zerodha by driving its Kite Connect login page in a headless browser and exchanging the request token it redirects with for a token.

    Args:
        settings (dict): Zerodha's credentials, which must contain api_key, api_secret, username, password and totp_secret.

    Returns:
        dict: The Zerodha access token, under the key "access_token".

    Raises:
        BrokerLoginError: If the login page does not redirect with a request token, or Zerodha returns no access token.
    """
    driver = start_headless_chrome()
    try:
        driver.get(f"https://kite.trade/connect/login?api_key={settings['api_key']}&v=3")
        time.sleep(PAGE_LOAD_PAUSE_SECONDS)
        driver.find_element(By.XPATH, '//*[@id="userid"]').send_keys(settings["username"])
        driver.find_element(By.XPATH, '//*[@id="password"]').send_keys(settings["password"])
        driver.find_element(By.XPATH, '//*[@id="container"]/div/div/div[2]/form/div[4]/button').click()
        time.sleep(PAGE_LOAD_PAUSE_SECONDS)
        driver.find_element(By.XPATH, '//*[@id="container"]/div[2]/div/div[2]/form/div[1]/input').send_keys(generate_one_time_password(settings["totp_secret"]))
        try:
            WebDriverWait(driver, REDIRECT_WAIT_SECONDS).until(lambda browser: "request_token=" in browser.current_url)
        except TimeoutException:
            raise BrokerLoginError(f"Zerodha did not redirect with a request token. The last page was {driver.current_url}.")
        request_token = parse_qs(urlparse(driver.current_url).query)["request_token"][0]
    finally:
        driver.quit()

    checksum = hashlib.sha256((settings["api_key"] + request_token + settings["api_secret"]).encode()).hexdigest()
    response = requests.post(
        "https://api.kite.trade/session/token",
        data={
            "api_key": settings["api_key"],
            "request_token": request_token,
            "checksum": checksum,
        },
        headers={
            "X-Kite-Version": "3",
            "User-Agent": "Kiteconnect-python/4.1.0",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code >= 300:
        raise BrokerLoginError(f"Zerodha would not exchange the request token, status {response.status_code}: {response.text}")
    access_token = response.json().get("data", {}).get("access_token")
    if access_token is None:
        raise BrokerLoginError(f"Zerodha returned no access token: {response.text}")
    return {"access_token": access_token}


BROKER_LOGINS = [
    ("dhan", login_to_dhan),
    ("flattrade", login_to_flattrade),
    ("fyers", login_to_fyers),
    ("groww", login_to_groww),
    ("indmoney", login_to_indmoney),
    ("kotak", login_to_kotak),
    ("shoonya", login_to_shoonya),
    ("stoxkart", login_to_stoxkart),
    ("wisdom_capital", login_to_wisdom_capital),
    ("zerodha", login_to_zerodha),
]


def log_in_to_brokers(broker_names, force):
    """
    Log in to each named broker in turn and store the access tokens, carrying on past any broker that fails.

    Args:
        broker_names (list): Names of the brokers to log in to, in the order they should be attempted.
        force (bool): Log in again even when the broker already has a token issued today.

    Returns:
        list: One tuple of broker name, outcome and detail per broker, where the outcome is "logged in", "skipped" or "failed".
    """
    mongodb_database = open_mongodb_database()
    login_functions = dict(BROKER_LOGINS)
    results = []

    for broker_name in broker_names:
        if not force and logged_in_today(mongodb_database, broker_name):
            results.append((broker_name, "skipped", "already has a token issued today"))
            continue
        try:
            settings = read_broker_settings(mongodb_database, broker_name)
            login_details = login_functions[broker_name](settings)
            save_last_login(mongodb_database, broker_name, login_details)
            results.append((broker_name, "logged in", f"token of {len(login_details['access_token'])} characters"))
        except Exception as failure:
            results.append((broker_name, "failed", str(failure)))

    return results


def main():
    """
    Log in to the brokers named on the command line, or to every broker when none are named, and report what happened.

    Args:
        None.

    Returns:
        int: Zero when every attempted broker logged in or was skipped, and one when any broker failed.
    """
    known_broker_names = [broker_name for broker_name, login_function in BROKER_LOGINS]
    parser = argparse.ArgumentParser(description="Log in to the brokers and store their access tokens in MongoDB.")
    parser.add_argument("--brokers", nargs="+", choices=known_broker_names, default=known_broker_names, help="Brokers to log in to. Every broker is attempted when this is omitted.")
    parser.add_argument("--force", action="store_true", help="Log in again even for a broker that already has a token issued today.")
    arguments = parser.parse_args()

    results = log_in_to_brokers(arguments.brokers, arguments.force)

    name_width = max(len(broker_name) for broker_name, outcome, detail in results)
    for broker_name, outcome, detail in results:
        print(f"{broker_name.ljust(name_width)}  {outcome.ljust(9)}  {detail}")

    failures = [broker_name for broker_name, outcome, detail in results if outcome == "failed"]
    if failures:
        print()
        print(f"{len(failures)} of {len(results)} brokers failed to log in: {', '.join(failures)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
