"""Test AwesomeAPI fields and alternative endpoints."""
import requests
import json

# 1) Check all fields in EUR-USD response
r = requests.get('https://economia.awesomeapi.com.br/json/last/EUR-USD', timeout=10)
data = r.json()
print("=== ALL FIELDS EUR-USD ===")
for k, v in data['EURUSD'].items():
    print(f"  {k}: {v}")

# 2) Try daily endpoint (has open/close)
print("\n=== DAILY ENDPOINT ===")
r2 = requests.get('https://economia.awesomeapi.com.br/json/daily/EUR-USD/2', timeout=10)
daily = r2.json()
for d in daily:
    print(f"  bid={d.get('bid')}, ask={d.get('ask')}, high={d.get('high')}, low={d.get('low')}, varBid={d.get('varBid')}, pctChange={d.get('pctChange')}, ts={d.get('create_date')}")

# 3) Try closing endpoint for opening reference
print("\n=== USD-BRL (test inverse) ===")
r3 = requests.get('https://economia.awesomeapi.com.br/json/last/USD-BRL', timeout=10)
usd = r3.json()
for k, v in usd['USDBRL'].items():
    print(f"  {k}: {v}")
