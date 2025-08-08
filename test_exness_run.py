import json
import sys
sys.path.append('sai_ultra_pro')
from main import test_exness

with open('sai_ultra_pro/config/config.json') as f:
    c = json.load(f)

api_key = c['api_keys']['EXNESS_API_KEY']
api_secret = c['api_keys']['EXNESS_API_SECRET']
server = c['api_keys']['EXNESS_SERVER']
platform = c['api_keys']['EXNESS_PLATFORM']
symbol = 'EURUSD'

test_exness(api_key, api_secret, server, platform, symbol)
