import json
from sai_ultra_pro.main import validar_api_binance

conf = json.load(open('sai_ultra_pro/config/config.json'))
validar_api_binance(conf['api_keys']['BINANCE_API_KEY'], conf['api_keys']['BINANCE_API_SECRET'])
