import os
import sys
import csv
import json
import threading
import time
import redis
import pyotp
import struct
import urllib
import pymongo
import hashlib
import logging
import requests
import websocket
import webbrowser
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import *
from selenium.webdriver.common.by import By
from urllib.parse import urlparse, parse_qs

from util.config import *

class FyersRestAPI:
    """
    FyersRestAPI class provides standard GET, POST, PATCH and DELETE methods to interact with Fyers REST API server.
    """
    
    number_of_rest_api_calls = 0
    number_of_order_api_calls = 0
    quote_api_calls = []
    historical_api_calls = []
    order_api_calls = []
    other_api_calls = []

    def __init__(self):
        """
        FyersRestAPI class provides standard GET, POST, PUT and DELETE methods to interact with Fyers REST API server.
        """
        logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
        self._logger = logging.getLogger()

        self._cache = redis.Redis(host=redis_config['host'], port=redis_config['port'], db=redis_config['db'], password=redis_config['password'], decode_responses=True, encoding='utf-8')
        self._mongo_client = pymongo.MongoClient(mongodb_config['connection_string'])
        self._mongo_db = self._mongo_client[mongodb_config['db']]

        if not self._cache.exists('fyers_settings'):
            self._logger.warning(msg="Fyers Settings not found in cache. Creating a new one.")
            settings = self._mongo_db['fyers_settings'].find_one({}, {'_id': 0})
            self._cache.set('fyers_settings', json.dumps(settings))

        if not self._cache.exists('fyers_last_login'):
            self._logger.warning(msg="Fyers last login not found in cache. Creating a new one.")
            last_login = self._mongo_db['fyers_last_login'].find_one({}, {'_id': 0})
            self._cache.set('fyers_last_login', json.dumps(last_login))

        settings = json.loads(self._cache.get('fyers_settings'))
        last_login = json.loads(self._cache.get('fyers_last_login'))
        
        self._client_id = settings['client_id']
        self._app_id = settings['app_id']
        self._secret_id = settings['secret_id']
        self._pin = settings['pin']
        self._mobile = settings['kyc']['mobile']
        self._email = settings['kyc']['email']
        self._pan = settings['kyc']['pan']
        self._date_of_birth = settings['kyc']['date_of_birth']
        self._gender = settings['kyc']['gender']
        self._demat_account_number = settings['demat']['account_number']
        self._depository = settings['demat']['depository']
        self._dp_id = settings['demat']['dp_id']        
        self._bo_id = settings['demat']['bo_id']
        self._bank_name = settings['bank']['name']
        self._bank_account_number = settings['bank']['account_no']        
        self._bank_account_type = settings['bank']['type']
        self._bank_micr = settings['bank']['micr']
        self._ifsc = settings['bank']['ifsc']
        
        self._scope = None
        self._nonce = None
        
        self._login_url = f"https://api-t1.fyers.in/api/v3/generate-authcode?client_id={self._app_id}&redirect_uri=http%3A%2F%2Flocalhost&response_type=code&state=sample"
        
        self._access_token = last_login['access_token']
        
        self._headers = {
            'Authorization': f'{self._app_id}:{self._access_token}',
            'Content-Type': 'application/json',
            'version': '3'                
        }
  
    def get(self, url, data=None):
        """
        Standard GET method to interact with Fyers REST API server.
        """
        if data is not None:
            url_parameters = urllib.parse.urlencode(data)
            url = f"{url}?{url_parameters}"
        try:
            response = requests.get(url, headers=self._headers)
        except Exception as e:
            self._logger.error(msg=f"GET request to {url} failed: {str(e)}")
            return None
        
        if response.status_code == 200 and 'json' in response.headers['content-type']:
            return response.json()
        else:
            self._logger.error(msg=f"GET request to {url} failed with status code {response.status_code}: {response.text}")
            return None
        
    def post(self, url, data=None):
        """
        Standard POST method to interact with Fyers REST API server.
        """
        try:
            response = requests.post(url, headers=self._headers, data=json.dumps(data))
        except Exception as e:
            self._logger.error(msg=f"POST request to {url} failed: {str(e)}")
            return None
        
        if response.status_code == 200 and 'json' in response.headers['content-type']:
            return response.json()
        else:
            self._logger.error(msg=f"POST request to {url} failed with status code {response.status_code}: {response.text}")
            return None
        
    def patch(self, url, data=None):
        """
        Standard PATCH method to interact with Fyers REST API server.
        """
        try:
            response = requests.patch(url, headers=self._headers, data=json.dumps(data))
        except Exception as e:
            self._logger.error(msg=f"PATCH request to {url} failed: {str(e)}")
            return None
        
        if response.status_code == 200 and 'json' in response.headers['content-type']:
            return response.json()
        else:
            self._logger.error(msg=f"PATCH request to {url} failed with status code {response.status_code}: {response.text}")
            return None

    def delete(self, url, data=None):
        """
        Standard DELETE method to interact with Fyers REST API server.
        """
        try:
            response = requests.delete(url, headers=self._headers, data=json.dumps(data))
        except Exception as e:
            self._logger.error(msg=f"DELETE request to {url} failed: {str(e)}")
            return None
        
        if response.status_code == 200 and 'json' in response.headers['content-type']:
            return response.json()
        else:
            self._logger.error(msg=f"DELETE request to {url} failed with status code {response.status_code}: {response.text}")
            return None
