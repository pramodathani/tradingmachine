import os
import sys
import csv
import json
import time
import redis
import pyotp
import struct
import pymongo
import hashlib
import logging
import requests
import threading
import websocket
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import *
from selenium.webdriver.common.by import By
from urllib.parse import urlparse, parse_qs

from util.config import *
from brokers.exceptions import *

class ZerodhaRestAPI:
    """
    ZerodhaRestAPI class provides standard GET, POST, PUT and DELETE Rest API functionality to interact with Zerodha KiteConnect API server.
    """

    number_of_rest_api_calls = 0
    number_of_order_api_calls = 0
    quote_api_calls = []
    historical_api_calls = []
    order_api_calls = []
    other_api_calls = []

    def __init__(self):
        logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
        self._logger = logging.getLogger()

        self._cache = redis.Redis(host=redis_config['host'], port=redis_config['port'], password=redis_config['password'], db=redis_config['db'], decode_responses=True, encoding='utf-8')
        self._mongo_client = pymongo.MongoClient(mongodb_config['connection_string'])
        self._mongo_db = self._mongo_client[mongodb_config['db']]

        if not self._cache.exists('zerodha_settings'):
            self._logger.warning(msg="Zerodha Settings not found in cache. Creating a new one.")
            settings = self._mongo_db['zerodha_settings'].find_one({}, {'_id': 0})
            self._cache.set('zerodha_settings', json.dumps(settings))

        if not self._cache.exists('zerodha_last_login'):
            self._logger.warning(msg="Zerodha last login not found in cache. Creating a new one.")
            last_login = self._mongo_db['zerodha_last_login'].find_one({}, {'_id': 0})
            self._cache.set('zerodha_last_login', json.dumps(last_login))

        settings = json.loads(self._cache.get('zerodha_settings'))
        last_login = json.loads(self._cache.get('zerodha_last_login'))

        self._username = settings['username']
        self._password = settings['password']
        self._api_key = settings['api_key']
        self._api_secret = settings['api_secret']
        self._totp_secret = settings['totp_secret']
        self._timeout = int(settings['timeout'])
        self._proxies = {}
        self._allow_redirects = settings['allow_redirects']
        self._verify = settings['verify']

        self._access_token = last_login['access_token']
        self._last_login_date = last_login['last_login_date']

        self._login_url = f'https://kite.trade/connect/login?api_key={self._api_key}&v=3'

        self._headers = {
            "X-Kite-Version": "3",
            "User-Agent": "Kiteconnect-python/4.1.0",
            "Authorization": f"token {self._api_key}:{self._access_token}"
        }
        
    def __request(self, method, url, parameters=None, data=None, json_data=None, headers=None, verbose=False):
        """
        Private generic REST API request to Zerodha KiteConnect API server.
        This is specialized into GET, POST, PUT and DELETE by public methods.

        - `method`: HTTP method to use for the request.
        - `url`: URL of the API endpoint.
        - `parameters`: Dictionary of parameters to be sent as part of the request.
        - `data`: Dictionary, bytes, or file-like object to send in the body of the request.
        - `json_data`: JSON data to send in the body of the request.
        - `headers`: Dictionary of HTTP headers to be sent with the request.
        - `verbose`: If set to True, the request and response are logged.
        """
        last_login = json.loads(self._cache.get('zerodha_last_login'))
        
        self._access_token = last_login['access_token']
        self._headers = {
            "X-Kite-Version": "3",
            "User-Agent": "Kiteconnect-python/4.1.0",
            "Authorization": f"token {self._api_key}:{self._access_token}"
        }

        if headers is None:
            headers = self._headers

        try:
            if verbose == True:
                self._logger.info(f"method={method}, url={url}, parameters={parameters}, data={data}, json_data={json_data}, headers={headers}, timeout={self._timeout}, proxies={self._proxies}, allow_redirects={self._allow_redirects}, verify={self._verify}")


            # The following sections implement the rate limiting for different types of API calls
            # The rate limiting is implemented by sleeping for the remaining time in the current second to ensure that the rate limit is not exceeded
            # The rate limit for different types of API calls is as follows:
            # 1. Quote API calls: 1 per second
            # 2. Historical API calls: 3 per second
            # 3. Order API calls: 10 per second
            # 4. Other API calls: 10 per second
            

            if '/quote' in url:
                if len(self.quote_api_calls) > 0:
                    first_call_time = self.quote_api_calls[0]
                    time_now = time.time()
                    time_diff = time_now - first_call_time
                    if (len(self.quote_api_calls) >= 1) and (time_diff < 1):
                        time.sleep(1 - time_diff)
                        if verbose == True:
                            self._logger.info(f"First call time: {first_call_time}, Time now: {time_now}, Time diff: {time_diff}, Sleep time: {1 - time_diff}, Length of quote_api_calls: {len(self.quote_api_calls)}, Quote API calls: {self.quote_api_calls}")
                        self.quote_api_calls = []

                self.quote_api_calls.append(time.time())
                

            elif '/historical' in url or '/instruments' in url:
                if len(self.historical_api_calls) > 0:
                    first_call_time = self.historical_api_calls[0]
                    time_now = time.time()
                    time_diff = time_now - first_call_time
                    if (len(self.historical_api_calls) >= 3) and (time_diff < 1):
                        time.sleep(1 - time_diff)
                        if verbose == True:
                            self._logger.info(f"First call time: {first_call_time}, Time now: {time_now}, Time diff: {time_diff}, Sleep time: {1 - time_diff}, Length of historical_api_calls: {len(self.historical_api_calls)}, Historical API calls: {self.historical_api_calls}")
                        self.historical_api_calls = []

                self.historical_api_calls.append(time.time())
                

            elif '/orders' in url or '/trades' in url:
                if len(self.order_api_calls) > 0:
                    first_call_time = self.order_api_calls[0]
                    time_now = time.time()
                    time_diff = time_now - first_call_time
                    if (len(self.order_api_calls) >= 10) and (time_diff < 1):
                        time.sleep(1 - time_diff)
                        if verbose == True:
                            self._logger.info(f"First call time: {first_call_time}, Time now: {time_now}, Time diff: {time_diff}, Sleep time: {1 - time_diff}, Length of order_api_calls: {len(self.order_api_calls)}, Order API calls: {self.order_api_calls}")
                        self.order_api_calls = []

                self.order_api_calls.append(time.time())


            else:
                if len(self.other_api_calls) > 0:
                    first_call_time = self.other_api_calls[0]
                    time_now = time.time()
                    time_diff = time_now - first_call_time
                    if (len(self.other_api_calls) >= 10) and (time_diff < 1):
                        time.sleep(1 - time_diff)
                        if verbose == True:
                            self._logger.info(f"First call time: {first_call_time}, Time now: {time_now}, Time diff: {time_diff}, Sleep time: {1 - time_diff}, Length of other_api_calls: {len(self.other_api_calls)}, Other API calls: {self.other_api_calls}")
                        self.other_api_calls = []

                self.other_api_calls.append(time.time())
                
            self.number_of_rest_api_calls += 1
            self._cache.set('number_of_zerodha_api_calls', self.number_of_rest_api_calls)
            self._cache.rpush('zerodha_api_calls', f"{datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f")} - {self.number_of_rest_api_calls} - request.request(method='{method}', url='{url}', parameters='{parameters}', data='{data}', json_data='{json_data}', headers='{headers}', timeout='{self._timeout}, proxies={self._proxies}, allow_redirects={self._allow_redirects}, verify={self._verify}')")
            if '/orders' in url:
                self.number_of_order_api_calls += 1
                self._cache.set('number_of_zerodha_order_api_calls', self.number_of_order_api_calls)

            response = requests.request(method=method,
                                        url=url,
                                        params=parameters,
                                        data=data,
                                        json=json_data,
                                        headers=headers,
                                        timeout=self._timeout,
                                        proxies=self._proxies,
                                        allow_redirects=self._allow_redirects,
                                        verify=self._verify)
        except Exception as e:
            raise e

        if response.status_code == 200 and 'json' in response.headers['content-type']:
            content = response.json()
            content['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            return content

        elif response.status_code == 200 and 'csv' in response.headers['content-type']:
            data = response.content.decode('utf-8').strip()
            return data

        elif response.status_code != 200 and 'json' in response.headers['content-type']:
            content = response.json()
            content['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

            if content['status'] == 'error':
                if content['error_type'] == 'InputException':
                    raise InputException(message=content['message'], code=response.status_code)
                elif content['error_type'] == 'DataException':
                    raise DataException(message=content['message'], code=response.status_code)
                elif content['error_type'] == 'NetworkException':
                    raise NetworkException(message=content['message'], code=response.status_code)
                elif content['error_type'] == 'GeneralException':
                    raise GeneralException(message=content['message'], code=response.status_code)
                elif content['error_type'] == 'UserException':
                    raise UserException(message=content['message'], code=response.status_code)
                elif content['error_type'] == 'TokenException':
                    raise TokenException(message=content['message'], code=response.status_code)
                elif content['error_type'] == 'PermissionException':
                    raise PermissionException(message=content['message'], code=response.status_code)
                elif content['error_type'] == 'OrderException':
                    raise OrderException(message=content['message'], code=response.status_code)

        e = Exception()
        raise e

    def get(self, url, parameters=None, data=None, json_data=None, headers=None, verbose=False):
        """
        HTTP GET Rest API call to Zerodha KiteConnect API server.
        This queries the Zerodha KiteConnect for some information. Most responses are JSON encoded. Only a few are CSV encoded.

        - `url`: URL of the API endpoint.
        - `parameters`: Dictionary of parameters to be sent as part of the request.
        - `data`: Dictionary, bytes, or file-like object to send in the body of the request.
        - `json_data`: JSON data to send in the body of the request.
        - `headers`: Dictionary of HTTP headers to be sent with the request.
        - `verbose`: If set to True, the request and response are logged.
        """
        data = self.__request(method="GET", url=url, parameters=parameters, data=data, json_data=json_data, headers=headers, verbose=verbose)
        return data

    def post(self, url, parameters=None, data=None, json_data=None, headers=None, verbose=False):
        """
        HTTP POST Rest API call to Zerodha KiteConnect API server.
        This carries out some action using Zerodha KiteConnect such as placing an order. Responses are JSON encoded.

        - `url`: URL of the API endpoint.
        - `parameters`: Dictionary of parameters to be sent as part of the request.
        - `data`: Dictionary, bytes, or file-like object to send in the body of the request.
        - `json_data`: JSON data to send in the body of the request.
        - `headers`: Dictionary of HTTP headers to be sent with the request.
        - `verbose`: If set to True, the request and response are logged.
        """
        data = self.__request(method="POST", url=url, parameters=parameters, data=data, json_data=json_data, headers=headers, verbose=verbose)
        return data

    def put(self, url, parameters=None, data=None, json_data=None, headers=None, verbose=False):
        """
        HTTP PUT Rest API call to Zerodha KiteConnect API server.
        This modifies something using Zerodha KiteConnect such as modifying an order. Responses are JSON encoded.

        - `url`: URL of the API endpoint.
        - `parameters`: Dictionary of parameters to be sent as part of the request.
        - `data`: Dictionary, bytes, or file-like object to send in the body of the request.
        - `json_data`: JSON data to send in the body of the request.
        - `headers`: Dictionary of HTTP headers to be sent with the request.
        - `verbose`: If set to True, the request and response are logged.
        """
        data = self.__request(method="PUT", url=url, parameters=parameters, data=data, json_data=json_data, headers=headers, verbose=verbose)
        return data

    def delete(self, url, parameters=None, data=None, json_data=None, headers=None, verbose=False):
        """
        HTTP DELETE Rest API call to Zerodha KiteConnect API server.
        This deletes something using Zerodha KiteConnect such as cancelling an order or invalidating an access token. Responses are JSON encoded.

        - `url`: URL of the API endpoint.
        - `parameters`: Dictionary of parameters to be sent as part of the request.
        - `data`: Dictionary, bytes, or file-like object to send in the body of the request.
        - `json_data`: JSON data to send in the body of the request.
        - `headers`: Dictionary of HTTP headers to be sent with the request.
        - `verbose`: If set to True, the request and response are logged.
        """
        data = self.__request(method="DELETE", url=url, parameters=parameters, data=data, json_data=json_data, headers=headers, verbose=verbose)
        return data


    def _get_request_token(self):
        """
        Private method to get request token from Zerodha KiteConnect API server.
        """
        try:
            self._logger.info(msg="Getting request token from Zerodha Kite trading platform.")
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            driver = Chrome(options=chrome_options)
            driver.get(self._login_url)
            time.sleep(2)
            self._logger.info(msg="started the chrome driver")

            # Enter user name and password using selenium webdriver on the loging page
            txt_user_name = driver.find_element(By.XPATH, r'//*[@id="userid"]')
            txt_password = driver.find_element(By.XPATH, r'//*[@id="password"]')
            btn_login = driver.find_element(By.XPATH, r'//*[@id="container"]/div/div/div[2]/form/div[4]/button')

            txt_user_name.send_keys(self._username)
            txt_password.send_keys(self._password)
            btn_login.click()

            time.sleep(2)

            # Enter OTP. Entering full OTP implicitly clicks 'Continue' button on the OTP page
            txt_totp = driver.find_element(By.XPATH, r'//*[@id="container"]/div[2]/div/div[2]/form/div[1]/input')
            totp = pyotp.TOTP(self._totp_secret).now()
            txt_totp.send_keys(str(totp))
            time.sleep(5)

            # We get the request token back from zerodha in a url
            parsed_url = urlparse(driver.current_url)
            request_token = parse_qs(parsed_url.query)['request_token'][0]
            driver.quit()

            return request_token

        except NoSuchElementException as nsee:
            raise ZerodhaException("Cannot find the form elements in kite login page for authentication.")

        except WebDriverException as wde:
            raise ZerodhaException("Cannot start selenium webdriver for authentication.")

    def _get_access_token(self, request_token):
        """
        Given a request token, retrieve the access token from the Zerodha Kite trading platform

        - `request_token` - Request token obtained from the Zerodha Kite trading platform after login flow
        """
        h = hashlib.sha256(self._api_key.encode("utf-8") + request_token.encode("utf-8") + self._api_secret.encode("utf-8"))
        checksum = h.hexdigest()
        
        url = "https://api.kite.trade/session/token"
        headers = {"X-Kite-Version": "3", "User-Agent": "Kiteconnect-python/4.1.0"}
        data = {
            "api_key": self._api_key, 
            "request_token": request_token, 
            "checksum": checksum
        }
        
        data = self.post(url=url, data=data, headers=headers)['data']
        
        if 'access_token' in data:
            # We got an access token from Zerodha KiteConnect server.
            # Let's store it in 'last_login' mongodb collection and redis key and reuse it during the day to make REST api calls directly.

            self._access_token = data['access_token']
            self._last_login_date = data['login_time']
            last_login = {'access_token': self._access_token, 'last_login_date': self._last_login_date}

            # Store the access token in 'last_login' mongodb collection and redis key
            self._cache.set('zerodha_last_login', json.dumps(last_login))
            self._mongo_db['zerodha_last_login'].delete_many({})
            self._mongo_db['zerodha_last_login'].insert_one(last_login)
            
            return self._access_token
        
        else:
            raise ZerodhaException("Cannot get access token from Zerodha KiteConnect server.")


    def connect(self):
        """
        Connect to the Zerodha Kite trading platform
        """        
        try:
            # Check whether the stored access token is still valid, if not, get a new access_token
            self.get(url="https://api.kite.trade/user/profile")['data']
            self._logger.info(msg="Logged in successfully.")
        except Exception as e:
            self._logger.warning(msg="Access token expired. Getting a new access token.")
            try:
                request_token = self._get_request_token()
                self._get_access_token(request_token = request_token)
                self._logger.info(msg="Logged in successfully.")
            except Exception as e:
                raise ZerodhaException("Cannot login to Zerodha Kite trading platform.")

    def disconnect(self):
        """
        Disconnect from the Zerodha Kite trading platform
        """        
        try:
            parameters={'api_key':self._api_key, 'access_token':self._access_token}
            status = self.delete(url="https://api.kite.trade/session/token", parameters=parameters)['data']
            return status
        except TokenException as te:
            self._logger.warning(msg="Already disconnected.")    

class ZerodhaWebSocket:
    """
    Zerodha Kite Connect websocket.
    """

    _EXCHANGE_MAP = {
        "nse": 1,
        "nfo": 2,
        "cds": 3,
        "bse": 4,
        "bfo": 5,
        "bcd": 6,
        "mcx": 7,
        "mcxsx": 8,
        "indices": 9,
        "bsecds": 6
    }

    def __init__(self, name, instrument_tokens):
        """
        Kite websocket app.

        - `name` is the name of the websocket.
        - `instrument_tokens` is the list of instrument tokens.
        """
        logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
        self._logger = logging.getLogger()

        self._logger.info(f"Initializing websocket {name}.")        
        self._mongo_client = pymongo.MongoClient(mongodb_config['connection_string'])        
        self._mongo_db = self._mongo_client[mongodb_config['db']]
        self._cache = redis.Redis(host=redis_config['host'], port=redis_config['port'], db=redis_config['db'], password=redis_config['password'])
        
        self._logger.info("Fetching settings from cache.")
        settings = self._mongo_db['zerodha_settings'].find_one({}, {'_id': 0})
        self._cache.set('zerodha_settings', json.dumps(settings))
        
        self._settings = json.loads(self._cache.get('zerodha_settings'))
        self._last_login = json.loads(self._cache.get('zerodha_last_login'))

        self._api_key = self._settings['api_key']
        self._access_token = self._last_login['access_token']

        self._instruments = self._cache.hgetall('zerodha_instruments')
        self._instruments = [json.loads(value.decode('utf-8')) for key, value in self._instruments.items()]
        self._instruments = pd.DataFrame(self._instruments)

        self._instruments_map = self._cache.hgetall('zerodha_instruments_map')
        self._instruments_map = {key.decode('utf-8'): value.decode('utf-8') for key, value in self._instruments_map.items()}

        self._name = name        
        self._instrument_tokens = instrument_tokens

    def _unpack_int(self, bin, start, end, byte_format="I"):
        """Unpack binary data as unsgined interger."""
        return struct.unpack(">" + byte_format, bin[start:end])[0]

    def split_packets(self, data):
        """Split packets from binary data."""
        if len(data) < 2:
            return {}

        number_of_packets = self._unpack_int(data, 0, 2, byte_format="H")
        packets = {}

        j = 2
        for i in range(number_of_packets):
            packet_length = self._unpack_int(data, j, j+2, byte_format="H")
            packet = data[j+2:j+2+packet_length]
            instrument_token = self._unpack_int(packet, 0, 4)
            id = self._instruments_map[str(instrument_token)]
            packets[id] = packet.hex()
            j += 2 + packet_length        
        return packets


    def on_open(self, ws):
        """
        On websocket open.
        
        - `ws` is the websocket object.
        """        
        self._logger.info("Websocket opened.")
        ws.send(json.dumps({"a": "subscribe", "v": self._instrument_tokens}))
        ws.send(json.dumps({"a": "mode", "v": ["full", self._instrument_tokens]}))

    def on_close(self, ws):
        """
        On websocket close.
        
        - `ws` is the websocket object.
        """        
        self._logger.info("Websocket closed.")

    def on_ping(self, ws):
        """
        On websocket ping.
        
        - `ws` is the websocket object.
        """        
        self._logger.info("Websocket pinged.")

    def on_pong(self, ws):
        """
        On websocket pong.
        
        - `ws` is the websocket object.
        """        
        self._logger.info("Websocket ponged.")

    def on_error(self, ws, error):
        """
        On websocket error.
        
        - `ws` is the websocket object.
        - `error` is the error received.
        """
        self._logger.error(f"Error received: {error}")

    def on_message(self, ws, message):
        """
        On websocket message.
        
        - `ws` is the websocket object.
        - `message` is the message received.
        """
        start_time = time.time()
        
        if not isinstance(message, bytes):
            return None

        packets = self.split_packets(message)
        if len(packets) == 0:
            return None

        self._cache.hmset('market_data', packets)

        quotes = list(packets.values())
        self._cache.lpush(f"quotes_{self._name}", *quotes)

        end_time = time.time()
        self._logger.info(f"{self._name} \t {len(message)} \t {len(packets)} \t {int((end_time - start_time)*1000)} ms.")        
        
    def run_forever(self):
        """
        Run websocket forever.
        """
        ws = websocket.WebSocketApp(
            f"wss://ws.kite.trade/?api_key={self._api_key}&access_token={self._access_token}", 
            on_open=self.on_open, 
            on_message=self.on_message, 
            on_error=self.on_error, 
            on_close=self.on_close, 
            on_ping=self.on_ping, 
            on_pong=self.on_pong
        )

        ws.run_forever()

class ZerodhaWebSocketServer:
    """
    Websocket server.
    """

    def __init__(self, numbers_of_securities_per_thread=3000):
        """
        Websocket server.
        """
        self._cache = redis.Redis(host=redis_config['host'], port=redis_config['port'], db=redis_config['db'], password=redis_config['password'])
        
        self._instruments = self._cache.hgetall('zerodha_instruments')
        self._instruments = [json.loads(value.decode('utf-8')) for key, value in self._instruments.items()]
        self._instruments = pd.DataFrame(self._instruments)
        
        # Exclude MCX instruments
        self._instruments = self._instruments[self._instruments['exchange'] != 'MCX']
        
        self._numbers_of_securities_per_thread = numbers_of_securities_per_thread
        nrows = self._instruments.shape[0]
        self._number_of_threads = nrows//numbers_of_securities_per_thread + 1
        

    def run_all_websockets(self):
        """
        Spawn websockets.
        """
        for i in range(self._number_of_threads):
            print(f"starting thread {i} of {self._number_of_threads}")
            batch = self._instruments.iloc[i*self._numbers_of_securities_per_thread:(i+1)*self._numbers_of_securities_per_thread, :]
            batch.reset_index(inplace=True, drop=True)

            instrument_tokens = batch['instrument_token'].tolist()
            web_socket = ZerodhaWebSocket(name=f"socket_{i}", instrument_tokens=instrument_tokens)

            web_socket_thread = threading.Thread(target=web_socket.run_forever, args=())
            web_socket_thread.start()
