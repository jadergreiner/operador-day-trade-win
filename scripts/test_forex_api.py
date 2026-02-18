"""Test AwesomeAPI forex data availability."""
import requests
import json

pairs = [
    'EUR-USD', 'GBP-USD', 'AUD-USD', 'NZD-USD', 'CAD-USD', 'CNY-USD',
    'MXN-USD', 'ZAR-USD', 'TRY-USD', 'CLP-USD', 'CHF-USD', 'JPY-USD'
]
url = 'https://economia.awesomeapi.com.br/json/last/' + ','.join(pairs)
print(f'URL: {url}')

r = requests.get(url, timeout=10)
print(f'Status: {r.status_code}')

data = r.json()
print(f'Pares retornados: {list(data.keys())}')
print()

for key, val in data.items():
    bid = val.get('bid', 'N/A')
    ask = val.get('ask', 'N/A')
    high = val.get('high', 'N/A')
    low = val.get('low', 'N/A')
    open_val = val.get('open', 'N/A')
    pct = val.get('pctChange', 'N/A')
    name = val.get('name', 'N/A')
    ts = val.get('create_date', 'N/A')
    print(f'  {key}: bid={bid}, open={open_val}, pct={pct}%, name={name}, ts={ts}')

# Verificar pares faltantes
returned_keys = set(data.keys())
expected_keys = {p.replace('-', ''): p for p in pairs}
missing = [p for k, p in expected_keys.items() if k not in returned_keys]
if missing:
    print(f'\nPares NAO disponíveis: {missing}')
    # Tentar pares invertidos (USD-XXX) para os faltantes
    for p in missing:
        parts = p.split('-')
        inv = f'{parts[1]}-{parts[0]}'
        print(f'  Tentando invertido: {inv}')
        r2 = requests.get(f'https://economia.awesomeapi.com.br/json/last/{inv}', timeout=5)
        if r2.status_code == 200:
            d2 = r2.json()
            for k2, v2 in d2.items():
                print(f'    {k2}: bid={v2.get("bid")}, open={v2.get("open")}')
        else:
            print(f'    Erro: {r2.status_code}')
else:
    print('\nTodos os 12 pares disponíveis!')
