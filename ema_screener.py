# Filename: ema_screener.py
import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import datetime as dt

# --------------------------
# Streamlit UI
# --------------------------
st.title("EMA + Earnings Reaction Screener")

# User inputs
ticker_list = st.text_area("Enter tickers (comma separated)", "AAPL,MSFT,GOOGL,AMZN,TSLA")
near_pct = st.number_input("Near EMA tolerance (%)", value=2.0)
earnings_positive_threshold = st.number_input("Min % positive earnings (last 10)", value=60.0)
years_hold = st.number_input("Years without falling below EMA", value=1)

tickers = [t.strip().upper() for t in ticker_list.split(",")]

# --------------------------
# Helper functions
# --------------------------
def get_ema(df, period):
    return df['Close'].ewm(span=period, adjust=False).mean()

def earnings_positive_reactions(ticker):
    try:
        stock = yf.Ticker(ticker)
        cal = stock.calendar
        hist_earnings = stock.earnings_dates(limit=12)  # last ~3 years
        hist = hist_earnings.sort_index(ascending=False).head(10)
        
        count_positive = 0
        for date in hist.index:
            date = date.to_pydatetime()
            df = yf.download(ticker, start=date - pd.Timedelta(days=5), end=date + pd.Timedelta(days=5))
            if len(df) >= 3:
                before_close = df.loc[df.index < date].iloc[-1]['Close']
                after_close = df.loc[df.index > date].iloc[0]['Close']
                if after_close > before_close:
                    count_positive += 1
        return (count_positive / 10) * 100
    except:
        return None

def passes_ema_hold(df, ema_period, years):
    start_date = df.index[-1] - pd.Timedelta(days=years * 365)
    df_recent = df[df.index >= start_date]
    ema = get_ema(df_recent, ema_period)
    return (df_recent['Close'] >= ema).all()

# --------------------------
# Main Screener
# --------------------------
results = []

for ticker in tickers:
    try:
        df = yf.download(ticker, period="3y", interval="1d")
        if df.empty:
            continue
        
        ema9 = get_ema(df, 9)
        ema21 = get_ema(df, 21)
        
        # Latest close
        close = df['Close'].iloc[-1]
        ema9_val = ema9.iloc[-1]
        ema21_val = ema21.iloc[-1]
        
        near_ema9 = abs(close - ema9_val) / ema9_val * 100 <= near_pct
        near_ema21 = abs(close - ema21_val) / ema21_val * 100 <= near_pct
        below_ema9 = close < ema9_val
        below_ema21 = close < ema21_val
        
        # Earnings positive %
        earn_pos_pct = earnings_positive_reactions(ticker)
        if earn_pos_pct is None:
            continue
        
        # EMA hold check
        ema9_hold = passes_ema_hold(df, 9, years_hold)
        ema21_hold = passes_ema_hold(df, 21, years_hold)
        
        if (near_ema9 or below_ema9) and (near_ema21 or below_ema21) and earn_pos_pct >= earnings_positive_threshold and ema9_hold and ema21_hold:
            results.append({
                "Ticker": ticker,
                "Close": round(close, 2),
                "EMA9": round(ema9_val, 2),
                "EMA21": round(ema21_val, 2),
                "% Positive Earnings": round(earn_pos_pct, 1),
                "Near EMA9": near_ema9,
                "Near EMA21": near_ema21
            })
    except Exception as e:
        print(f"Error with {ticker}: {e}")

if results:
    st.subheader("Matching Stocks")
    st.dataframe(pd.DataFrame(results))
else:
    st.warning("No stocks match the criteria.")
