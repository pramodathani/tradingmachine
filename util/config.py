from urllib.parse import quote_plus

redis_config = {
    'host': '192.168.1.2',
    'port': 6379,
    'db': 0
}

mongodb_config = {
    'host': '192.168.1.2',
    'port': 27017,
    'db': 'TradingMachine',
    'connection_string': f'mongodb://192.168.1.2:27017/'
}