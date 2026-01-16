"""Quick debug script for ThinkMarkets symbol"""
import MetaTrader5 as mt5

# ThinkMarkets config
path = "C:/Program Files/Pepperstone MetaTrader 5/terminal64.exe"
server = "ThinkMarkets-Demo"
login = 74444
password = "YS#Dv1uP2k"
symbol = "XAUUSDx"

# Connect
mt5.shutdown()
if mt5.initialize(path=path, login=login, password=password, server=server):
    print(f"Connected to {server}")

    # Get symbol info
    info = mt5.symbol_info(symbol)
    if info:
        print(f"\nSymbol: {symbol}")
        print(f"  Visible: {info.visible}")
        print(f"  Point: {info.point}")
        print(f"  Digits: {info.digits}")
        print(f"  Spread (from info): {info.spread}")

        # Select symbol
        mt5.symbol_select(symbol, True)

        # Get tick
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            print(f"\nTick data:")
            print(f"  Bid: {tick.bid}")
            print(f"  Ask: {tick.ask}")
            print(f"  Spread: {tick.ask - tick.bid}")
            print(f"  Time: {tick.time}")
        else:
            print("No tick data!")
    else:
        print(f"Symbol {symbol} not found!")

    mt5.shutdown()
else:
    print(f"Failed to connect: {mt5.last_error()}")
