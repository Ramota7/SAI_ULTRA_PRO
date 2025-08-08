import requests

def obtener_orderbook_binance(symbol, depth=20):
    url = f'https://api.binance.com/api/v3/depth?symbol={symbol}&limit={depth}'
    r = requests.get(url)
    data = r.json()
    return data['bids'], data['asks']

def estimar_slippage_y_liquidez(symbol, size, side='buy', max_slippage=0.003):
    """
    Evalúa la profundidad del libro de órdenes y estima el slippage para el tamaño dado.
    Descarta la señal si el slippage estimado es mayor a 0.3% o la liquidez es insuficiente.
    """
    bids, asks = obtener_orderbook_binance(symbol)
    book = asks if side == 'buy' else bids
    size_restante = size
    precio_medio = 0
    total_cost = 0
    total_qty = 0
    for price, qty in book:
        price = float(price)
        qty = float(qty)
        if qty >= size_restante:
            total_cost += size_restante * price
            total_qty += size_restante
            break
        else:
            total_cost += qty * price
            total_qty += qty
            size_restante -= qty
    if size_restante > 0:
        # No hay suficiente liquidez
        return False, None, 'liquidez insuficiente'
    precio_medio = total_cost / total_qty if total_qty > 0 else 0
    mejor_precio = float(book[0][0])
    slippage = abs(precio_medio - mejor_precio) / mejor_precio if mejor_precio > 0 else 0
    if slippage > max_slippage:
        return False, slippage, 'slippage alto'
    return True, slippage, 'ok'
