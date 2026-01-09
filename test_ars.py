import yfinance as yf
try:
    print("Fetching ARS=X...")
    ticker = yf.Ticker("ARS=X")
    hist = ticker.history(period="1d")
    print(hist)
    if not hist.empty:
        print(f"Last price: {hist['Close'].iloc[-1]}")
    else:
        print("Empty history")
except Exception as e:
    print(f"Error: {e}")
