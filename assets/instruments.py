import csv
import json
import zlib
import time
import math
import redis
import struct
import pickle
import logging
import pymongo
import websocket
import threading
import numpy as np
import pandas as pd
import talib as ta
import opstrat as op
import backtesting
import backtesting.lib
import backtesting.test

from six import StringIO
from dateutil.relativedelta import *
from datetime import datetime, timedelta

from brokers.zerodha import *
from brokers.fyers import *
from assets.exceptions import *

class Instrument:
    """
    Instrument class encapsulates all the data and functionality related to a single instrument.
    """
    _cache = redis.Redis(host=redis_config['host'], port=redis_config['port'], db=redis_config['db'], password=redis_config['password'], decode_responses=True, encoding='utf-8')
    _historical_price_cache = redis.Redis(host=redis_config['host'], port=redis_config['port'], db=redis_config['db'], password=redis_config['password'])
    _zerodha_rest_api = ZerodhaRestAPI()
    _fyers_rest_api = FyersRestAPI()
    
    def __init__(self, id):
        """
        Instrument class encapsulates all the data and functionality related to a single instrument.

        - `id`: is the id of the instrument. This is of the format 'exchange:tradingsymbol'. For example, the id of the NIFTY 50 index is 'NFO:NIFTY 50'.
        """
        logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
        self._logger = logging.getLogger()
        
        self._id = id.upper()
        if not self._cache.hexists('zerodha_instruments', self._id):
            raise InstrumentException(message=f"Instrument not found in Zerodha instruments list: {self._id}")
        
        self._zerodha_instrument = json.loads(self._cache.hget('zerodha_instruments', self._id))
        if self._zerodha_instrument is None:
            raise InstrumentException(message=f"Instrument not found in Zerodha instruments list: {self._id}")
        
        # if not self._cache.hexists('fyers_instruments', self._id):
        #     raise InstrumentException(message=f"Instrument not found in Fyers instruments list: {self._id}")
        
        # self._fyers_instrument = json.loads(self._cache.hget('fyers_instruments', self._id))
        # if self._fyers_instrument is None:
        #     raise InstrumentException(message=f"Instrument not found in Fyers instruments list: {self._id}")
        
        self._zerodha_instrument = json.loads(self._cache.hget('zerodha_instruments', self._id))
        # self._fyers_instrument = json.loads(self._cache.hget('fyers_instruments', self._id))
        
    def __repr__(self):
        """
        Returns a string representation of the instrument.
        """
        return f"Instrument(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the instrument.
        """
        return f"Instrument(id=\"{self._id}\")"
        
    def __eq__(self, other):
        """
        Returns True if the instrument is equal to the other instrument.
        """
        return self._id == other._id
    
    def __ne__(self, other):
        """
        Returns True if the instrument is not equal to the other instrument.
        """
        return self._id != other._id
    
    def __hash__(self):
        """
        Returns the hash of the instrument.
        """
        return hash(self._id)
        
    @property
    def id(self):
        return self._id
    
    @property
    def zerodha_instrument(self):
        return self._zerodha_instrument
    
    @property
    def fyers_instrument(self):
        return self._fyers_instrument
    
    @property
    def instrument_token(self):
        return self._zerodha_instrument['instrument_token']
    
    @property
    def exchange_token(self):
        return self._zerodha_instrument['exchange_token']
    
    @property
    def tradingsymbol(self):
        return self._zerodha_instrument['tradingsymbol']
    
    @property
    def name(self):
        return self._zerodha_instrument['name']
    
    @property
    def tick_size(self):
        return self._zerodha_instrument['tick_size']
    
    @property
    def expiry(self):
        return self._zerodha_instrument['expiry']
    
    @property
    def lot_size(self):
        return self._zerodha_instrument['lot_size']
    
    @property
    def instrument_type(self):
        return self._zerodha_instrument['instrument_type']
    
    @property
    def segment(self):
        return self._zerodha_instrument['segment']
    
    @property
    def exchange(self):
        return self._zerodha_instrument['exchange']
    
    @property
    def fyers_token(self):
        return self._fyers_instrument['token']
    
    @property
    def isin(self):
        return self._fyers_instrument['ISIN']
    
    @property
    def trade_session_timings(self):
        return self._fyers_instrument['Trading Session']

    
    # historical prices and technical indicators

    def _get_date_ranges(self, from_date, to_date, interval):
        """
        Get the date ranges for the required interval.
        
        - `from_date`: is the start date of the date range.
        - `to_date`: is the end date of the date range.
        - `interval`: is the interval of the date range.
        """
        # this code needs refactoring.

        interval = interval.lower()
        interval_mapping = {'day': 2000, '60minute': 400, '30minute': 200, '15minute': 200, '10minute': 100, '5minute': 100, '3minute': 100, 'minute': 60}
        delta = interval_mapping[interval]
        
        date_ranges = []
        from_date = datetime.strptime(from_date, "%Y-%m-%d %H:%M:%S")
        to_date = datetime.strptime(to_date, "%Y-%m-%d %H:%M:%S")

        start_date = from_date
        end_date = start_date + timedelta(days=delta)
        while end_date <= to_date:
            date_ranges.append({'from_date':start_date, 'to_date':end_date})
            start_date = end_date + timedelta(days=1)
            end_date = start_date + timedelta(days=delta)
        
        if end_date > to_date:
            date_ranges.append({'from_date':start_date, 'to_date':to_date})

        date_ranges1 = []
        for i in range(0, len(date_ranges)):
            if date_ranges[i]['from_date'] <= date_ranges[i]['to_date']:
                date_ranges1.append(date_ranges[i])

        date_ranges = date_ranges1

        date_ranges = pd.DataFrame(date_ranges)
        date_ranges = date_ranges.sort_values('from_date', ascending=False)
        date_ranges = date_ranges.to_dict('records')
        return date_ranges
    
    def get_historical_prices(self, from_date, to_date, interval='day', continuous=False, open_interest=False):
        """
        Get historical prices for an instrument.

        - `from_date`: Start date.
        - `to_date`: End date.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `continuous`: If true, then the data points are returned in a continuous format.
        - `open_interest`: If true, then the data points are returned with open interest.
        """
        exchange = self.exchange
        tradingsymbol = self.tradingsymbol

        date_ranges = self._get_date_ranges(from_date, to_date, interval)
        
        instrument_token = self.instrument_token
        
        if instrument_token is None:
            raise InstrumentException("Instrument not found in the instruments history file.")
        
        prices = []
        for period in date_ranges:
            from_date = period['from_date'].strftime("%Y-%m-%d %H:%M:%S")
            to_date = period['to_date'].strftime("%Y-%m-%d %H:%M:%S")
            try:
                parameters = {
                    'from': from_date,
                    'to': to_date,
                    'interval': interval,
                    'continuous': 1 if continuous else 0,
                    'oi': 1 if open_interest else 0
                }
                price_data = self._zerodha_rest_api.get(url=f"https://api.kite.trade/instruments/historical/{instrument_token}/{interval}", parameters=parameters)['data']
                time.sleep(0.3)
            
                if price_data is not None and 'candles' in price_data and len(price_data['candles']) > 0:
                    for candle_data in price_data['candles']:
                        timestamp = candle_data[0]
                        timestamp = timestamp.split('T')[0]+' '+timestamp.split('T')[1].split('+')[0]  # remove timezone
                        open_price = candle_data[1]
                        high_price = candle_data[2]
                        low_price = candle_data[3]
                        close_price = candle_data[4]
                        volume = candle_data[5]
                        candle = {
                            'exchange': exchange, 
                            'tradingsymbol': tradingsymbol, 
                            'interval': interval, 
                            'datetime': timestamp, 
                            'open': open_price, 
                            'high': high_price, 
                            'low': low_price, 
                            'close': close_price, 
                            'volume': volume
                        }
                        prices.append(candle)
            except Exception as ue:
                print(str(ue))
                time.sleep(0.3)
                continue
        if len(prices) == 0:
            return None

        prices = pd.DataFrame(prices)
        prices = prices.sort_values(['datetime','interval','exchange','tradingsymbol'], ascending=True)
        return prices        

    def prices(self, period='one_month', interval='day'):
        """
        Get prices for an instrument.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        if period == 'one_day':
            from_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = datetime.now()
        elif period == 'two_days':
            from_date = datetime.now() - timedelta(days=2)
            from_date = from_date + timedelta(days=1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = datetime.now()
        elif period == 'three_days':
            from_date = datetime.now() - timedelta(days=3)
            from_date = from_date + timedelta(days=1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = datetime.now()
        elif period == 'one_week':
            from_date = datetime.now() - timedelta(weeks=1)
            from_date = from_date + timedelta(days=1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = datetime.now()
        elif period == 'two_weeks':
            from_date = datetime.now() - timedelta(weeks=2)
            from_date = from_date + timedelta(days=1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = datetime.now()
        elif period == 'one_month':
            from_date = datetime.now() - relativedelta(months=1)
            from_date = from_date + timedelta(days=1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = datetime.now()
        elif period == 'two_months':
            from_date = datetime.now() - relativedelta(months=2)
            from_date = from_date + timedelta(days=1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = datetime.now()
        elif period == 'three_months':
            from_date = datetime.now() - relativedelta(months=3)
            from_date = from_date + timedelta(days=1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = datetime.now()
        elif period == 'six_months':
            from_date = datetime.now() - relativedelta(months=6)
            from_date = from_date + timedelta(days=1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = datetime.now()
        elif period == 'one_year':
            from_date = datetime.now() - relativedelta(years=1)
            from_date = from_date + timedelta(days=1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = datetime.now()
        elif period == 'two_years':
            from_date = datetime.now() - relativedelta(years=2)
            from_date = from_date + timedelta(days=1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = datetime.now()
        elif period == 'three_years':
            from_date = datetime.now() - relativedelta(years=3)
            from_date = from_date + timedelta(days=1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = datetime.now()
        elif period == 'five_years':
            from_date = (datetime.now() - relativedelta(years=5))
            from_date = from_date+timedelta(days=1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = datetime.now()
        elif period == 'ten_years':
            from_date = (datetime.now() - relativedelta(years=10))
            from_date = from_date+timedelta(days=1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = datetime.now()
        elif period == 'maximum':
            from_date = datetime(1990, 1, 1)
            from_date = from_date+timedelta(days=1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = datetime.now()
        elif period == 'week_to_date':
            to_date = datetime.now()
            from_date = to_date - timedelta(days=to_date.weekday())
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'month_to_date':
            to_date = datetime.now()
            from_date = to_date - timedelta(days=to_date.day-1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'year_to_date':
            to_date = datetime.now()
            from_date = to_date - timedelta(days=to_date.timetuple().tm_yday-1)
            from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif len(period) == 42:
            from_date = datetime.strptime(period[0:19], "%Y-%m-%d %H:%M:%S")
            to_date = datetime.strptime(period[23:42], "%Y-%m-%d %H:%M:%S")
        else:
            raise InstrumentException("Invalid time period.")

        from_date = from_date.strftime("%Y-%m-%d %H:%M:%S")
        to_date = to_date.strftime("%Y-%m-%d %H:%M:%S")

        period_formatted = period.replace(':', '')
        period_formatted = period_formatted.replace(' ', '_')

        expiration_seconds = 5*60
        key = f"{self._id}:historical_prices:{period_formatted}:{interval}".upper()
        
        if not self._historical_price_cache.exists(key):
            historical_prices = self.get_historical_prices(from_date=from_date, to_date=to_date, interval=interval)
            if historical_prices is not None and not historical_prices.empty:
                self._historical_price_cache.setex(name=key, time=expiration_seconds, value=pickle.dumps(historical_prices))
        else:
            historical_prices = pickle.loads(self._historical_price_cache.get(key))

        return historical_prices
    
    def price_high(self, period='one_month', interval='day'):
        """
        Get highest price for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        return prices['high'].max()

    def price_low(self, period='one_month', interval='day'):
        """
        Get lowest price for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        return prices['low'].min()

    def price_mean(self, period='one_month', interval='day', column='close'):
        """
        Get mean price for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column to be used for mean calculation. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        return prices[column].mean()

    def price_median(self, period='one_month', interval='day', column='close'):
        """
        Get median price for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column to be used for median calculation. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        return prices[column].median()

    def price_standard_deviation(self, period='one_month', interval='day', column='close'):
        """
        Get standard deviation of prices for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column to be used for standard deviation calculation. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        return prices[column].std()

    def price_variance(self, period='one_month', interval='day', column='close'):
        """
        Get variance of prices for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column to be used for variance calculation. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        return prices[column].var()

    def price_mean_absolute_deviation(self, period='one_month', interval='day', column='close'):
        """
        Get mean absolute deviation of prices for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column to be used for mean absolute deviation calculation. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        return prices[column].mad()

    def price_skewness(self, period='one_month', interval='day', column='close'):
        """
        Get skewness of prices for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column to be used for skewness calculation. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        return prices[column].skew()

    def price_kurtosis(self, period='one_month', interval='day', column='close'):
        """
        Get kurtosis of prices for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column to be used for kurtosis calculation. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        return prices[column].kurtosis()

    def price_quantile(self, period='one_month', interval='day', quantile=0.5, column='close'):
        """
        Get quantile of prices for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `quantile`: Quantile for which price is required.
        - `column`: Column to be used for quantile calculation. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        return prices[column].quantile(quantile)

    def price_summary(self, period='one_month', interval='day', column='close'):
        """
        Get summary of prices for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}        
        """
        prices = self.prices(period=period, interval=interval)
        return prices[column].describe()

    def price_histogram(self, period='one_month', interval='day', bins=50, column='close'):
        """
        Get histogram of prices for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `bins`: Number of bins for histogram.
        """
        prices = self.prices(period=period, interval=interval)
        return prices[column].hist(bins=bins)

    def volumes(self, period='one_month', interval='day'):
        """
        Get volume traded for an instrument.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        vol = self.prices(period=period, interval=interval)
        vol = vol[['exchange', 'tradingsymbol', 'datetime', 'interval', 'volume']]
        return vol

    def volume_total(self, period='one_month', interval='day'):
        """
        Get total volume traded for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        volumes = self.volumes(period=period, interval=interval)
        return volumes['volume'].sum()

    def volume_high(self, period='one_month', interval='day'):
        """
        Get highest volume traded for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        volumes = self.volumes(period=period, interval=interval)
        return volumes['volume'].max()

    def volume_low(self, period='one_month', interval='day'):
        """
        Get lowest volume traded for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        volumes = self.volumes(period=period, interval=interval)
        return volumes['volume'].min()

    def volume_mean(self, period='one_month', interval='day'):
        """
        Get mean volume traded for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        volumes = self.volumes(period=period, interval=interval)
        return volumes['volume'].mean()

    def volume_median(self, period='one_month', interval='day'):
        """
        Get median volume traded for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        volumes = self.volumes(period=period, interval=interval)
        return volumes['volume'].median()

    def volume_standard_deviation(self, period='one_month', interval='day'):
        """
        Get standard deviation of volume traded for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        volumes = self.volumes(period=period, interval=interval)
        return volumes['volume'].std()

    def volume_variance(self, period='one_month', interval='day'):
        """
        Get variance of volume traded for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        volumes = self.volumes(period=period, interval=interval)
        return volumes['volume'].var()

    def volume_mean_absolute_deviation(self, period='one_month', interval='day'):
        """
        Get mean absolute deviation of volume traded for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        volumes = self.volumes(period=period, interval=interval)
        return volumes['volume'].mad()

    def volume_kurtosis(self, period='one_month', interval='day'):
        """
        Get kurtosis of volume traded for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        volumes = self.volumes(period=period, interval=interval)
        return volumes['volume'].kurtosis()

    def volume_skewness(self, period='one_month', interval='day'):
        """
        Get skewness of volume traded for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        volumes = self.volumes(period=period, interval=interval)
        return volumes['volume'].skew()

    def volume_quantile(self, period='one_month', interval='day', quantile=0.5):
        """
        Get quantile of volume traded for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `quantile`: Quantile for which volume is required.
        """
        volumes = self.volumes(period=period, interval=interval)
        return volumes['volume'].quantile(quantile)

    def volume_summary(self, period='one_month', interval='day'):
        """
        Get summary statistics of volume traded for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        volumes = self.volumes(period=period, interval=interval)
        return volumes['volume'].describe()

    def volume_histogram(self, period='one_month', interval='day', bins=50):
        """
        Get histogram of volume traded for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        volumes = self.volumes(period=period, interval=interval)
        return volumes['volume'].hist(bins=bins)



    def returns(self, period='one_month', interval='day', column='close'):
        """
        Get returns for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which returns are required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        prices['returns'] = prices[column].pct_change()
        prices = prices[['exchange', 'tradingsymbol', 'datetime', 'interval', 'returns']]
        return prices

    def returns_high(self, period='one_month', interval='day', column='close'):
        """
        Get highest return for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which returns are required. {'open', 'high', 'low', 'close', 'volume'}
        """
        returns = self.returns(period=period, interval=interval, column=column)
        return returns['returns'].max()

    def returns_low(self, period='one_month', interval='day', column='close'):
        """
        Get lowest return for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which returns are required. {'open', 'high', 'low', 'close', 'volume'}
        """
        returns = self.returns(period=period, interval=interval, column=column)
        return returns['returns'].min()

    def returns_mean(self, period='one_month', interval='day', column='close'):
        """
        Get mean return for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which returns are required. {'open', 'high', 'low', 'close', 'volume'}
        """
        returns = self.returns(period=period, interval=interval, column=column)
        return returns['returns'].mean()

    def returns_median(self, period='one_month', interval='day', column='close'):
        """
        Get median return for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which returns are required. {'open', 'high', 'low', 'close', 'volume'}
        """
        returns = self.returns(period=period, interval=interval, column=column)
        return returns['returns'].median()

    def returns_standard_deviation(self, period='one_month', interval='day', column='close'):
        """
        Get standard deviation of returns for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which returns are required. {'open', 'high', 'low', 'close', 'volume'}
        """
        returns = self.returns(period=period, interval=interval, column=column)
        return returns['returns'].std()

    def returns_variance(self, period='one_month', interval='day', column='close'):
        """
        Get variance of returns for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which returns are required. {'open', 'high', 'low', 'close', 'volume'}
        """
        returns = self.returns(period=period, interval=interval, column=column)
        return returns['returns'].var()

    def returns_mean_absolute_deviation(self, period='one_month', interval='day', column='close'):
        """
        Get mean absolute deviation of returns for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which returns are required. {'open', 'high', 'low', 'close', 'volume'}
        """
        returns = self.returns(period=period, interval=interval, column=column)
        return returns['returns'].mad()

    def returns_skewness(self, period='one_month', interval='day', column='close'):
        """
        Get skewness of returns for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which returns are required. {'open', 'high', 'low', 'close', 'volume'}
        """
        returns = self.returns(period=period, interval=interval, column=column)
        return returns['returns'].skew()

    def returns_kurtosis(self, period='one_month', interval='day', column='close'):
        """
        Get kurtosis of returns for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which returns are required. {'open', 'high', 'low', 'close', 'volume'}
        """
        returns = self.returns(period=period, interval=interval, column=column)
        return returns['returns'].kurt()

    def returns_quantile(self, period='one_month', interval='day', quantile=0.5, column='close'):
        """
        Get kurtosis of returns for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `quantile`: Quantile for which returns are required. {'open', 'high', 'low', 'close', 'volume'}
        """
        returns = self.returns(period=period, interval=interval, column=column)
        return returns['returns'].quantile(q = quantile)

    def returns_histogram(self, period='one_month', interval='day', column='close', bins=50):
        """
        Get histogram of returns for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which returns are required. {'open', 'high', 'low', 'close', 'volume'}
        """
        returns = self.returns(period=period, interval=interval, column=column)
        return returns['returns'].hist(bins=bins)

    def returns_summary(self, period='one_month', interval='day', column='close'):
        """
        Get summary of returns for a given period.

        - `period`: Period for which volumes are required.
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which returns are required. {'open', 'high', 'low', 'close', 'volume'}
        """
        returns = self.returns(period=period, interval=interval, column=column)
        return returns['returns'].describe()

    def simple_moving_average(self, period='one_month', interval='day', window=10, column='close'):
        """
        Get simple moving average for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating SMA.
        - `column`: Column name for which SMA is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        if prices is None or prices.empty:
            return None
        
        column_name = 'sma_' + str(window)
        prices[column_name] = ta.SMA(prices[column], timeperiod=window)
        return prices

    def exponential_moving_average(self, period='one_month', interval='day', window=10, column='close'):
        """
        Get exponential moving average for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating EMA.
        - `column`: Column name for which EMA is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'ema_' + str(window)
        prices[column_name] = ta.EMA(prices[column], timeperiod=window)
        return prices

    def weighted_moving_average(self, period='one_month', interval='day', window=10, column='close'):
        """
        Get weighted moving average for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating WMA.
        - `column`: Column name for which WMA is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'wma_' + str(window)
        prices[column_name] = ta.WMA(prices[column], timeperiod=window)
        return prices

    def double_exponential_moving_average(self, period='one_month', interval='day', window=10, column='close'):
        """
        Get double exponential moving average for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating DEMA.
        - `column`: Column name for which DEMA is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'dema_' + str(window)
        prices[column_name] = ta.DEMA(prices[column], timeperiod=window)
        return prices

    def triple_exponential_moving_average(self, period='one_month', interval='day', window=10, vfactor=0.7, column='close'):
        """
        Get triple exponential moving average for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating TEMA.
        - `vfactor`: Vfactor for calculating TEMA.
        - `column`: Column name for which TEMA is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 't3_' + str(window)
        prices[column_name] = ta.T3(prices[column], timeperiod=window, vfactor=vfactor)
        return prices

    def kaufman_adaptive_moving_average(self, period='one_month', interval='day', window=10, column='close'):
        """
        Get Kaufman adaptive moving average for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating KAMA.
        - `column`: Column name for which KAMA is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'kama_' + str(window)
        prices[column_name] = ta.KAMA(prices[column], timeperiod=window)
        return prices

    def mesa_adaptive_moving_average(self, period='one_month', interval='day', fastlimit=0.5, slowlimit=0.05, column='close'):
        """
        Get Mesa adaptive moving average for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating MAMA.
        - `column`: Column name for which MAMA is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name1 = 'mama'
        column_name2 = 'fama'
        prices[column_name1], prices[column_name2] = ta.MAMA(prices[column], fastlimit=fastlimit, slowlimit=slowlimit)
        return prices

    def triangular_moving_average(self, period='one_month', interval='day', window=10, column='close'):
        """
        Get triangular moving average for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating TMA.
        - `column`: Column name for which TMA is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'trima_' + str(window)
        prices[column_name] = ta.TRIMA(prices[column], timeperiod=window)
        return prices

    def parabolic_sar(self, period='one_month', interval='day', acceleration=0.02, maximum=0.2):
        """
        Get parabolic SAR for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `acceleration`: Acceleration factor for calculating SAR.
        - `maximum`: Maximum acceleration factor for calculating SAR.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'psar'
        prices[column_name] = ta.SAR(prices['high'], prices['low'], acceleration=acceleration, maximum=maximum)
        return prices

    def bollinger_bands(self, period='one_month', interval='day', window=10, std_dev_up=2, std_dev_down=2, ma_type=0, column='close'):
        """
        Get Bollinger bands for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating Bollinger bands.
        - `std_dev_up`: Standard deviation for calculating upper Bollinger band.
        - `std_dev_down`: Standard deviation for calculating lower Bollinger band.
        - `column`: Column name for which Bollinger bands is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name1 = 'bb_upper_band_' + str(window)
        column_name2 = 'bb_middle_band_' + str(window)
        column_name3 = 'bb_lower_band_' + str(window)

        prices[column_name1], prices[column_name2], prices[column_name3] = ta.BBANDS(prices[column], timeperiod=window, nbdevup=std_dev_up, nbdevdn=std_dev_down, matype=ma_type)
        return prices

    def mid_point(self, period='one_month', interval='day', window=10, column='close'):
        """
        Get mid point for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating mid point.
        - `column`: Column name for which mid point is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'mid_point_' + str(window)
        prices[column_name] = ta.MIDPOINT(prices[column], timeperiod=window)
        return prices

    def middle_price(self, period='one_month', interval='day', window=10):
        """
        Get mid price for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating mid price.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'middle_price_' + str(window)
        prices[column_name] = ta.MIDPRICE(prices['high'], prices['low'], timeperiod=window)
        return prices

    def average_directional_movement_index(self, period='one_month', interval='day', window=10):
        """
        Get average directional movement index for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating ADX.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'adx_' + str(window)
        prices[column_name] = ta.ADX(prices['high'], prices['low'], prices['close'], timeperiod=window)
        return prices

    def average_directional_movement_index_rating(self, period='one_month', interval='day', window=10):
        """
        Get average directional movement index rating for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating ADXR.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'adxr_' + str(window)
        prices[column_name] = ta.ADXR(prices['high'], prices['low'], prices['close'], timeperiod=window)
        return prices

    def absolute_price_oscillator(self, period='one_month', interval='day', fastperiod=12, slowperiod=26, ma_type=0, column='close'):
        """
        Get absolute price oscillator for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `fastperiod`: Fast period for calculating APO.
        - `slowperiod`: Slow period for calculating APO.
        - `ma_type`: Moving average type for calculating APO.
        - `column`: Column name for which APO is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'apo_' + str(fastperiod) + '_' + str(slowperiod)
        prices[column_name] = ta.APO(prices[column], fastperiod=fastperiod, slowperiod=slowperiod, matype=ma_type)
        return prices

    def aroon(self, period='one_month', interval='day', window=10):
        """
        Get aroon for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating aroon.
        """
        prices = self.prices(period=period, interval=interval)
        column_name1 = 'aroon_down_' + str(window)
        column_name2 = 'aroon_up_' + str(window)
        prices[column_name1], prices[column_name2] = ta.AROON(prices['high'], prices['low'], timeperiod=window)
        return prices

    def aroon_oscillator(self, period='one_month', interval='day', window=10):
        """
        Get aroon oscillator for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating aroon oscillator.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'aroon_osc_' + str(window)
        prices[column_name] = ta.AROONOSC(prices['high'], prices['low'], timeperiod=window)
        return prices

    def balance_of_power(self, period='one_month', interval='day'):
        """
        Get balance of power for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'bop'
        prices[column_name] = ta.BOP(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def commodity_channel_index(self, period='one_month', interval='day', window=10):
        """
        Get commodity channel index for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating CCI.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'cci_' + str(window)
        prices[column_name] = ta.CCI(prices['high'], prices['low'], prices['close'], timeperiod=window)
        return prices

    def chande_momentum_oscillator(self, period='one_month', interval='day', window=10, column='close'):
        """
        Get chande momentum oscillator for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating CMO.
        - `column`: Column name for which CMO is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'cmo_' + str(window)
        prices[column_name] = ta.CMO(prices[column], timeperiod=window)
        return prices

    def directional_movement_index(self, period='one_month', interval='day', window=10):
        """
        Get directional movement index for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating DMX.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'dx_' + str(window)
        prices[column_name] = ta.DX(prices['high'], prices['low'], prices['close'], timeperiod=window)
        return prices

    def moving_average_convergence_divergence(self, period='one_month', interval='day', fastperiod=12, slowperiod=26, signalperiod=9, column='close'):
        """
        Get moving average convergence divergence for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `fastperiod`: Fast period for calculating MACD.
        - `slowperiod`: Slow period for calculating MACD.
        - `signalperiod`: Signal period for calculating MACD.
        - `column`: Column name for which MACD is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name1 = 'macd_' + str(fastperiod) + '_' + str(slowperiod) + '_' + str(signalperiod)
        column_name2 = 'macd_signal_' + str(fastperiod) + '_' + str(slowperiod) + '_' + str(signalperiod)
        column_name3 = 'macd_hist_' + str(fastperiod) + '_' + str(slowperiod) + '_' + str(signalperiod)
        prices[column_name1], prices[column_name2], prices[column_name3] = ta.MACD(prices[column], fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)
        return prices

    def moving_average_convergence_divergence_extended(self, period='one_month', interval='day', fastperiod=12, fast_ma_type=0, slowperiod=26, slow_ma_type=0, signalperiod=9, signal_ma_type=0, column='close'):
        """
        Get extended moving average convergence divergence extended for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `fastperiod`: Fast period for calculating MACD.
        - `fast_ma_type`: Moving average type for calculating fast MACD.
        - `slowperiod`: Slow period for calculating MACD.
        - `slow_ma_type`: Moving average type for calculating slow MACD.
        - `signalperiod`: Signal period for calculating MACD.
        - `signal_ma_type`: Moving average type for calculating signal MACD.
        - `column`: Column name for which MACD is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name1 = 'macd_' + str(fastperiod) + '_' + str(slowperiod) + '_' + str(signalperiod)
        column_name2 = 'macd_signal_' + str(fastperiod) + '_' + str(slowperiod) + '_' + str(signalperiod)
        column_name3 = 'macd_hist_' + str(fastperiod) + '_' + str(slowperiod) + '_' + str(signalperiod)
        prices[column_name1], prices[column_name2], prices[column_name3] = ta.MACDEXT(prices[column], fastperiod=fastperiod, fastmatype=fast_ma_type, slowperiod=slowperiod, slowmatype=slow_ma_type, signalperiod=signalperiod, signalmatype=signal_ma_type)
        return prices

    def money_flow_index(self, period='one_month', interval='day', window=14):
        """
        Get money flow index for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating MFI.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'mfi_' + str(window)
        prices[column_name] = ta.MFI(prices['high'], prices['low'], prices['close'], prices['volume'], timeperiod=window)
        return prices

    def minus_directional_indicator(self, period='one_month', interval='day', window=14):
        """
        Get minus directional indicator for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating MDI.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'minus_di_' + str(window)
        prices[column_name] = ta.MINUS_DI(prices['high'], prices['low'], prices['close'], timeperiod=window)
        return prices

    def minus_directional_movement(self, period='one_month', interval='day', window=14):
        """
        Get minus directional movement for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating MDM.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'minus_dm_' + str(window)
        prices[column_name] = ta.MINUS_DM(prices['high'], prices['low'], timeperiod=window)
        return prices

    def momentum(self, period='one_month', interval='day', window=14, column='close'):
        """
        Get momentum for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating MOM.
        - `column`: Column name for which MOM is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'momentum_' + str(window)
        prices[column_name] = ta.MOM(prices[column], timeperiod=window)
        return prices

    def plus_directional_indicator(self, period='one_month', interval='day', window=14):
        """
        Get plus directional indicator for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating PDI.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'plus_di_' + str(window)
        prices[column_name] = ta.PLUS_DI(prices['high'], prices['low'], prices['close'], timeperiod=window)
        return prices

    def plus_directional_movement(self, period='one_month', interval='day', window=14):
        """
        Get plus directional movement for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating PDM.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'plus_dm_' + str(window)
        prices[column_name] = ta.PLUS_DM(prices['high'], prices['low'], timeperiod=window)
        return prices

    def percentage_price_oscillator(self, period='one_month', interval='day', fastperiod=12, slowperiod=26, matype=0, column='close'):
        """
        Get percentage price oscillator for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `fastperiod`: Fast period for calculating PPO.
        - `slowperiod`: Slow period for calculating PPO.
        - `matype`: Moving average type for calculating PPO.
        - `column`: Column name for which PPO is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'ppo'
        prices[column_name] = ta.PPO(prices[column], fastperiod=fastperiod, slowperiod=slowperiod, matype=matype)
        return prices

    def rate_of_change(self, period='one_month', interval='day', window=14, column='close'):
        """
        Get rate of change for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating ROC.
        - `column`: Column name for which ROC is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'roc_' + str(window)
        prices[column_name] = ta.ROC(prices[column], timeperiod=window)
        return prices

    def rate_of_change_percent(self, period='one_month', interval='day', window=14, column='close'):
        """
        Get rate of change percent for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating ROC.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'rocp_' + str(window)
        prices[column_name] = ta.ROCP(prices[column], timeperiod=window)
        return prices

    def rate_of_change_ratio(self, period='one_month', interval='day', window=14, column='close'):
        """
        Get rate of change ratio for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating ROC.
        - `column`: Column name for which ROC is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'rocr_' + str(window)
        prices[column_name] = ta.ROCR(prices[column], timeperiod=window)
        return prices

    def relative_strength_index(self, period='one_month', interval='day', window=14, column='close'):
        """
        Get relative strength index for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window size for calculating RSI.
        - `column`: Column name for which RSI is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'rsi_' + str(window)
        prices[column_name] = ta.RSI(prices[column], timeperiod=window)
        return prices

    def stochastic_oscillator(self, period='one_month', interval='day', fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0):
        """
        Get stochastic oscillator for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `fastk_period`: Fast K period for calculating STOCH.
        - `slowk_period`: Slow K period for calculating STOCH.
        - `slowk_matype`: Moving average type for Slow K.
        - `slowd_period`: Slow D period for calculating STOCH.
        - `slowd_matype`: Moving average type for Slow D.
        """
        prices = self.prices(period=period, interval=interval)
        column_name1 = 'slowk' + str(slowk_period)
        column_name2 = 'slowd' + str(slowd_period)
        prices[column_name1], prices[column_name2] = ta.STOCH(prices['high'], prices['low'], prices['close'], fastk_period=fastk_period, slowk_period=slowk_period, slowk_matype=slowk_matype, slowd_period=slowd_period, slowd_matype=slowd_matype)
        return prices

    def stochastic_fast_oscillator(self, period='one_month', interval='day', fastk_period=5, fastd_period=3, fastd_matype=0):
        """
        Get stochastic fast oscillator for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `fastk_period`: Fast K period for calculating STOCHF.
        - `fastd_period`: Fast D period for calculating STOCHF.
        - `fastd_matype`: Moving average type for Fast D.
        """
        prices = self.prices(period=period, interval=interval)
        column_name1 = 'stochf_fastk' + str(fastk_period)
        column_name2 = 'stochf_fastd' + str(fastd_period)
        prices[column_name1], prices[column_name2] = ta.STOCHF(prices['high'], prices['low'], prices['close'], fastk_period=fastk_period, fastd_period=fastd_period, fastd_matype=fastd_matype)
        return prices

    def stochastic_relative_strength_index(self, period='one_month', interval='day', fastk_period=5, fastd_period=3, fastd_matype=0, column='close'):
        """
        Get stochastic relative strength index for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `fastk_period`: Fast K period for calculating STOCHRSI.
        - `fastd_period`: Fast D period for calculating STOCHRSI.
        - `fastd_matype`: Moving average type for Fast D.
        - `column`: Column name for which STOCHRSI is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name1 = 'stochrsi_fastk' + str(fastk_period)
        column_name2 = 'stochrsi_fastd' + str(fastd_period)
        prices[column_name1], prices[column_name2] = ta.STOCHRSI(prices[column], timeperiod=fastk_period, fastd_period=fastd_period, fastd_matype=fastd_matype)
        return prices

    def trix(self, period='one_month', interval='day', window=15, column='close'):
        """
        Get trix for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `timeperiod`: Timeperiod for calculating TRIX.
        - `column`: Column name for which TRIX is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'trix_' + str(window)
        prices[column_name] = ta.TRIX(prices[column], timeperiod=window)
        return prices

    def ultimate_oscillator(self, period='one_month', interval='day', fast_period=7, slow_period=14, signal_period=28):
        """
        Get ultimate oscillator for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `fast_period`: Fast period for calculating ULTOSC.
        - `slow_period`: Slow period for calculating ULTOSC.
        - `signal_period`: Signal period for calculating ULTOSC.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'ultosc_' + str(fast_period)
        prices[column_name] = ta.ULTOSC(prices['high'], prices['low'], prices['close'], timeperiod1=fast_period, timeperiod2=slow_period, timeperiod3=signal_period)
        return prices

    def williams_percent_R(self, period='one_month', interval='day', window=14):
        """
        Get Williams percent R for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `timeperiod`: Timeperiod for calculating Williams percent R.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'willr_' + str(window)
        prices[column_name] = ta.WILLR(prices['high'], prices['low'], prices['close'], timeperiod=window)
        return prices

    def chaikin_ad_line(self, period='one_month', interval='day'):
        """
        Get Chaikin AD line for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'chaikin_ad'
        prices[column_name] = ta.AD(prices['high'], prices['low'], prices['close'], prices['volume'])
        return prices

    def chaikin_ad_oscillator(self, period='one_month', interval='day', fast_period=3, slow_period=10):
        """
        Get Chaikin AD oscillator for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `fast_period`: Fast period for calculating Chaikin AD oscillator.
        - `slow_period`: Slow period for calculating Chaikin AD oscillator.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'chaikin_adosc'
        prices[column_name] = ta.ADOSC(prices['high'], prices['low'], prices['close'], prices['volume'], fastperiod=3, slowperiod=10)
        return prices

    def on_balance_volume(self, period='one_month', interval='day', column='close'):
        """
        Get on balance volume for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which on balance volume is required. {'open', 'high', 'low', 'close', 'volume'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'obv'
        prices[column_name] = ta.OBV(prices[column], prices['volume'])
        return prices

    def hilbert_transform_dominant_cycle_period(self, period='one_month', interval='day', column='close'):
        """
        Get Hilbert transform dominant cycle period for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `timeperiod`: Timeperiod for calculating Hilbert transform dominant cycle period.
        - `column`: Column name for which Hilbert transform dominant cycle period is required. {'open', 'high', 'low', 'close'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'ht_dcperiod'
        prices[column_name] = ta.HT_DCPERIOD(prices[column])
        return prices

    def hilbert_transform_dominant_cycle_phase(self, period='one_month', interval='day', column='close'):
        """
        Get Hilbert transform dominant cycle phase for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which Hilbert transform dominant cycle phase is required. {'open', 'high', 'low', 'close'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'ht_dcphase'
        prices[column_name] = ta.HT_DCPHASE(prices[column])
        return prices

    def hilbert_transform_phasor_components(self, period='one_month', interval='day', column='close'):
        """
        Get Hilbert transform phasor components for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which Hilbert transform phasor components is required. {'open', 'high', 'low', 'close'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name1 = 'inphase'
        column_name2 = 'quadrature'
        prices[column_name1], prices[column_name2] = ta.HT_PHASOR(prices[column])
        return prices

    def hilbert_transform_sine_wave(self, period='one_month', interval='day', column='close'):
        """
        Get Hilbert transform sine wave for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which Hilbert transform sine wave is required. {'open', 'high', 'low', 'close'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name1 = 'sine'
        column_name2 = 'lead_sine'
        prices[column_name1], prices[column_name2] = ta.HT_SINE(prices[column])
        return prices

    def hilbert_transform_trend_mode(self, period='one_month', interval='day', column='close'):
        """
        Get Hilbert transform trend mode for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which Hilbert transform trend mode is required. {'open', 'high', 'low', 'close'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'ht_trendmode'
        prices[column_name] = ta.HT_TRENDMODE(prices[column])
        return prices

    def hilbert_transform_trend_line(self, period='one_month', interval='day', column='close'):
        """
        Get Hilbert transform trend line for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name for which Hilbert transform trend line is required. {'open', 'high', 'low', 'close'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'ht_trendline'
        prices[column_name] = ta.HT_TRENDLINE(prices[column])
        return prices

    def average_price(self, period='one_month', interval='day'):
        """
        Get average price for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'avg_price'
        prices[column_name] = ta.AVGPRICE(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def median_price(self, period='one_month', interval='day'):
        """
        Get median price for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'med_price'
        prices[column_name] = ta.MEDPRICE(prices['high'], prices['low'])
        return prices

    def typical_price(self, period='one_month', interval='day'):
        """
        Get typical price for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'typ_price'
        prices[column_name] = ta.TYPPRICE(prices['high'], prices['low'], prices['close'])
        return prices

    def weighted_close(self, period='one_month', interval='day'):
        """
        Get weighted close for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'wght_close'
        prices[column_name] = ta.WCLPRICE(prices['high'], prices['low'], prices['close'])
        return prices

    def average_true_range(self, period='one_month', interval='day', window=14):
        """
        Get average true range for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window for calculating average true range.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'atr' + str(window)
        prices[column_name] = ta.ATR(prices['high'], prices['low'], prices['close'], timeperiod=window)
        return prices

    def normalized_average_true_range(self, period='one_month', interval='day', window=14):
        """
        Get normalized average true range for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window for calculating normalized average true range.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'natr' + str(window)
        prices[column_name] = ta.NATR(prices['high'], prices['low'], prices['close'], timeperiod=window)
        return prices

    def true_range(self, period='one_month', interval='day'):
        """
        Get true range for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'tr'
        prices[column_name] = ta.TRANGE(prices['high'], prices['low'], prices['close'])
        return prices



    def beta(self, period='one_month', interval='day', window=14):
        """
        Get beta for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window for calculating beta.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'beta_' + str(window)
        prices[column_name] = ta.BETA(prices['high'], prices['low'], timeperiod=window)
        return prices

    def correlation_coefficient(self, period='one_month', interval='day', window=14):
        """
        Get correlation coefficient for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window for calculating correlation coefficient.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'corr_' + str(window)
        prices[column_name] = ta.CORREL(prices['high'], prices['low'], timeperiod=window)
        return prices

    def linear_regression(self, period='one_month', interval='day', window=14, column='close'):
        """
        Get linear regression for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window for calculating linear regression.
        - `column`: Column for which linear regression is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'lin_regr_' + str(window)
        prices[column_name] = ta.LINEARREG(prices[column], timeperiod=window)
        return prices

    def linear_regression_slope(self, period='one_month', interval='day', window=14, column='close'):
        """
        Get linear regression slope for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window for calculating linear regression slope.
        - `column`: Column for which linear regression slope is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'lin_regr_slope_' + str(window)
        prices[column_name] = ta.LINEARREG_SLOPE(prices[column], timeperiod=window)
        return prices

    def linear_regression_intercept(self, period='one_month', interval='day', window=14, column='close'):
        """
        Get linear regression intercept for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window for calculating linear regression intercept.
        - `column`: Column for which linear regression intercept is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'lin_regr_int_' + str(window)
        prices[column_name] = ta.LINEARREG_INTERCEPT(prices[column], timeperiod=window)
        return prices

    def linear_regression_angle(self, period='one_month', interval='day', window=14, column='close'):
        """
        Get linear regression angle for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window for calculating linear regression angle.
        - `column`: Column for which linear regression angle is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'lin_regr_angle_' + str(window)
        prices[column_name] = ta.LINEARREG_ANGLE(prices[column], timeperiod=window)
        return prices

    def standard_deviation(self, period='one_month', interval='day', window=14, nbdev=1, column='close'):
        """
        Get standard deviation for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window for calculating standard deviation.
        - `nbdev`: Number of standard deviations.
        - `column`: Column for which standard deviation is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'std_dev_' + str(window)
        prices[column_name] = ta.STDDEV(prices[column], timeperiod=window, nbdev=nbdev)
        return prices

    def variance(self, period='one_month', interval='day', window=14, nbdev=1, column='close'):
        """
        Get variance for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `window`: Window for calculating variance.
        - `nbdev`: Number of standard deviations.
        - `column`: Column for which variance is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'var_' + str(window)
        prices[column_name] = ta.VAR(prices[column], timeperiod=window, nbdev=nbdev)
        return prices

    def acos(self, period='one_month', interval='day', column='close'):
        """
        Get arccosine for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column for which arccosine is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'acos'
        prices[column_name] = ta.ACOS(prices[column])
        return prices

    def asin(self, period='one_month', interval='day', column='close'):
        """
        Get arcsine for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column for which arcsine is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'asin'
        prices[column_name] = ta.ASIN(prices[column])
        return prices

    def atan(self, period='one_month', interval='day', column='close'):
        """
        Get arctangent for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column for which arctangent is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'atan'
        prices[column_name] = ta.ATAN(prices[column])
        return prices

    def ceil(self, period='one_month', interval='day', column='close'):
        """
        Get ceiling for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column for which ceiling is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'ceil'
        prices[column_name] = ta.CEIL(prices[column])
        return prices

    def cos(self, period='one_month', interval='day', column='close'):
        """
        Get cosine for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column for which cosine is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'cos'
        prices[column_name] = ta.COS(prices[column])
        return prices

    def cosh(self, period='one_month', interval='day', column='close'):
        """
        Get hyperbolic cosine for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column for which hyperbolic cosine is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'cosh'
        prices[column_name] = ta.COSH(prices[column])
        return prices

    def exp(self, period='one_month', interval='day', column='close'):
        """
        Get exponential for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column for which exponential is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'exp'
        prices[column_name] = ta.EXP(prices[column])
        return prices

    def floor(self, period='one_month', interval='day', column='close'):
        """
        Get floor for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column for which floor is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'floor'
        prices[column_name] = ta.FLOOR(prices[column])
        return prices

    def ln(self, period='one_month', interval='day', column='close'):
        """
        Get natural logarithm for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column for which natural logarithm is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'ln'
        prices[column_name] = ta.LN(prices[column])
        return prices

    def log10(self, period='one_month', interval='day', column='close'):
        """
        Get logarithm to base 10 for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column for which logarithm to base 10 is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'log10'
        prices[column_name] = ta.LOG10(prices[column])
        return prices

    def sin(self, period='one_month', interval='day', column='close'):
        """
        Get sine for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column for which sine is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'sin'
        prices[column_name] = ta.SIN(prices[column])
        return prices

    def sinh(self, period='one_month', interval='day', column='close'):
        """
        Get hyperbolic sine for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column for which hyperbolic sine is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'sinh'
        prices[column_name] = ta.SINH(prices[column])
        return prices

    def sqrt(self, period='one_month', interval='day', column='close'):
        """
        Get square root for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column for which square root is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'sqrt'
        prices[column_name] = ta.SQRT(prices[column])
        return prices

    def tan(self, period='one_month', interval='day', column='close'):
        """
        Get tangent for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column for which tangent is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'tan'
        prices[column_name] = ta.TAN(prices[column])
        return prices

    def tanh(self, period='one_month', interval='day', column='close'):
        """
        Get hyperbolic tangent for a given period.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column for which hyperbolic tangent is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'tanh'
        prices[column_name] = ta.TANH(prices[column])
        return prices

    def add(self, period='one_month', interval='day', column1 = 'high', column2 = 'low'):
        """
        Add price series.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column1`: First column name.
        - `column2`: Second column name.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'sum'
        prices[column_name] = ta.ADD(prices[column1], prices[column2])
        return prices

    def sub(self, period='one_month', interval='day', column1 = 'high', column2 = 'low'):
        """
        Subtract price series.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column1`: First column name.
        - `column2`: Second column name. 
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'difference'
        prices[column_name] = ta.SUB(prices[column1], prices[column2])
        return prices

    def mul(self, period='one_month', interval='day', column1 = 'high', column2 = 'low'):
        """
        Multiply price series.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column1`: First column name.
        - `column2`: Second column name. 
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'product'
        prices[column_name] = ta.MULT(prices[column1], prices[column2])
        return prices

    def div(self, period='one_month', interval='day', column1 = 'high', column2 = 'low'):
        """
        Divide price series.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column1`: First column name.
        - `column2`: Second column name. 
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'quotient'
        prices[column_name] = ta.DIV(prices[column1], prices[column2])
        return prices

    def max(self, period='one_month', interval='day', column = 'close', window = 10):
        """
        Get maximum of price series.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name.
        - `window`: Window size.
        - `column`: Column name for which max is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'max'
        prices[column_name] = ta.MAX(prices[column], timeperiod=window)
        return prices

    def min(self, period='one_month', interval='day', column = 'close', window = 10):
        """
        Get minimum of price series.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name.
        - `window`: Window size.
        - `column`: Column name for which min is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'min'
        prices[column_name] = ta.MIN(prices[column], timeperiod=window)
        return prices

    def maxindex(self, period='one_month', interval='day', column = 'close', window = 10):
        """
        Get index of maximum of price series.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name.
        - `window`: Window size.
        - `column`: Column name for which max index is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'maxindex'
        prices[column_name] = ta.MAXINDEX(prices[column], timeperiod=window)
        return prices

    def minindex(self, period='one_month', interval='day', column = 'close', window = 10):
        """
        Get index of minimum of price series.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name.
        - `window`: Window size.
        - `column`: Column name for which min index is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'minindex'
        prices[column_name] = ta.MININDEX(prices[column], timeperiod=window)
        return prices

    def minmax(self, period='one_month', interval='day', column = 'close', window = 10):
        """
        Get minimum and maximum of price series.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name.
        - `window`: Window size.
        - `column`: Column name for which minimum and maximum is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name1 = 'min'
        column_name2 = 'max'
        prices[column_name1], prices[column_name2] = ta.MINMAX(prices[column], timeperiod=window)
        return prices

    def minmaxindex(self, period='one_month', interval='day', column = 'close', window = 10):
        """
        Get index of minimum and maximum of price series.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `column`: Column name.
        - `window`: Window size.
        - `column`: Column name for which minimum and maximum index is required.
        """
        prices = self.prices(period=period, interval=interval)
        column_name1 = 'minindex'
        column_name2 = 'maxindex'
        prices[column_name1], prices[column_name2] = ta.MINMAXINDEX(prices[column], timeperiod=window)
        return prices



    def candle_two_crows(self, period='one_month', interval='day'):
        """
        Get two crows candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_two_crows'
        prices[column_name] = ta.CDL2CROWS(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_three_black_crows(self, period='one_month', interval='day'):
        """
        Get three black crows candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_three_black_crows'
        prices[column_name] = ta.CDL3BLACKCROWS(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_three_inside_up_down(self, period='one_month', interval='day'):
        """
        Get three inside up/down candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_three_inside_up_down'
        prices[column_name] = ta.CDL3INSIDE(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_three_line_strike(self, period='one_month', interval='day'):
        """
        Get three line strike candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_three_line_strike'
        prices[column_name] = ta.CDL3LINESTRIKE(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_three_outside_up_down(self, period='one_month', interval='day'):
        """
        Get three outside up/down candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_three_outside_up_down'
        prices[column_name] = ta.CDL3OUTSIDE(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_three_stars_in_the_south(self, period='one_month', interval='day'):
        """
        Get three stars in the south candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_three_stars_in_the_south'
        prices[column_name] = ta.CDL3STARSINSOUTH(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_three_white_soldiers(self, period='one_month', interval='day'):
        """
        Get three white soldiers candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_three_white_soldiers'
        prices[column_name] = ta.CDL3WHITESOLDIERS(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_abandoned_baby(self, period='one_month', interval='day'):
        """
        Get abandoned baby candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_abandoned_baby'
        prices[column_name] = ta.CDLABANDONEDBABY(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_advance_block(self, period='one_month', interval='day'):
        """
        Get advance block candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_advance_block'
        prices[column_name] = ta.CDLADVANCEBLOCK(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_belt_hold(self, period='one_month', interval='day'):
        """
        Get belt hold candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_belt_hold'
        prices[column_name] = ta.CDLBELTHOLD(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_breakaway(self, period='one_month', interval='day'):
        """
        Get breakaway candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_breakaway'
        prices[column_name] = ta.CDLBREAKAWAY(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_closing_marubozu(self, period='one_month', interval='day'):
        """
        Get closing marubozu candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_closing_marubozu'
        prices[column_name] = ta.CDLCLOSINGMARUBOZU(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_concealing_baby_swallow(self, period='one_month', interval='day'):
        """
        Get concealing baby swallow candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_concealing_baby_swallow'
        prices[column_name] = ta.CDLCONCEALBABYSWALL(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_counter_attack(self, period='one_month', interval='day'):
        """
        Get counter attack candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_counter_attack'
        prices[column_name] = ta.CDLCOUNTERATTACK(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_dark_cloud_cover(self, period='one_month', interval='day'):
        """
        Get dark cloud cover candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_dark_cloud_cover'
        prices[column_name] = ta.CDLDARKCLOUDCOVER(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_doji(self, period='one_month', interval='day'):
        """
        Get doji candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_doji'
        prices[column_name] = ta.CDLDOJI(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_doji_star(self, period='one_month', interval='day'):
        """
        Get doji star candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_doji_star'
        prices[column_name] = ta.CDLDOJISTAR(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_dragonfly_doji(self, period='one_month', interval='day'):
        """
        Get dragonfly doji candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_dragonfly_doji'
        prices[column_name] = ta.CDLDRAGONFLYDOJI(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_engulfing(self, period='one_month', interval='day'):
        """
        Get engulfing candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_engulfing'
        prices[column_name] = ta.CDLENGULFING(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_evening_dojistar(self, period='one_month', interval='day'):
        """
        Get evening dojistar candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_evening_dojistar'
        prices[column_name] = ta.CDLEVENINGDOJISTAR(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_evening_star(self, period='one_month', interval='day'):
        """
        Get evening star candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_evening_star'
        prices[column_name] = ta.CDLEVENINGSTAR(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_side_by_side_white_lines(self, period='one_month', interval='day'):
        """
        Get side by side white lines candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_side_by_side_white_lines'
        prices[column_name] = ta.CDLGAPSIDESIDEWHITE(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_gravestone_doji(self, period='one_month', interval='day'):
        """
        Get gravestone doji candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_gravestone_doji'
        prices[column_name] = ta.CDLGRAVESTONEDOJI(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_hammer(self, period='one_month', interval='day'):
        """
        Get hammer candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_hammer'
        prices[column_name] = ta.CDLHAMMER(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_hangingman(self, period='one_month', interval='day'):
        """
        Get hanging man candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_harami'
        prices[column_name] = ta.CDLHANGINGMAN(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_harami(self, period='one_month', interval='day'):
        """
        Get harami candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_harami'
        prices[column_name] = ta.CDLHARAMI(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_harami_cross(self, period='one_month', interval='day'):
        """
        Get harami cross candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_harami_cross'
        prices[column_name] = ta.CDLHARAMICROSS(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_high_wave(self, period='one_month', interval='day'):
        """
        Get high wave candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_high_wave'
        prices[column_name] = ta.CDLHIGHWAVE(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_hikkake(self, period='one_month', interval='day'):
        """
        Get hikkake candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_hikkake'
        prices[column_name] = ta.CDLHIKKAKE(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_modified_hikkake(self, period='one_month', interval='day'):
        """
        Get modified hikkake candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_modified_hikkake'
        prices[column_name] = ta.CDLHIKKAKEMOD(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_homing_pigeon(self, period='one_month', interval='day'):
        """
        Get homing pigeon candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_homing_pigeon'
        prices[column_name] = ta.CDLHOMINGPIGEON(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_identical_three_crows(self, period='one_month', interval='day'):
        """
        Get identical three crows candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_identical_three_crows'
        prices[column_name] = ta.CDLIDENTICAL3CROWS(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_in_neck(self, period='one_month', interval='day'):
        """
        Get in neck candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_in_neck'
        prices[column_name] = ta.CDLINNECK(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_inverted_hammer(self, period='one_month', interval='day'):
        """
        Get inverted hammer candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_inverted_hammer'
        prices[column_name] = ta.CDLINVERTEDHAMMER(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_kicking(self, period='one_month', interval='day'):
        """
        Get kicking candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_kicking'
        prices[column_name] = ta.CDLKICKING(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_kicking_by_length(self, period='one_month', interval='day'):
        """
        Get kicking by length candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_kicking_by_length'
        prices[column_name] = ta.CDLKICKINGBYLENGTH(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_ladder_bottom(self, period='one_month', interval='day'):
        """
        Get ladder bottom candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_ladder_bottom'
        prices[column_name] = ta.CDLLADDERBOTTOM(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_long_legged_doji(self, period='one_month', interval='day'):
        """
        Get long legged doji candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_long_legged_doji'
        prices[column_name] = ta.CDLLONGLEGGEDDOJI(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_long_line(self, period='one_month', interval='day'):
        """
        Get long line candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_long_line'
        prices[column_name] = ta.CDLLONGLINE(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_marubozu(self, period='one_month', interval='day'):
        """
        Get marubozu candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_marubozu'
        prices[column_name] = ta.CDLMARUBOZU(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_matching_low(self, period='one_month', interval='day'):
        """
        Get matching low candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_matching_low'
        prices[column_name] = ta.CDLMATCHINGLOW(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_mat_hold(self, period='one_month', interval='day'):
        """
        Get mat hold candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_mat_hold'
        prices[column_name] = ta.CDLMATHOLD(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_morning_star(self, period='one_month', interval='day'):
        """
        Get morning star candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_morning_star'
        prices[column_name] = ta.CDLMORNINGSTAR(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_morning_star_doji(self, period='one_month', interval='day'):
        """
        Get morning star doji candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_morning_star_doji'
        prices[column_name] = ta.CDLMORNINGDOJISTAR(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_on_neck(self, period='one_month', interval='day'):
        """
        Get on neck candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_on_neck'
        prices[column_name] = ta.CDLONNECK(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_piercing(self, period='one_month', interval='day'):
        """
        Get piercing candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_piercing'
        prices[column_name] = ta.CDLPIERCING(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_rickshaw_man(self, period='one_month', interval='day'):
        """
        Get rickshaw man candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_rickshaw_man'
        prices[column_name] = ta.CDLRICKSHAWMAN(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_rise_fall_three_methods(self, period='one_month', interval='day'):
        """
        Get rise fall three methods candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_rise_fall_three_methods'
        prices[column_name] = ta.CDLRISEFALL3METHODS(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_separating_lines(self, period='one_month', interval='day'):
        """
        Get separating lines candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_separating_lines'
        prices[column_name] = ta.CDLSEPARATINGLINES(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_shooting_star(self, period='one_month', interval='day'):
        """
        Get shooting star candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_shooting_star'
        prices[column_name] = ta.CDLSHOOTINGSTAR(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_short_line(self, period='one_month', interval='day'):
        """
        Get short line candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_short_line'
        prices[column_name] = ta.CDLSHORTLINE(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_spinning_top(self, period='one_month', interval='day'):
        """
        Get spinning top candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_spinning_top'
        prices[column_name] = ta.CDLSPINNINGTOP(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_stalled_pattern(self, period='one_month', interval='day'):
        """
        Get stalled pattern candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_stalled_pattern'
        prices[column_name] = ta.CDLSTALLEDPATTERN(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_stick_sandwich(self, period='one_month', interval='day'):
        """
        Get stick sandwich candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_stick_sandwich'
        prices[column_name] = ta.CDLSTICKSANDWICH(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_takuri(self, period='one_month', interval='day'):
        """
        Get takuri candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_takuri'
        prices[column_name] = ta.CDLTAKURI(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_tasuki_gap(self, period='one_month', interval='day'):
        """
        Get tasuki gap candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_tasuki_gap'
        prices[column_name] = ta.CDLTASUKIGAP(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_thrusting_pattern(self, period='one_month', interval='day'):
        """
        Get thrusting pattern candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_thrusting_pattern'
        prices[column_name] = ta.CDLTHRUSTING(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_tristar(self, period='one_month', interval='day'):
        """
        Get tristar candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_tristar'
        prices[column_name] = ta.CDLTRISTAR(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_unique_three_river(self, period='one_month', interval='day'):
        """
        Get unique three river candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_unique_three_river'
        prices[column_name] = ta.CDLUNIQUE3RIVER(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_up_side_gap_two_crows(self, period='one_month', interval='day'):
        """
        Get up side gap two crows candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_up_side_gap_two_crows'
        prices[column_name] = ta.CDLUPSIDEGAP2CROWS(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices

    def candle_up_side_down_side_gap_three_methods(self, period='one_month', interval='day'):
        """
        Get up side gap three methods candle pattern.

        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        """
        prices = self.prices(period=period, interval=interval)
        column_name = 'candle_up_side_gap_three_methods'
        prices[column_name] = ta.CDLXSIDEGAP3METHODS(prices['open'], prices['high'], prices['low'], prices['close'])
        return prices



    def is_cross_over(self, data, column1, column2):
        """
        Check if the data crosses over the other data.

        - `data`: Dataframe with the data.
        - `column1`: Column name of the first data.
        - `column2`: Column name of the second data.
        """
        data = data.copy()
        cols = data.columns.tolist()
        data.reset_index(inplace=True, drop=True)
        data['shifted_column1'] = data[column1].shift()
        data['cross_over'] = np.where((data['shifted_column1'] <= data[column2]) & (data[column2] < data[column1]), True, False)
        data = data[cols + ['cross_over']]
        return data

    def is_cross_under(self, data, column1, column2):
        """
        Check if the data crosses under the other data.

        - `data`: Dataframe with the data.
        - `column1`: Column name of the first data.
        - `column2`: Column name of the second data.
        """
        data = data.copy()
        cols = data.columns.tolist()
        data.reset_index(inplace=True, drop=True)
        data['shifted_column1'] = data[column1].shift()
        data['cross_under'] = np.where((data['shifted_column1'] >= data[column2]) & (data[column2] > data[column1]), True, False)
        data = data[cols + ['cross_under']]
        return data

    def run_backtest(self, strategy, period='one_year', interval='day', cash=10000, commission=0.0, margin=1.0, trade_on_close=False, hedging=False, exclusive_orders=False):
        """
        Run backtest for the given strategy.

        - `strategy`: Strategy to be tested.
        - `period`: Period for which prices are required. {'one_day', 'one_week', 'one_month', 'three_months', 'six_months', 'one_year', 'five_years', 'max', 'week_to_date', 'month_to_date', 'year_to_date'}
        - `interval`: Interval between two consecutive data points. {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour', 'day'}
        - `cash`: Cash to start with.
        - `commission`: Commission per trade.
        - `margin`: Margin to be used.
        - `trade_on_close`: If True, the trade is executed at the close of the day.
        - `hedging`: If True, hedging is allowed.
        - `exclusive_orders`: If True, only one order per bar is allowed.
        """
        prices = self.prices(period=period, interval=interval)
        prices['datetime'] = pd.to_datetime(prices['datetime'])
        prices.index = prices['datetime']
        prices = prices.drop(columns=['datetime', 'exchange', 'tradingsymbol', 'interval'])
        prices.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

        backtest = backtesting.backtesting.Backtest(data=prices, strategy=strategy, cash=cash, commission=commission, margin=margin, trade_on_close=trade_on_close, hedging=hedging, exclusive_orders=exclusive_orders)
        backtest_stats = backtest.run()
        backtest.plot()
        return backtest_stats

class TradeableInstrument(Instrument):
    """
    TradeableInstrument class encapsulates the functionality of a tradeable instrument.
    """

    def __init__(self, id):
        """
        TradeableInstrument class encapsulates the functionality of a tradeable instrument.

        - `id`: is the instrument id. It is of the format `exchange:tradingsymbol`.
        """
        super().__init__(id=id)
        
        self._EXCHANGE_MAP = {
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

        if self.segment == 'INDICES':
            raise TradeableInstrumentException(f"{id} is not a tradeable instrument.")

    def __repr__(self):
        """
        Returns a string representation of the tradeable instrument.
        """
        return f"TradeableInstrument(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the tradeable instrument.
        """
        return f"TradeableInstrument(id=\"{self._id}\")"

    def _unpack_int(self, bin, start, end, byte_format="I"):
        """Unpack binary data as unsgined interger.
        
        - `bin`: Binary data.
        - `start`: Start index.
        - `end`: End index.
        - `byte_format`: Byte format.
        """
        return struct.unpack(">" + byte_format, bin[start:end])[0]
    

    # Streaming market quotes
    def _get_segment(self, packet):
        """
        Get segment from packet.
        
        - `packet`: Binary data packet.
        """
        instrument_token = self._unpack_int(packet, 0, 4)
        return instrument_token & 0xff

    def _get_divisor(self, packet):
        """
        Get divisor from packet.
        """
        segment = self._get_segment(packet)

        if segment == self._EXCHANGE_MAP["cds"]:
            divisor = 10000000.0
        elif segment == self._EXCHANGE_MAP["bcd"]:
            divisor = 1000.0
        else:
            divisor = 100.0

        return divisor

    @property
    def quote(self):
        """
        Returns the quote.
        """
        if not self._cache.hexists('market_data', self.id):
            return None
                    
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        instrument_token = self._unpack_int(packet, 0, 4)
        segment = instrument_token & 0xff

        if segment == self._EXCHANGE_MAP["cds"]:
            divisor = 10000000.0
        elif segment == self._EXCHANGE_MAP["bcd"]:
            divisor = 1000.0
        else:
            divisor = 100.0

        tradeable = False if segment == self._EXCHANGE_MAP["indices"] else True

        quote = {
            "tradeable": tradeable,
            "mode": "full",
            "instrument_token": instrument_token,
            "last_traded_price": self._unpack_int(packet, 4, 8) / divisor,
            "last_traded_quantity": self._unpack_int(packet, 8, 12),
            "average_traded_price": self._unpack_int(packet, 12, 16) / divisor,
            "volume_traded_today": self._unpack_int(packet, 16, 20),
            "total_bid_quantity": self._unpack_int(packet, 20, 24),
            "total_offer_quantity": self._unpack_int(packet, 24, 28),
            "ohlc": {
                "open": self._unpack_int(packet, 28, 32) / divisor,
                "high": self._unpack_int(packet, 32, 36) / divisor,
                "low": self._unpack_int(packet, 36, 40) / divisor,
                "close": self._unpack_int(packet, 40, 44) / divisor
            },
            "last_trade_time": datetime.fromtimestamp(self._unpack_int(packet, 44, 48)).strftime("%Y-%m-%d %H:%M:%S.%f"),
            "oi": self._unpack_int(packet, 48, 52),
            "oi_day_high": self._unpack_int(packet, 52, 56),
            "oi_day_low": self._unpack_int(packet, 56, 60),
            "exchange_timestamp": datetime.fromtimestamp(self._unpack_int(packet, 60, 64)).strftime("%Y-%m-%d %H:%M:%S.%f"),
            "arrival_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        }

        quote["change"] = 0
        if (quote["ohlc"]["close"] != 0):
            quote["change"] = (quote["last_traded_price"] - quote["ohlc"]["close"]) * 100 / quote["ohlc"]["close"]

        depth = {
            "buy": [],
            "sell": []
        }

        for i, p in enumerate(range(64, len(packet), 12)):
            depth["sell" if i >= 5 else "buy"].append({
                "quantity": self._unpack_int(packet, p, p + 4),
                "price": self._unpack_int(packet, p + 4, p + 8) / divisor,
                "orders": self._unpack_int(packet, p + 8, p + 10, byte_format="H")
            })

        quote["depth"] = depth
        return quote

    @property
    def is_tradeable(self):
        """
        Returns True if the instrument is tradeable.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        segment = self._get_segment(packet)
        return False if segment == self._EXCHANGE_MAP["indices"] else True
    
    @property
    def mode(self):
        """
        Returns the mode.
        """
        return "full"

    @property
    def last_traded_price(self):
        """
        Returns the last traded price.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        segment = self._get_segment(packet)
        divisor = self._get_divisor(packet)        
        return self._unpack_int(packet, 4, 8) / divisor
    
    @property
    def last_traded_quantity(self):
        """
        Returns the last traded quantity.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        return self._unpack_int(packet, 8, 12)
    
    @property
    def average_traded_price(self):
        """
        Returns the average traded price.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        segment = self._get_segment(packet)
        divisor = self._get_divisor(packet)
        return self._unpack_int(packet, 12, 16) / divisor
    
    @property
    def volume_traded_today(self):
        """
        Returns the volume traded today.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        return self._unpack_int(packet, 16, 20)
    
    @property
    def total_bid_quantity(self):
        """
        Returns the total bid quantity.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        return self._unpack_int(packet, 20, 24)
    
    @property
    def total_offer_quantity(self):
        """
        Returns the total offer quantity.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        return self._unpack_int(packet, 24, 28)
    
    @property
    def ohlc(self):
        """
        Returns the ohlc.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        segment = self._get_segment(packet)
        divisor = self._get_divisor(packet)
        return {
            "open": self._unpack_int(packet, 28, 32) / divisor,
            "high": self._unpack_int(packet, 32, 36) / divisor,
            "low": self._unpack_int(packet, 36, 40) / divisor,
            "close": self._unpack_int(packet, 40, 44) / divisor
        }
    
    @property
    def last_trade_time(self):
        """
        Returns the last trade time.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        return datetime.fromtimestamp(self._unpack_int(packet, 44, 48)).strftime("%Y-%m-%d %H:%M:%S.%f")
    
    @property
    def oi(self):
        """
        Returns the oi.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        return self._unpack_int(packet, 48, 52)
    
    @property
    def oi_day_high(self):
        """
        Returns the oi day high.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        return self._unpack_int(packet, 52, 56)
    
    @property
    def oi_day_low(self):
        """
        Returns the oi day low.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        return self._unpack_int(packet, 56, 60)
    
    @property
    def exchange_timestamp(self):
        """
        Returns the exchange timestamp.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        return datetime.fromtimestamp(self._unpack_int(packet, 60, 64)).strftime("%Y-%m-%d %H:%M:%S.%f")
    
    @property
    def change(self):
        """
        Returns the change.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        quote = self.quote
        return quote["change"]
    
    @property
    def market_depth(self):
        """
        Returns the depth.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        segment = self._get_segment(packet)
        divisor = self._get_divisor(packet)
        depth = {
            "buy": [],
            "sell": []
        }

        for i, p in enumerate(range(64, len(packet), 12)):
            depth["sell" if i >= 5 else "buy"].append({
                "quantity": self._unpack_int(packet, p, p + 4),
                "price": self._unpack_int(packet, p + 4, p + 8) / divisor,
                "orders": self._unpack_int(packet, p + 8, p + 10, byte_format="H")
            })

        return depth
    
    @property
    def bids(self):
        """
        Returns the bids.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        depth = self.market_depth
        return depth["buy"]
    
    @property
    def offers(self):
        """
        Returns the offers.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        depth = self.market_depth
        return depth["sell"]
    
    @property
    def best_bid(self):
        """
        Returns the best bid.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        bids = self.bids
        return bids[0] if len(bids) > 0 else None
    
    @property
    def best_offer(self):
        """
        Returns the best offer.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        offers = self.offers
        return offers[0] if len(offers) > 0 else None
    
    @property
    def bid_offer_spread(self):
        """
        Returns the bid offer spread.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        depth = self.market_depth
        best_bid = depth["buy"][0] if len(depth["buy"]) > 0 else None
        best_offer = depth["sell"][0] if len(depth["sell"]) > 0 else None
        return best_offer["price"] - best_bid["price"] if best_bid and best_offer else None
    
    @property
    def mid_price(self):
        """
        Returns the mid price.
        """
        packet = bytes.fromhex(self._cache.hget('market_data', self.id))
        depth = self.market_depth
        best_bid = depth["buy"][0] if len(depth["buy"]) > 0 else None
        best_offer = depth["sell"][0] if len(depth["sell"]) > 0 else None
        return (best_bid["price"] + best_offer["price"]) / 2 if best_bid and best_offer else None


    # order related methods
    @property
    def orders(self):
        """
        Returns orders placed during the day.
        """
        data = self._zerodha_rest_api.get(url="https://api.kite.trade/orders")['data']
        if data is None or len(data) == 0:
            return None
        
        data = pd.DataFrame(data)
        orders = data[(data['tradingsymbol'] == self.tradingsymbol) & (data['exchange'] == self.exchange)]

        if orders.empty:
            return None

        orders.reset_index(drop=True, inplace=True)
        return orders

    @property
    def completed_orders(self):
        """
        Returns completed orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        completed_orders = orders[orders['status'] == 'COMPLETE']
        if completed_orders.empty:
            return None

        completed_orders.reset_index(drop=True, inplace=True)
        return completed_orders
    
    @property
    def open_orders(self):
        """
        Returns open orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        open_orders = orders[orders['status'] == 'OPEN']
        if open_orders.empty:
            return None

        open_orders.reset_index(drop=True, inplace=True)
        return open_orders
    
    @property
    def rejected_orders(self):
        """
        Returns rejected orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        rejected_orders = orders[orders['status'] == 'REJECTED']
        if rejected_orders.empty:
            return None

        rejected_orders.reset_index(drop=True, inplace=True)
        return rejected_orders

    @property
    def cancelled_orders(self):
        """
        Returns cancelled orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        cancelled_orders = orders[orders['status'].str.contains('CANCELLED')]
        if cancelled_orders.empty:
            return None

        cancelled_orders.reset_index(drop=True, inplace=True)
        return cancelled_orders



    @property
    def orders_placed_in_last_hour(self):
        """
        Orders places in the last one hour
        """
        orders = self.orders
        if orders is None:
            return None

        orders_placed_in_last_hour = orders[orders['order_timestamp'] >= (datetime.now() - timedelta(hours=1))]
        if orders_placed_in_last_hour.empty:
            return None

        orders_placed_in_last_hour.reset_index(drop=True, inplace=True)
        return orders_placed_in_last_hour
    
    @property
    def orders_placed_in_last_two_hours(self):
        """
        Orders places in the last two hours
        """
        orders = self.orders
        if orders is None:
            return None

        orders_placed_in_last_two_hours = orders[orders['order_timestamp'] >= (datetime.now() - timedelta(hours=2))]
        if orders_placed_in_last_two_hours.empty:
            return None

        orders_placed_in_last_two_hours.reset_index(drop=True, inplace=True)
        return orders_placed_in_last_two_hours
    
    @property
    def orders_placed_in_last_three_hours(self):
        """
        Orders places in the last three hours
        """
        orders = self.orders
        if orders is None:
            return None

        orders_placed_in_last_three_hours = orders[orders['order_timestamp'] >= (datetime.now() - timedelta(hours=3))]
        if orders_placed_in_last_three_hours.empty:
            return None

        orders_placed_in_last_three_hours.reset_index(drop=True, inplace=True)
        return orders_placed_in_last_three_hours
    
    @property
    def orders_placed_in_last_four_hours(self):
        """
        Orders places in the last four hours
        """
        orders = self.orders
        if orders is None:
            return None

        orders_placed_in_last_four_hours = orders[orders['order_timestamp'] >= (datetime.now() - timedelta(hours=4))]
        if orders_placed_in_last_four_hours.empty:
            return None

        orders_placed_in_last_four_hours.reset_index(drop=True, inplace=True)
        return orders_placed_in_last_four_hours
    
    @property
    def orders_placed_in_last_five_hours(self):
        """
        Orders places in the last five hours
        """
        orders = self.orders
        if orders is None:
            return None

        orders_placed_in_last_five_hours = orders[orders['order_timestamp'] >= (datetime.now() - timedelta(hours=5))]
        if orders_placed_in_last_five_hours.empty:
            return None

        orders_placed_in_last_five_hours.reset_index(drop=True, inplace=True)
        return orders_placed_in_last_five_hours



    @property
    def regular_orders(self):
        """
        Returns regular orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        regular_orders = orders[orders['variety'] == 'regular']
        if regular_orders.empty:
            return None

        regular_orders.reset_index(drop=True, inplace=True)
        return regular_orders
    
    @property
    def cover_orders(self):
        """
        Returns cover orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        cover_orders = orders[orders['variety'] == 'co']
        if cover_orders.empty:
            return None

        cover_orders.reset_index(drop=True, inplace=True)
        return cover_orders
    
    @property
    def after_market_orders(self):
        """
        Returns after market orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        after_market_orders = orders[orders['variety'] == 'amo']
        if after_market_orders.empty:
            return None

        after_market_orders.reset_index(drop=True, inplace=True)
        return after_market_orders
    
    @property
    def iceberg_orders(self):
        """
        Returns iceberg orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        iceberg_orders = orders[orders['variety'] == 'iceberg']
        if iceberg_orders.empty:
            return None

        iceberg_orders.reset_index(drop=True, inplace=True)
        return iceberg_orders
    
    @property
    def auction_orders(self):
        """
        Returns auction orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        auction_orders = orders[orders['variety'] == 'auction']
        if auction_orders.empty:
            return None

        auction_orders.reset_index(drop=True, inplace=True)
        return auction_orders

    @property
    def modified_order(self):
        """
        Returns modified orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        modified_orders = orders[orders['modified'] == True]
        if modified_orders.empty:
            return None

        modified_orders.reset_index(drop=True, inplace=True)
        return modified_orders
    
    @property
    def unmodified_orders(self):
        """
        Returns unmodified orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        unmodified_orders = orders[orders['modified'] == False]
        if unmodified_orders.empty:
            return None

        unmodified_orders.reset_index(drop=True, inplace=True)
        return unmodified_orders

    @property
    def limit_orders(self):
        """
        Returns limit orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        limit_orders = orders[orders['order_type'] == 'LIMIT']
        if limit_orders.empty:
            return None

        limit_orders.reset_index(drop=True, inplace=True)
        return limit_orders
    
    @property
    def market_orders(self):
        """
        Returns market orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        market_orders = orders[orders['order_type'] == 'MARKET']
        if market_orders.empty:
            return None

        market_orders.reset_index(drop=True, inplace=True)
        return market_orders
    
    @property
    def stop_loss_orders(self):
        """
        Returns stop loss orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        stop_loss_orders = orders[orders['order_type'] == 'SL']
        if stop_loss_orders.empty:
            return None

        stop_loss_orders.reset_index(drop=True, inplace=True)
        return stop_loss_orders
    
    @property
    def stop_loss_market_orders(self):
        """
        Returns stop loss market orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        stop_loss_market_orders = orders[orders['order_type'] == 'SL-M']
        if stop_loss_market_orders.empty:
            return None

        stop_loss_market_orders.reset_index(drop=True, inplace=True)
        return stop_loss_market_orders

    @property
    def buy_orders(self):
        """
        Returns buy orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        buy_orders = orders[orders['transaction_type'] == 'BUY']
        if buy_orders.empty:
            return None

        buy_orders.reset_index(drop=True, inplace=True)
        return buy_orders
    
    @property
    def sell_orders(self):
        """
        Returns sell orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        sell_orders = orders[orders['transaction_type'] == 'SELL']
        if sell_orders.empty:
            return None

        sell_orders.reset_index(drop=True, inplace=True)
        return sell_orders

    @property
    def day_orders(self):
        """
        Returns day orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        day_orders = orders[orders['validity'] == 'DAY']
        if day_orders.empty:
            return None

        day_orders.reset_index(drop=True, inplace=True)
        return day_orders
    
    @property
    def ttl_orders(self):
        """
        Returns ttl orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        ttl_orders = orders[orders['validity'] == 'TTL']
        if ttl_orders.empty:
            return None

        ttl_orders.reset_index(drop=True, inplace=True)
        return ttl_orders

    @property
    def mis_orders(self):
        """
        Returns mis orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        mis_orders = orders[orders['product'] == 'MIS']
        if mis_orders.empty:
            return None

        mis_orders.reset_index(drop=True, inplace=True)
        return mis_orders
    
    @property
    def cnc_orders(self):
        """
        Returns cnc orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        cnc_orders = orders[orders['product'] == 'CNC']
        if cnc_orders.empty:
            return None

        cnc_orders.reset_index(drop=True, inplace=True)
        return cnc_orders
    
    @property
    def nrml_orders(self):
        """
        Returns nrml orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        nrml_orders = orders[orders['product'] == 'NRML']
        if nrml_orders.empty:
            return None

        nrml_orders.reset_index(drop=True, inplace=True)
        return nrml_orders

    @property
    def fully_filled_orders(self):
        """
        Returns fully filled orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        fully_filled_orders = orders[(orders['pending_quantity'] == 0) & (orders['filled_quantity'] == orders['quantity'])]
        if fully_filled_orders.empty:
            return None

        fully_filled_orders.reset_index(drop=True, inplace=True)
        return fully_filled_orders

    @property
    def partially_filled_orders(self):
        """
        Returns partially filled orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        partially_filled_order = orders[(orders['filled_quantity'] > 0) & (orders['pending_quantity'] > 0)]
        if partially_filled_order.empty:
            return None

        partially_filled_order.reset_index(drop=True, inplace=True)
        return partially_filled_order

    @property
    def unfilled_orders(self):
        """
        Returns unfilled orders placed during the day.
        """
        orders = self.orders
        if orders is None:
            return None

        unfilled_orders = orders[orders['pending_quantity'] == orders['quantity']]
        if unfilled_orders.empty:
            return None

        unfilled_orders.reset_index(drop=True, inplace=True)
        return unfilled_orders

    @property
    def order_history(self):
        """
        Returns the order history of all orders for this instrument.
        """
        orders = self.orders
        if orders is None:
            return None

        order_hist = []
        for index, row in orders.iterrows():
            order_id = row['order_id']
            data = self._zerodha_rest_api.get(url=f"https://api.kite.trade/orders/{order_id}")['data']
            if data is None:
                raise TradeableInstrumentException(f"Order {order_id} not found")            
            order_hist.append(pd.DataFrame(data))

        if len(order_hist) == 0:
            return None
            
        order_hist = pd.concat(order_hist, ignore_index=True)
        order_hist.reset_index(drop=True, inplace=True)
        return order_hist

    @property
    def trades(self):
        """
        Returns the list of trades for the instrument
        """
        data = self._zerodha_rest_api.get(url="https://api.kite.trade/trades")['data']
        if data is None or len(data) == 0:
            return None
        
        data = pd.DataFrame(data)
        trades = data[(data['tradingsymbol'] == self.tradingsymbol) & (data['exchange'] == self.exchange)]

        if trades.empty:
            return None
        
        trades.reset_index(drop=True, inplace=True)
        return trades



    def place_order(self, variety='regular', transaction_type='BUY', order_type='MARKET', product='CNC', quantity=1, price=None, trigger_price=None, disclosed_quantity=None, validity='DAY', validity_ttl=None, iceberg_legs=None, iceberg_quantity=None, auction_number=None, tag=None):
        """
        Place an order for the instrument

        - `variety`: Variety of order. {regular, co, amo, iceberg, auction}
        - `transaction_type`: Transaction type. {BUY, SELL}
        - `order_type`: Order type. {MARKET, LIMIT, SL, SL-M}
        - `product`: Margin product to use for the order (margins are blocked based on this). {MIS, CNC, NRML}        
        
        - `quantity`: Quantity to transact.
        - `price`: The price to execute the order at (for LIMIT orders).
        
        - `trigger_price`: The price at which an order should be triggered (SL, SL-M).
        - `disclosed_quanity`: Quantity to disclose publicly (for equity trades).
        
        - `validity`: Order validity. {DAY, IOC, TTL}
        - `validity_ttl`: Order life span in minutes for TTL validity orders.
        
        - `iceberg_legs`: Total number of legs for iceberg order type (number of legs per Iceberg should be between 2 and 10).
        - `iceberg_quantity`: Split quantity for each iceberg leg order (quantity/iceberg_legs).
        
        - `auction_number`: A unique identifier for a particular auction.
        
        - `tag`: An optional tag to apply to an order to identify it (alphanumeric, max 20 chars).
        """
        data = {}
        data['variety'] = variety.lower()
        data['exchange'] = self.exchange.upper()
        data['tradingsymbol'] = self.tradingsymbol.upper()
        data['transaction_type'] = transaction_type.upper()
        data['order_type'] = order_type.upper()
        data['product'] = product.upper()

        data['quantity'] = quantity * self.lot_size
        if price:
            data['price'] = price

        if validity:
            data['validity'] = validity.upper()
        if validity_ttl:
            data['validity_ttl'] = validity_ttl

        if disclosed_quantity:
            data['disclosed_quantity'] = disclosed_quantity
        if trigger_price:
            data['trigger_price'] = trigger_price

        if iceberg_legs:
            data['iceberg_legs'] = iceberg_legs
        if iceberg_quantity:
            data['iceberg_quantity'] = iceberg_quantity

        if auction_number:
            data['auction_number'] = auction_number

        if tag:
            data['tag'] = tag

        order_id = self._zerodha_rest_api.post(url=f"https://api.kite.trade/orders/{variety}", data=data)['data']['order_id']
        return order_id

    def modify_order(self, order_id, variety='regular', parent_order_id=None, quantity=None, price=None, order_type=None, trigger_price=None, validity=None, disclosed_quantity=None):
        """
        Modify an open order.

        - `order_id`: Order ID.
        - `variety`: Variety of order. {regular, co, amo, iceberg, auction}
        - `parent_order_id`: Parent order ID.
        - `quantity`: Quantity to transact.
        - `price`: The price to execute the order at (for LIMIT orders).
        - `order_type`: Order type. {MARKET, LIMIT, SL, SL-M}
        - `trigger_price`: The price at which an order should be triggered (SL, SL-M).
        - `validity`: Validity. {DAY, IOC, TTL}
        - `disclosed_quantity`: Quantity to disclose publicly (for equity trades).
        """
        data = {}
        data['variety'] = variety.lower()
        data['order_id'] = order_id
        if parent_order_id:
            data['parent_order_id'] = parent_order_id
        if quantity:
            data['quantity'] = quantity * self.lot_size
        if price:
            data['price'] = price
        if order_type:
            data['order_type'] = order_type
        if trigger_price:
            data['trigger_price'] = trigger_price
        if validity:
            data['validity'] = validity.upper()
        if disclosed_quantity:
            data['disclosed_quantity'] = disclosed_quantity

        order_id = self._zerodha_rest_api.put(url=f"https://api.kite.trade/orders/{variety}/{order_id}", data=data)['data']['order_id']        
        return order_id

    def cancel_order(self, order_id, parent_order_id=None):
        """
        Cancel an open order.

        - `order_id`: Order ID.
        - `parent_order_id`: Parent order ID.
        """
        order_details = self.orders[self.orders['order_id'] == order_id]
        variety = order_details['variety'].values[0]
        variety = variety.lower()

        if parent_order_id is not None:
            data = {'parent_order_id': parent_order_id}
            order_id = self._zerodha_rest_api.delete(url=f"https://api.kite.trade/orders/{variety}/{order_id}", data=data)['data']['order_id']
        else:
            order_id = self._zerodha_rest_api.delete(url=f"https://api.kite.trade/orders/{variety}/{order_id}")['data']['order_id']        
        return order_id



    def buy_at_market_price(self, quantity=1, product='CNC'):
        """
        Buy at market price.

        - `quantity`: Quantity.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self.place_order(variety='regular', transaction_type='BUY', order_type='MARKET', product=product, quantity=quantity)

    def sell_at_market_price(self, quantity=1, product='CNC'):
        """
        Sell at market price.

        - `quantity`: Quantity.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self.place_order(variety='regular', transaction_type='SELL', order_type='MARKET', product=product, quantity=quantity)

    def buy_at_limit_price(self, price, quantity=1, variety='regular', product='CNC'):
        """
        Buy at limit price.

        - `price`: Price.
        - `quantity`: Quantity.
        - `variety`: Variety. {regular, co, amo, iceberg}
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self.place_order(variety=variety, transaction_type='BUY', order_type='LIMIT', product=product, quantity=quantity, price=price)

    def sell_at_limit_price(self, price, quantity=1, variety='regular', product='CNC'):
        """
        Sell at limit price.

        - `price`: Price.
        - `quantity`: Quantity.
        - 'variety`: Variety. {regular, co, amo, iceberg}
        - `product`: Product. {MIS, CNC, NRML}        
        """
        return self.place_order(variety=variety, transaction_type='SELL', order_type='LIMIT', product=product, quantity=quantity, price=price)



    def stop_loss_market_buy_order(self, price, quantity=1, product='CNC'):
        """
        Stop loss market buy order.

        - `price`: Price.
        - `quantity`: Quantity.
        - `product`: Product. {MIS, CNC, NRML}        
        """
        return self.place_order(variety='regular', transaction_type='BUY', order_type='SL-M', product=product, quantity=quantity, price=price)

    def stop_loss_market_sell_order(self, price, quantity=1, product='CNC'):
        """
        Stop loss market sell order.

        - `price`: price.
        - `quantity`: Quantity.
        - `product`: Product. {MIS, CNC, NRML}        
        """
        return self.place_order(variety='regular', transaction_type='SELL', order_type='SL-M', product=product, quantity=quantity, price=price)

    def stop_loss_limit_buy_order(self, price, trigger_price, quantity=1, variety='regular', product='CNC'):
        """
        Stop loss order.

        - `price`: Price.
        - `trigger_price`: Trigger price.
        - `quantity`: Quantity.
        - `variety`: Variety. {regular, co, amo, iceberg}
        - `product`: Product. {MIS, CNC, NRML}        
        """
        return self.place_order(variety=variety, transaction_type='BUY', order_type='SL', product=product, quantity=quantity, price=price, trigger_price=trigger_price)

    def stop_loss_limit_sell_order(self, price, trigger_price, quantity=1, variety='regular', product='CNC'):
        """
        Stop loss order.

        - `price`: Price.
        - `quantity`: Quantity.
        - `trigger_price`: Trigger price.
        - `variety`: Variety. {regular, co, amo, iceberg}
        - `product`: Product. {MIS, CNC, NRML}        
        """
        return self.place_order(variety=variety, transaction_type='SELL', order_type='SL', product=product, quantity=quantity, price=price, trigger_price=trigger_price)



    def cancel_pending_orders(self):
        """
        Cancel all pending orders.
        """
        for index, row in self.orders.iterrows():
            if row['status'] not in ['COMPLETE', 'CANCELLED', 'REJECTED', 'CANCELLED AMO', 'REJECTED AMO']:
                try:
                    self.cancel_order(order_id=row['order_id'])
                except Exception as e:
                    self._logger.error(f"Cancelling order failed for order_id: {row['order_id']}")

    def _limit_buy_at_nth_best_bid(self, quantity=1, product='CNC', n=1):
        """
        Place a limit buy order at the nth best bid price.

        - `quantity`: Quantity to buy.
        - `product`: Product. {MIS, CNC, NRML}
        - `n`: Queue number in the bid queue. {1,2,3,4,5}
        """
        bids = self.bids
        nth_best_bid = bids[n-1]
        price = nth_best_bid['price']

        order_id = self.buy_at_limit_price(price=price, quantity=quantity, variety='regular', product=product)
        return order_id

    def _limit_buy_at_nth_best_offer(self, quantity=1, product='CNC', n=1):
        """
        Place a limit buy order at the nth best offer price. This is a type of marketable limit order.

        - `quantity`: Quantity to buy.
        - `product`: Product. {MIS, CNC, NRML}
        - `n`: Queue number in the bid queue. {1,2,3,4,5}
        """
        offers = self.offers
        nth_best_offer = offers[n-1]
        price = nth_best_offer['price']

        order_id = self.buy_at_limit_price(price=price, quantity=quantity, variety='regular', product=product)
        return order_id

    def _limit_sell_at_nth_best_ask(self, quantity=1, product='CNC', n=1):
        """
        Place a limit sell order at the nth best ask price.

        - `quantity`: Quantity to sell.
        - `product`: Product. {MIS, CNC, NRML}
        - `n`: Queue number in the ask queue. {1,2,3,4,5}
        """
        asks = self.offers
        nth_best_ask = asks[n-1]
        price = nth_best_ask['price']

        order_id = self.sell_at_limit_price(price=price, quantity=quantity, variety='regular', product=product)
        return order_id

    def _limit_sell_at_nth_best_bid(self, quantity=1, product='CNC', n=1):
        """
        Place a limit sell order at the nth best ask price. This is a type of marketable limit order.

        - `quantity`: Quantity to sell.
        - `product`: Product. {MIS, CNC, NRML}
        - `n`: Queue number in the ask queue. {1,2,3,4,5}
        """
        bids = self.bids
        nth_best_bid = bids[n-1]
        price = nth_best_bid['price']

        order_id = self.sell_at_limit_price(price=price, quantity=quantity, variety='regular', product=product)
        return order_id



    def buy_at_best_bid_price(self, quantity=1, product='MIS'):
        """
        Place a limit buy order at the best bid price.

        - `quantity`: Quantity to buy.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_buy_at_nth_best_bid(quantity=quantity, product=product, n=1)

    def buy_at_second_best_bid_price(self, quantity=1, product='MIS'):
        """
        Place a limit buy order at the second best bid price.

        - `quantity`: Quantity to buy.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_buy_at_nth_best_bid(quantity=quantity, product=product, n=2)

    def buy_at_third_best_bid_price(self, quantity=1, product='MIS'):
        """
        Place a limit buy order at the third best bid price.

        - `quantity`: Quantity to buy.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_buy_at_nth_best_bid(quantity=quantity, product=product, n=3)

    def buy_at_fourth_best_bid_price(self, quantity=1, product='MIS'):
        """
        Place a limit buy order at the fourth best bid price.

        - `quantity`: Quantity to buy.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_buy_at_nth_best_bid(quantity=quantity, product=product, n=4)

    def buy_at_fifth_best_bid_price(self, quantity=1, product='MIS'):
        """
        Place a limit buy order at the fifth best bid price.

        - `quantity`: Quantity to buy.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_buy_at_nth_best_bid(quantity=quantity, product=product, n=5)



    def buy_at_best_offer_price(self, quantity=1, product='MIS'):
        """
        Place a limit buy order at the best offer price. This is a type of marketable limit order.

        - `quantity`: Quantity to buy.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_buy_at_nth_best_offer(quantity=quantity, product=product, n=1)
    
    def buy_at_second_best_offer_price(self, quantity=1, product='MIS'):
        """
        Place a limit buy order at the second best offer price. This is a type of marketable limit order.

        - `quantity`: Quantity to buy.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_buy_at_nth_best_offer(quantity=quantity, product=product, n=2)
    
    def buy_at_third_best_offer_price(self, quantity=1, product='MIS'):
        """
        Place a limit buy order at the third best offer price. This is a type of marketable limit order.

        - `quantity`: Quantity to buy.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_buy_at_nth_best_offer(quantity=quantity, product=product, n=3)
    
    def buy_at_fourth_best_offer_price(self, quantity=1, product='MIS'):
        """
        Place a limit buy order at the fourth best offer price. This is a type of marketable limit order.

        - `quantity`: Quantity to buy.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_buy_at_nth_best_offer(quantity=quantity, product=product, n=4)
    
    def buy_at_fifth_best_offer_price(self, quantity=1, product='MIS'):
        """
        Place a limit buy order at the fifth best offer price. This is a type of marketable limit order.

        - `quantity`: Quantity to buy.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_buy_at_nth_best_offer(quantity=quantity, product=product, n=5)



    def sell_at_best_offer_price(self, quantity=1, product='MIS'):
        """
        Place a limit sell order at the best offer price.

        - `quantity`: Quantity to sell.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_sell_at_nth_best_ask(quantity=quantity, product=product, n=1)

    def sell_at_second_best_offer_price(self, quantity=1, product='MIS'):
        """
        Place a limit sell order at the second best offer price.

        - `quantity`: Quantity to sell.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_sell_at_nth_best_ask(quantity=quantity, product=product, n=2)

    def sell_at_third_best_offer_price(self, quantity=1, product='MIS'):
        """
        Place a limit sell order at the third best offer price.

        - `quantity`: Quantity to sell.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_sell_at_nth_best_ask(quantity=quantity, product=product, n=3)

    def sell_at_fourth_best_offer_price(self, quantity=1, product='MIS'):
        """
        Place a limit sell order at the fourth best offer price.

        - `quantity`: Quantity to sell.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_sell_at_nth_best_ask(quantity=quantity, product=product, n=4)

    def sell_at_fifth_best_offer_price(self, quantity=1, product='MIS'):
        """
        Place a limit sell order at the fifth best offer price.

        - `quantity`: Quantity to sell.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_sell_at_nth_best_ask(quantity=quantity, product=product, n=5)



    def sell_at_best_bid_price(self, quantity=1, product='MIS'):
        """
        Place a limit sell order at the best bid price. This is a type of marketable limit order.

        - `quantity`: Quantity to sell.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_sell_at_nth_best_bid(quantity=quantity, product=product, n=1)
    
    def sell_at_second_best_bid_price(self, quantity=1, product='MIS'):
        """
        Place a limit sell order at the second best bid price. This is a type of marketable limit order.

        - `quantity`: Quantity to sell.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_sell_at_nth_best_bid(quantity=quantity, product=product, n=2)
    
    def sell_at_third_best_bid_price(self, quantity=1, product='MIS'):
        """
        Place a limit sell order at the third best bid price. This is a type of marketable limit order.

        - `quantity`: Quantity to sell.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_sell_at_nth_best_bid(quantity=quantity, product=product, n=3)
    
    def sell_at_fourth_best_bid_price(self, quantity=1, product='MIS'):
        """
        Place a limit sell order at the fourth best bid price. This is a type of marketable limit order.

        - `quantity`: Quantity to sell.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_sell_at_nth_best_bid(quantity=quantity, product=product, n=4)
    
    def sell_at_fifth_best_bid_price(self, quantity=1, product='MIS'):
        """
        Place a limit sell order at the fifth best bid price. This is a type of marketable limit order.

        - `quantity`: Quantity to sell.
        - `product`: Product. {MIS, CNC, NRML}
        """
        return self._limit_sell_at_nth_best_bid(quantity=quantity, product=product, n=5)



    def buy_at_midprice(self, quantity=1, product='MIS'):
        """
        Place a limit buy order at the mid price.

        - `quantity`: Quantity to buy.
        - `product`: Product. {MIS, CNC, NRML}
        """
        mid_price = self.midprice
        order_id = self.buy_at_limit_price(price=mid_price, quantity=quantity, variety='regular', product=product)
        return order_id

    def sell_at_midprice(self, quantity=1, product='MIS'):
        """
        Place a limit sell order at the mid price.

        - `quantity`: Quantity to sell.
        - `product`: Product. {MIS, CNC, NRML}
        """
        mid_price = self.midprice
        order_id = self.sell_at_limit_price(price=mid_price, quantity=quantity, variety='regular', product=product)
        return order_id

    def buy_at_vwap(self, quantity=1, product='MIS'):
        """
        Place a limit buy order at the vwap.

        - `quantity`: Quantity to buy.
        - `product`: Product. {MIS, CNC, NRML}
        """
        vwap = self.average_traded_price
        order_id = self.buy_at_limit_price(price=vwap, quantity=quantity, variety='regular', product=product)
        return order_id

    def sell_at_vwap(self, quantity=1, product='MIS'):
        """
        Place a limit sell order at the vwap.

        - `quantity`: Quantity to sell.
        - `product`: Product. {MIS, CNC, NRML}
        """
        vwap = self.average_traded_price
        order_id = self.sell_at_limit_price(price=vwap, quantity=quantity, variety='regular', product=product)
        return order_id



    # positions related methods
    @property
    def net_positions(self):
        """
        Get net position in this instrument.
        """
        positions = self._zerodha_rest_api.get(url='https://api.kite.trade/portfolio/positions')['data']
        if positions is None or len(positions) == 0:
            return None

        net = positions['net']
        net = pd.DataFrame(net)        
        if net.empty:
            return None

        net = net[(net['exchange']==self.exchange) & (net['tradingsymbol']==self.tradingsymbol)]
        if net.empty:
            return None

        net.reset_index(inplace=True, drop=True)
        return net

    @property
    def day_positions(self):
        """
        Get day positions.
        """
        positions = self._zerodha_rest_api.get(url='https://api.kite.trade/portfolio/positions')['data']
        if positions is None or len(positions) == 0:
            return None

        day = positions['day']
        day = pd.DataFrame(day)
        if day.empty:
            return None

        day = day[(day['exchange']==self.exchange) & (day['tradingsymbol']==self.tradingsymbol)]
        if day.empty:
            return None

        day.reset_index(inplace=True, drop=True)
        return day

    @property
    def open_positions(self):
        """
        Get open positions.
        """
        net_positions = self.net_positions
        if net_positions is None or net_positions.empty:
            return None

        open_positions = net_positions[net_positions['quantity'] != 0]
        if open_positions is None or open_positions.empty:
            return None

        open_positions.reset_index(inplace=True, drop=True)
        return open_positions

    @property
    def long_positions(self):
        """
        Get long positions.
        """
        net_positions = self.net_positions
        if net_positions is None or net_positions.empty:
            return None

        long_positions = net_positions[net_positions['quantity'] > 0]
        if long_positions is None or long_positions.empty:
            return None

        long_positions.reset_index(inplace=True, drop=True)
        return long_positions

    @property
    def short_positions(self):
        """
        Get short positions.
        """
        net_positions = self.net_positions
        if net_positions is None or net_positions.empty:
            return None

        short_positions = net_positions[net_positions['quantity'] < 0]
        if short_positions is None or short_positions.empty:
            return None

        short_positions.reset_index(inplace=True, drop=True)
        return short_positions

    @property
    def position_value(self):
        """
        Get the value of the positions in the instrument.
        """
        positions = self.net_positions
        if positions is None or positions.empty:
            return None

        return abs(positions.loc[0, 'value'])

    @property
    def position_pnl(self):
        """
        Get the pnl of the positions in the instrument
        """
        positions = self.net_positions
        if positions is None or positions.empty:
            return None

        return positions.loc[0, 'pnl']



    def add_position(self, quantity=1, price=None, position_type='long', variety='regular', product='MIS'):
        """
        Add a position. This assumes that requisite funds/margin are available.

        - `quantity`: Quantity.
        - `price`: Price.
        - `position_type`: Position type. {'long', 'short'}
        - `product`: Product. {'MIS', 'NRML'}
        - `variety`: Variety. {'regular', 'amo', 'bo'}
        """
        if position_type.lower() == 'long':
            if price is None:
                order_id = self.buy_at_market_price(quantity=quantity, product=product)
            else:
                order_id = self.buy_at_limit_price(price=price, quantity=quantity, variety=variety, product=product)
        elif position_type.lower() == 'short':
            if price is None:
                order_id = self.sell_at_market_price(quantity=quantity, product=product)
            else:
                order_id = self.sell_at_limit_price(price=price, quantity=quantity, variety=variety, product=product)
        else:
            raise TradeableInstrumentException(f"Invalid position type {position_type}.")

        return order_id

    def reduce_position(self, quantity=1, price=None, position_type='long', variety='regular', product='MIS'):
        """
        Reduce a position.

        - `quantity`: Quantity.
        - `price`: Price.
        - `position_type`: Position type. {'long', 'short'}
        - `product`: Product. {'MIS', 'NRML'}
        - `variety`: Variety. {'regular', 'amo', 'bo'}
        """
        if position_type.lower() == 'long':
            long_positions = self.long_positions
            if long_positions is None or long_positions.empty:
                raise TradeableInstrumentException(f"No long positions found for {self.id}.")

            if long_positions['quantity'][0] < quantity:
                raise TradeableInstrumentException(f"Not enough quantity in long positions found for {self.id}.")

            if price is None:
                order_id = self.sell_at_market_price(quantity=quantity, product=product)
            else:
                order_id = self.sell_at_limit_price(price=price, quantity=quantity, variety=variety, product=product)

        elif position_type.lower() == 'short':
            short_positions = self.short_positions
            if short_positions is None or short_positions.empty:
                raise TradeableInstrumentException(f"No short positions found for {self.id}.")

            if short_positions['quantity'][0] > -1*quantity:
                raise TradeableInstrumentException(f"Not enough quantity in short positions found for {self.id}.")

            if price is None:
                order_id = self.buy_at_market_price(quantity=-1*quantity, product=product)
            else:
                order_id = self.buy_at_limit_price(price=price, quantity=-1*quantity, variety=variety, product=product)
        else:
            raise TradeableInstrumentException(f"Invalid position type {position_type}.")

        return order_id

    def close_position(self, variety='regular'):
        """
        Close position.
        """
        open_positions = self.open_positions
        if open_positions is None or open_positions.empty:
            raise InstrumentException(f"No open positions to close for the instrument {self.id}")

        quantity = int(open_positions.loc[0, 'quantity']/self.lot_size)
        product = open_positions.loc[0, 'product']


        if quantity > 0:
            try:
                order_id = self.sell_at_best_bid_price(quantity=quantity, product=product)
            except Exception as e:
                order_id = self.sell_at_market_price(quantity=quantity, product=product)
        else:
            try:
                order_id = self.buy_at_best_offer_price(quantity=-1*quantity, product=product)                
            except Exception as e:
                order_id = self.buy_at_market_price(quantity=-1*quantity, product=quantity)
                

        return order_id

    def _trail_long_position2(self, order_id):
        """
        Trail long position.

        - `order_id`: Order ID.
        """
        order_details = self.orders[self.orders['order_id']==order_id]
        print(order_details)

        

    def _trail_long_position(self, trailing_stop_margin=10, target_margin=25, sleep_interval=10, in_loss_time_to_live=300, in_profit_time_to_live=600):
        """
        Trail long position.

        - `trailing_stop_margin`: Trailing stop margin.
        - `target_margin`: Target margin.
        - `sleep_interval`: Sleep interval.
        """
        stop_losses = []
        buy_price = self.orders[self.orders['transaction_type']=='BUY'].iloc[-1]['average_price']
        buy_trades = self.trades[self.trades['transaction_type']=='BUY']
        
        last_buy_trade = buy_trades.iloc[-1]
        last_buy_trade_time = last_buy_trade['fill_timestamp']
        last_buy_trade_time = datetime.strptime(last_buy_trade_time, '%Y-%m-%d %H:%M:%S')
        
        
        now = datetime.now()
        market_open_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)

        while market_open_time < datetime.now() < market_close_time:
            time_now = datetime.now()
            
            if self.long_positions is None:
                self._logger.warning(f"No long positions found for {self.id}.")
                break

            best_offer_price = self.best_offer['price'] ## instead of comparing with LTP, compare with best offer price
            stop_losses.append(buy_price - trailing_stop_margin)
            if best_offer_price > buy_price+1:
                stop_losses.append(buy_price)

            trailing_stop_loss = max(stop_losses)

            if best_offer_price < trailing_stop_loss:
                self.close_position()
                stop_losses.clear()
                break
            elif best_offer_price > buy_price+target_margin:
                self.close_position()
                stop_losses.clear()
                break
            elif best_offer_price < buy_price and (time_now - last_buy_trade_time).seconds > in_loss_time_to_live:
                self.close_position()
                stop_losses.clear()
                break
            elif best_offer_price >= buy_price and (time_now - last_buy_trade_time).seconds > in_profit_time_to_live:
                self.close_position()
                stop_losses.clear()
                break
            else:
                stop_losses.append(best_offer_price - trailing_stop_margin)
                trailing_stop_loss = max(stop_losses)
                if best_offer_price < buy_price:
                    print(f"{self.id}: \t Making Losses: {round(best_offer_price - buy_price, 2)} LTP: {round(best_offer_price,2)} Trailing SL: {round(trailing_stop_loss,2)} Buy Price: {round(buy_price,2)} Target: {round(buy_price+target_margin,2)} In Loss TTL: {in_loss_time_to_live - (time_now - last_buy_trade_time).seconds} In Profit TTL: {in_profit_time_to_live - (time_now - last_buy_trade_time).seconds}")
                else:
                    print(f"{self.id}: \t Making Profits: {round(best_offer_price - buy_price, 2)} LTP: {round(best_offer_price,2)} Trailing SL: {round(trailing_stop_loss,2)} Buy Price: {round(buy_price,2)} Target: {round(buy_price+target_margin,2)} In Loss TTL: {in_loss_time_to_live - (time_now - last_buy_trade_time).seconds} In Profit TTL: {in_profit_time_to_live - (time_now - last_buy_trade_time).seconds}")

                
                if sleep_interval > 0:
                    time.sleep(sleep_interval)             

    def trail_long_position(self, trailing_stop_margin=10, target_margin=25, sleep_interval=10, in_loss_time_to_live=300, in_profit_time_to_live=600):
        """
        Trail long position.

        - `trailing_stop_margin`: Trailing stop margin.
        - `target_margin`: Target margin.
        - `sleep_interval`: Sleep interval.
        """
        thread = threading.Thread(target=self._trail_long_position, args=(trailing_stop_margin, target_margin, sleep_interval, in_loss_time_to_live, in_profit_time_to_live))
        thread.start()        
        return thread

    def _trail_short_position(self, trailing_stop_margin=10, target_margin=25, sleep_interval=10):
        """
        Trail a short position

        - `trailing_stop_margin`: Trailing stop margin.
        - `target_margin`: Target margin.
        - `sleep_interval`: Sleep interval.
        """
        stop_losses = []
        sell_price = self.orders[self.orders['transaction_type']=='SELL'].iloc[-1]['average_price']
        

        now = datetime.now()
        market_open_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        while market_open_time < datetime.now() < market_close_time:
            if self.short_positions is None:
                self._logger.warning("No short positions found. Exiting.")
                break

            best_bid_price = self.best_bid['price']
            stop_losses.append(sell_price + trailing_stop_margin)
            trailing_stop_loss = min(stop_losses)

            if best_bid_price > trailing_stop_loss:
                self.close_position()
                stop_losses.clear()                
                break
            elif best_bid_price < sell_price-target_margin:
                self.close_position()
                stop_losses.clear()                
                break
            else:
                stop_losses.append(best_bid_price + trailing_stop_margin)
                trailing_stop_loss = min(stop_losses)
                self._logger.info(f"{self.exchange} {self.tradingsymbol}: \tLTP: {round(best_bid_price,2)} Trailing SL: {round(trailing_stop_loss,2)} Buy Price: {round(sell_price,2)} Target: {round(sell_price-target_margin, 2)}")
                if sleep_interval > 0:
                    time.sleep(sleep_interval)

    def trail_short_position(self, trailing_stop_margin=10, target_margin=25, sleep_interval=10):
        """
        Trail short position.

        - `trailing_stop_margin`: Trailing stop margin.
        - `target_margin`: Target margin.
        - `sleep_interval`: Sleep interval.
        """
        thread = threading.Thread(target=self._trail_short_position, args=(trailing_stop_margin, target_margin, sleep_interval))
        thread.start()
        return thread



    def go_long(self, quantity=1, price=None, variety='regular', product='MIS'):
        """
        Go long.

        - `quantity`: Quantity.
        - `price`: Price.
        - `variety`: Variety. {'regular', 'co', 'iceberg'}
        - `product`: Product type. {'MIS', 'CNC', 'NRML'}        
        """
        if price is None:
            order_id = self.buy_at_market_price(quantity=quantity, product=product)
        else:
            order_id = self.buy_at_limit_price(price=price, quantity=quantity, variety=variety, product=product)
            
        return order_id

    def go_short(self, quantity=1, price=None, variety='regular', product='MIS'):
        """
        Go short.

        - `quantity`: Quantity.
        - `price`: Price.
        - `variety`: Variety. {'regular', 'co', 'iceberg'}
        - `product`: Product type. {'MIS', 'CNC', 'NRML'} 
        """
        if price is None:
            order_id = self.sell_at_market_price(quantity=quantity, product=product)
        else:
            order_id = self.sell_at_limit_price(price=price, quantity=quantity, variety=variety, product=product)
        
        return order_id

    def go_long_and_trail_stop(self, quantity=1, price=None, variety='regular', product='MIS', trailing_stop_margin=10, target_margin=25, sleep_interval=10):
        """
        Go long and trail stop.

        - `quantity`: Quantity.
        - `price`: Price.
        - `variety`: Variety. {'regular', 'co', 'iceberg'}
        - `product`: Product type. {'MIS', 'CNC', 'NRML'}   
        - `trailing_stop_margin`: Trailing stop margin.
        - `target_margin`: Target margin.
        - `sleep_interval`: Sleep interval.
        """
        order_id = self.go_long(quantity=quantity, price=price, variety=variety, product=product)
        self.trail_long_position(trailing_stop_margin=trailing_stop_margin, target_margin=target_margin, sleep_interval=sleep_interval)

    def go_short_and_trail_stop(self, quantity=1, price=None, variety='regular', product='MIS', trailing_stop_margin=10, target_margin=25, sleep_interval=10):
        """
        Go short and trail stop.

        - `quantity`: Quantity.
        - `price`: Price.
        - `product`: Product type. {'MIS', 'CNC', 'NRML'}
        - `variety`: Variety. {'regular', 'co', 'iceberg'}
        - `trailing_stop_margin`: Trailing stop margin.
        - `target_margin`: Target margin.
        - `sleep_interval`: Sleep interval.
        """
        order_id = self.go_short(quantity=quantity, price=price, variety=variety, product=product)
        self.trail_short_position(trailing_stop_margin=trailing_stop_margin, target_margin=target_margin, sleep_interval=sleep_interval)

class NonTradeableInstrument(Instrument):
    """
    NonTradeableInstrument class encapsulates the functionality of a non-tradeable instrument.
    """

    def __init__(self, id):
        """
        NonTradeableInstrument class encapsulates the functionality of a non-tradeable instrument.

        - `id`: is the instrument id. It is of the format `exchange:tradingsymbol`.
        """
        super().__init__(id=id)

        if self.segment != 'INDICES':
            raise NonTradeableInstrumentException(f"{id} is not a non-tradeable instrument.")

    def __repr__(self):
        """
        Returns a string representation of the non-tradeable instrument.
        """
        return f"NonTradeableInstrument(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the non-tradeable instrument.
        """
        return f"NonTradeableInstrument(id=\"{self._id}\")"
    
    # market price methods
    @property
    def last_traded_price(self):
        """
        Returns the last traded price.
        """
        # print(self.instrument)
        ltp = self._zerodha_rest_api.get(url=f"https://api.kite.trade/quote/ltp?i={self.instrument_token}")
        return ltp['data'][str(self.instrument_token)]['last_price']
    
    @property
    def ohlc(self):
        """
        Returns OHLC data.
        """
        ohlc = self._zerodha_rest_api.get(url=f"https://api.kite.trade/quote/ohlc?i={self.instrument_token}")
        return ohlc['data'][str(self.instrument_token)]['ohlc']
    
    @property
    def quote(self):
        """
        Returns quote data.
        """
        quote = self._zerodha_rest_api.get(url=f"https://api.kite.trade/quote?i={self.instrument_token}")
        return quote['data'][str(self.instrument_token)]

    @property
    def change(self):
        """
        Returns change.
        """
        return self.quote['net_change']


class Futures(TradeableInstrument):
    """
    Futures class encapsulates the functionality of a futures contract.
    """

    def __init__(self, id, underlying_asset=None):
        """
        Futures class encapsulates the functionality of a futures contract.

        - `id`: is the instrument id. It is of the format `exchange:tradingsymbol`.
        - `underlying_asset`: is the underlying asset. It is of the format `exchange:tradingsymbol`.
        """
        super().__init__(id=id)
        self._underlying_asset = underlying_asset

        if self.instrument_type != 'FUT':
            raise FuturesException(f"Instrument {id} is not a futures contract.")

        self._risk_free_rate = float(json.loads(self._cache.get('risk_free_rate')))

    def __repr__(self):
        """
        Returns a string representation of the futures contract.
        """
        return f"Futures(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the futures contract.
        """
        return f"Futures(id=\"{self._id}\")"
    
    @property
    def expiry(self):
        """
        Get expiry.
        """
        return self.instrument['expiry']

    @property
    def days_to_expiry(self):
        """
        Get days to expiry.
        """
        return (datetime.strptime(self.expiry, "%Y-%m-%d") - datetime.now()).days

    @property
    def underlying(self):
        """
        Get underlying.
        """
        return self._underlying_asset

class Option(TradeableInstrument):
    """
    Option class encapsulates the functionality of an option contract.
    """

    def __init__(self, id, underlying_asset=None):
        """
        Option class encapsulates the functionality of an option contract.

        - `id`: is the id of the instrument. Format: `exchange:tradingsymbol`.
        - `underlying_asset`: is the underlying asset. It is of the format `exchange:tradingsymbol`.
        """
        super().__init__(id=id)

        if self.instrument_type not in ['CE', 'PE']:
            raise OptionException(f"Instrument {id} is not an options contract.")
        
        self._underlying_asset = underlying_asset
        risk_free_rate = float(json.loads(self._cache.get('risk_free_rate')))
        self._risk_free_rate = risk_free_rate

    def __repr__(self):
        """
        Returns a string representation of the option contract.
        """
        return f"Option(id=\"{self._id}\")"

    def __str__(self):
        """
        Returns a string representation of the option contract.
        """
        return f"Option(id=\"{self._id}\")"

    @property
    def option_type(self):
        """
        Get option type.
        """
        if self.instrument_type == 'CE':
            return 'call'
        elif self.instrument_type == 'PE':
            return 'put'
        else:
            raise OptionException(f"Instrument {self.id} is not an option contract.")

    @property
    def underlying(self):
        """
        Get underlying.
        """
        return self._underlying_asset

    @property
    def expiry(self):
        """
        Get expiry.
        """
        return self.instrument['expiry']

    @property
    def days_to_expiry(self):
        """
        Get days to expiry.
        """
        return (datetime.strptime(self.expiry, "%Y-%m-%d") - datetime.now()).days

    @property
    def strike(self):
        """
        Get strike.
        """
        return self.instrument['strike']

    @property
    def volatility_of_underlying(self):
        """
        Get volatility of underlying.
        """
        return self.underlying.returns_standard_deviation(period='one_year', interval='day')*math.sqrt(252)

    @property
    def _black_scholes_model(self):
        """
        Get output form Black Scholes Merton model.        
        """
        if self.option_type == 'call':
            type = 'c'
        elif self.option_type == 'put':
            type = 'p'

        if self.underlying.segment == 'INDICES':
            underlying_ltp = self.underlying.prices(period='two_days', interval='minute')
            underlying_ltp = underlying_ltp.iloc[-1]['close']        
        else:
            underlying_ltp = self.underlying.last_traded_price

        bsm = op.black_scholes(K=self.strike, St=underlying_ltp, r=self._risk_free_rate, t=self.days_to_expiry, v=self.volatility_of_underlying*100, type=type)
        # print(f"K={self.strike}, St={underlying_ltp}, r={self._risk_free_rate}, t={self.days_to_expiry}, v={self.volatility_of_underlying*100}, type={type}")
        return bsm

    @property
    def black_scholes_price(self):
        """
        Get Black Scholes Merton model price.
        """
        return self._black_scholes_model['value']['option value']

    @property
    def intrinsic_value(self):
        """
        Get intrinsic value.
        """
        return self._black_scholes_model['value']['intrinsic value']

    @property
    def time_value(self):
        """
        Get time value.
        """
        return self._black_scholes_model['value']['time value']

    @property
    def delta(self):
        """
        Get delta.
        """
        return self._black_scholes_model['greeks']['delta']

    @property
    def gamma(self):
        """
        Get gamma.
        """
        return self._black_scholes_model['greeks']['gamma']

    @property
    def theta(self):
        """
        Get theta.
        """
        return self._black_scholes_model['greeks']['theta']

    @property
    def vega(self):
        """
        Get vega.
        """
        return self._black_scholes_model['greeks']['vega']

    @property
    def rho(self):
        """
        Get rho.
        """
        return self._black_scholes_model['greeks']['rho']


class Index(NonTradeableInstrument):
    """
    Index class encapsulates the functionality of an index of an asset or commodity.
    """
    def __init__(self, id):
        """
        Index class encapsulates the functionality of an index of an asset or commodity.

        - `id`: is the id of the index. Format is exchange:tradingsymbol. Default is NSE:NIFTY 50.
        """
        super().__init__(id=id)

        if self.segment != 'INDICES':
            raise IndexException(f"{self.exchange} {self.tradingsymbol} is not an index.")

    def __repr__(self):
        """
        Returns a string representation of the Index.
        """
        return f"Index(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the Index.
        """
        return f"Index(id=\"{self._id}\")"

class IndexFutures(Futures):
    """
    IndexFutures class encapsulates the functionality of an index futures contract.
    """

    def __init__(self, id, underlying_asset=None):
        """
        IndexFutures class encapsulates the functionality of an index futures contract.

        - `id`: is the id of the instrument. Format: `NFO:NIFTY23AUGFUT`.
        - `underlying_asset`: is the underlying asset. It is of the format `exchange:tradingsymbol`.
        """
        super().__init__(id=id, underlying_asset=underlying_asset)

    def __repr__(self):
        """
        Returns a string representation of the Index Futures.
        """
        return f"IndexFutures(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the Index Futures.
        """
        return f"IndexFutures(id=\"{self._id}\")"

class IndexOption(Option):
    """
    IndexOption class encapsulates the functionality of an index option contract.
    """

    def __init__(self, id, underlying_asset=None):
        """
        IndexOption class encapsulates the functionality of an index option contract.

        - `id`: is the id of the instrument. Format: `NFO:NIFTY23AUG18000CE`.
        - `underlying_asset`: is the underlying asset. It is of the format `exchange:tradingsymbol`.
        """
        super().__init__(id=id, underlying_asset=underlying_asset)

    def __repr__(self):
        """
        Returns a string representation of the Index Option.
        """
        return f"IndexOption(id=\"{self._id}\")"
    
    def __str__(self):
        """
        Returns a string representation of the Index Option.
        """
        return f"IndexOption(id=\"{self._id}\")"
