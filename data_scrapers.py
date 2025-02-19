import yfinance as yf
import requests
from datetime import datetime, timedelta


def get_treasury_yield():
    bond = yf.Ticker("^TNX")  # 10-Year Treasury Yield Index
    return bond.history(period="1d")["Close"].iloc[-1]


def assess_yield_curve():
    """
    Check yield curve inversion (10Y - 2Y spread)
    """
    ten_year = yf.Ticker("^TNX").history(period="1d")["Close"].iloc[-1]
    two_year = yf.Ticker("^IRX").history(period="1d")["Close"].iloc[-1]
    spread = ten_year - two_year
    return spread, "Inverted" if spread < 0 else "Normal"


def get_stock_quotes():
    """
    Fetch latest stock quotes including daily price changes and percentage changes using Yahoo Finance API.
    """
    tickers = {
        "S&P 500": "^GSPC",
        "Dow Jones": "^DJI",
        "Nasdaq": "^IXIC"
    }
    
    stock_data = {}

    for name, symbol in tickers.items():
        try:
            stock = yf.Ticker(symbol)
            today = datetime.today().strftime('%Y-%m-%d')

            # Fetch latest market data
            hist = stock.history(period="2d")  # Get last 2 days to ensure previous close is available

            if len(hist) < 2:  # Ensure we have at least two days of data
                print(f"⚠️ Not enough data for {name}. Using available data.")
                last_price = hist["Close"].iloc[-1]
                prev_close = last_price
            else:
                last_price = hist["Close"].iloc[-1]  # Latest close
                prev_close = hist["Close"].iloc[-2]  # Previous close

            change = last_price - prev_close
            change_pct = (change / prev_close) * 100
            
            stock_data[name] = {
                "price": round(last_price, 2),
                "prev_close": round(prev_close, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2)
            }

        except Exception as e:
            print(f"❌ ERROR fetching {name}: {e}")
            stock_data[name] = {"price": "N/A", "prev_close": "N/A", "change": "N/A", "change_pct": "N/A"}
    
    return stock_data


# if __name__ == "__main__":
#     stocks = get_stock_quotes()
#     print(stocks)