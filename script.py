import streamlit as st
import ccxt
import pandas as pd
import datetime


# -------------------
#   TWAP FUNCTION
# -------------------
def get_twap_last_5_business_days(symbol, timeframe, days_to_fetch=5):
    """
    Fetches OHLCV data for the specified symbol and timeframe from MEXC exchange
    and calculates the TWAP over the last 'days_to_fetch' business days.
    """
    # Initialize the MEXC exchange via ccxt
    exchange = ccxt.mexc()

    # Calculate time range (UTC)
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(days=days_to_fetch)

    # Convert to milliseconds for ccxt
    since = int(start_time.timestamp() * 1000)
    now_ms = int(end_time.timestamp() * 1000)

    ohlcv = []
    limit = 1000  # ccxt default max per fetch

    # Paginate through OHLCV if needed
    while True:
        # Fetch candles
        batch = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        if not batch:
            break

        ohlcv.extend(batch)

        # Last candle’s timestamp
        last_timestamp = batch[-1][0]

        # Update 'since' so next fetch starts after the last candle we received
        since = last_timestamp + 1

        # Stop if we've passed the desired end_time
        if last_timestamp > now_ms:
            break

    # Convert to Pandas DataFrame
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

    # Determine the cutoff date (last X business days)
    today = datetime.datetime.utcnow().date()
    five_business_days_ago = today - pd.tseries.offsets.Day(days_to_fetch)
    df = df[df["timestamp"].dt.date >= five_business_days_ago.date()]

    if df.empty:
        return None, None

    # Calculate typical price for each bar
    df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3

    # Time-Weighted Average Price (over the filtered period)
    twap_value = df["typical_price"].mean()

    return twap_value, df


# -------------------
#   STREAMLIT APP
# -------------------
def main():
    st.title("Crypto TWAP Dashboard")

    # You can easily add or remove symbols here.
    token_options = [
        "MIDLE/USDT",
        "RIVAL/USDT",
        "FARTBOY/USDT",  # Replace this with other pairs you'd like to track
        "ASV/USDT",
        "SUPR/USDT",
        "NTX/USDT"
    ]

    # Let users pick which symbols to fetch
    selected_tokens = st.multiselect(
        "Select tokens to fetch TWAP",
        token_options,
        default=["FARTBOY/USDT"]  # default selection
    )

    # Parameters for TWAP calculation
    timeframe = st.selectbox("Select timeframe:", ["1m", "5m", "15m", "1h", "1d"], index=0)
    days_to_fetch = st.slider("Business days to fetch:", 1, 30, 5)

    if st.button("Fetch TWAP Data"):
        st.write(f"**Fetching data for:** {selected_tokens}")

        results = []
        for token in selected_tokens:
            twap, df = get_twap_last_5_business_days(token, timeframe, days_to_fetch)
            if twap is not None and df is not None:
                results.append({"Symbol": token, "TWAP": twap})

                # Display token-level info
                st.subheader(f"Symbol: {token}")
                st.write(f"**TWAP (last {days_to_fetch} business days):** {twap:.6f}")

                # Show a line chart of typical_price
                st.line_chart(df.set_index("timestamp")["typical_price"])

            else:
                st.warning(f"No data retrieved for {token}. Please check the pair or date range.")

        # Display aggregated results in a table
        if results:
            result_df = pd.DataFrame(results)
            st.write("### Summary of TWAPs")
            st.write(result_df)


if __name__ == "__main__":
    main()
