# RSI_bot_binance

Trades a currency pair based on the RSI indicator, which is re-calculated. The time scale and currency pair can be modified.
This ia not meant as an actual practical trading method or strategy and operates on the binance testnet by default (can be set to trade on an actual account though).

Make sure to add your API and key, there is a template file testnet_key_template.py, where you can paste your information and rename the file to testnet_key.py.

It automatically grabs recent data from binance in order to calculate the RSI and make a decision on whether to buy, sell or none of the above.
