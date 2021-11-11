import websocket
import json
import pprint
import talib
from collections import deque
import pandas as pd
import numpy as np
import hashlib
import urllib.parse
import urllib.request
import hmac
import requests
import datetime
import time
import testnet_key # testnet_key.py containing:
# TESTKEY = 'xxx'
# TESTSECRET = 'xxx'
#import config <- same kind of file with actual API key and secret - not needed while operating on testnet
# how to get testnet api key:
# https://academy.binance.com/en/articles/binance-api-series-pt-1-spot-trading-with-postman

#sources
#wss://stream.binance.com:9443
#wss://stream>
#https://www.youtube.com/watch?v=GdlFhF6gjKo&list=PLvzuUVysUFOuB1kJQ3S2G-nB7_nHhD7Ay&index=11


TRADE_SYMBOL = 'BNBBUSD'
SOCKET = "wss://stream.binance.com:9443/ws/{}@kline_1m".format(TRADE_SYMBOL.lower())
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
TRADE_QUANTITY = 1.
testing_mode = True
closes = np.array([])

if testing_mode:
    base_url = 'https://testnet.binance.vision/'
    secret = bytes(testnet_key.TESTSECRET.encode('utf-8'))
    theKey = testnet_key.TESTKEY
else:
    base_url = 'https://api.binance.us/'
    secret = bytes(config.API_SECRET.encode('utf-8'))
    theKey = config.API_KEY
    # if you want to do this, create a config.py file containing actual key and secret

#prev_vals = deque(maxlen=4)
#closes = deque(maxlen = RSI_PERIOD+10) #keeping a few extra values, might be useful later?

in_position = False

def on_open(ws):
    print('opened connection')

def on_close(ws):
    print('closed connection')

def on_message(ws, message):
    global closes
    global in_position
    #print('received message')
    json_message = json.loads(message)
    #pprint.pprint(json_message)
    candle = json_message['k']
    is_candle_closed = candle['x']
    close = candle['c']
    #prev_vals.append(float(close))
    #print("prev_vals = {}".format(prev_vals))

    if is_candle_closed:
        print("candle closed at {}".format(close))
        if len(closes) < RSI_PERIOD:
            endTime=time.time()*1000
            startTime=endTime-60000*(RSI_PERIOD+1)
            apiStr = 'https://api3.binance.com/api/v3/klines?symbol={}&interval={}&startTime={}&endTime={}'
            apiStr = apiStr.format(TRADE_SYMBOL, '1m', int(startTime), int(endTime))
            names = ['time', 'open', 'high', 'low', 'close', 'volume', 'closeTime', 'quoteAssetVolume', 'nTrades',
                     'takerBuyBaseAssetVol', 'takerBuyQuoteAssetVol', 'ignore']
            hist_data = pd.DataFrame(requests.get(apiStr).json(), columns=names).astype({'close':'float'})
            closes = np.append(closes, np.array(hist_data['close']))
        closes = np.append(closes, float(close))

        if len(closes) > RSI_PERIOD:
            #np_closes = np.double(closes)
            rsi = talib.RSI(closes, RSI_PERIOD)
            print("all RSIs calculated so far")
            print(rsi)
            last_rsi = rsi[-1]
            print("the current RSI is {}".format(last_rsi))
            if last_rsi > RSI_OVERBOUGHT:
                if in_position:
                    print("sell! " + str(datetime.datetime.now()))
                    place_order('SELL', TRADE_QUANTITY, TRADE_SYMBOL, 'MARKET', rcvWindow=5000)
                    in_position = False
                else:
                    print("it's overbought but we dont own any - nothing to do")
            elif last_rsi < RSI_OVERSOLD:
                if in_position:
                    print("it's oversold but you already own it - nothing to do")
                else:
                    print("Buy! " + str(datetime.datetime.now()))
                    place_order('BUY', TRADE_QUANTITY, TRADE_SYMBOL, 'MARKET', rcvWindow=5000, timeInForce='GTC')
                    in_position = True
def place_order(side, quantity, symbols, type, rcvWindow=5000, timeInForce='GTC'):
    #example: selling one LTC for BTC at market price
    #params = {
    #    'symbol': 'LTCBTC',
    #    'recvWindow': 50000,
    #    'side': 'SELL',
    #    'type': 'MARKET',
    #    'timestamp': int(time.time() * 1000),
    #    'quantity': 1.0,
    #}
    url = base_url + 'api/v3/order'
    headers = {'X-MBX-APIKEY': theKey}
    params = {
        'side': side,
        'quantity': quantity,
        'symbol': symbols,
        'type': type,
        'recvWindow': rcvWindow,  # time window for the order. default is 5000, max is 60000 (=1min)
        #'timeInForce': timeInForce,
        'timestamp': int(time.time() * 1000),
    }
    #secret = bytes(secret.encode('utf-8'))
    signature = hmac.new(secret, urllib.parse.urlencode(params).encode('utf-8'), hashlib.sha256).hexdigest()
    params['signature'] = signature
    #data = urllib.parse.urlencode(params).encode('ascii')
    response = requests.post(url, params=params, headers=headers)
    print(response.json())

def get_account_balance():
    # Setup header with API_KEY
    headers = {'X-MBX-APIKEY': theKey}
    # Params requires timestamp in MS
    params = {'timestamp': int(time.time() * 1000)}
    # Encode params into url
    url = base_url+'api/v3/account?'+ urllib.parse.urlencode(params)
    # Create a HMAC SHA256 signature
    signature = hmac.new(secret, urllib.parse.urlencode(params).encode('utf-8'), hashlib.sha256).hexdigest()
    # Add signature to url
    url += f'&signature={signature}'
    # Make a request
    req = urllib.request.Request(url, headers=headers)
    # try something like this
    # respses = requests.get(url, params=params, headers=headers)
    # Read and decode response
    response = urllib.request.urlopen(req).read().decode('utf-8')
    # Convert to json
    response_json = json.loads(response)
    # Print balances for all coins not at 0
    for entry in response_json['balances']:
        if entry['free'] == '0.00000000':
            continue
        print(entry)

get_account_balance()
ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
ws.run_forever()