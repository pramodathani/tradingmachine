import os
from dotenv import load_dotenv
from urllib.parse import quote_plus, quote

load_dotenv()
redis_pwd = os.getenv("REDIS_PASSWORD")
mongodb_pwd = os.getenv("MONGODB_PASSWORD")

redis_config = {
    'host': '192.168.1.2',
    'port': 6379,
    'db': 0,
    'username': 'default',
    'password': redis_pwd
}

mongodb_config = {
    'host': '192.168.1.2',
    'port': 27017,
    'db': 'TradingMachine',
    'username': 'admin',
    'password': mongodb_pwd,
    'connection_string': f'mongodb://{quote_plus('TradingMachine')}:{quote_plus(mongodb_pwd)}@192.168.1.2:27017/'
}
