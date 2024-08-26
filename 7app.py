import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from ta.trend import EMAIndicator
import os

# Set the app to wide mode
st.set_page_config(layout="wide")

# Sidebar configuration
st.sidebar.title('Multicharts with EMA')

# Handle file uploads
uploaded_file = st.sidebar.file_uploader("Upload an Excel file", type=["xlsx"])

if uploaded_file is not None:
    try:
        stock_data = pd.read_excel(uploaded_file)
        tickers = stock_data['Ticker'].unique()
    except Exception as e:
        st.sidebar.error(f"Error reading the Excel file: {e}")
        st.stop()
else:
    st.sidebar.write("Please upload an Excel file containing stock tickers.")
    st.stop()

# Interval selection
interval = st.sidebar.selectbox("Select Interval", options=["1H", "3H", "1D", "1W"], index=2)

# Number of candles option
num_candles = st.sidebar.number_input("Number of Candles", min_value=1, max_value=10000, value=100)

# EMA indicators
selected_indicators = []
indicator_params = {}

# Allow adding multiple instances of EMA
add_ema = st.sidebar.checkbox("Add EMA")
if add_ema:
    num_instances = st.sidebar.number_input("How many EMAs?", min_value=1, max_value=5, value=1)
    for i in range(num_instances):
        with st.sidebar.expander(f"EMA Instance {i+1}"):
            window = st.sidebar.number_input(f"EMA Window", min_value=2, max_value=1000, value=14)
            selected_indicators.append("EMA")
            indicator_params[f"EMA_{i}"] = {"window": window}

# Pre-defined list of colors
colors = ['blue', 'orange', 'green', 'red', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']

# Number of columns in chart grid
num_columns = st.sidebar.number_input("Number of Columns", min_value=1, max_value=10, value=2)

# Height of the chart
chart_height = st.sidebar.number_input("Chart Height", min_value=100, max_value=1200, value=800)

# Function to download data based on interval
def download_data(ticker, interval, num_candles):
    try:
        if interval == "1H":
            df = yf.download(ticker, period=f"{num_candles}h", interval='1h')
        elif interval == "3H":
            df = yf.download(ticker, period=f"{num_candles*3}h", interval='1h')
            df = df.resample('3H').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
        elif interval == "1D":
            df = yf.download(ticker, period=f"{num_candles}d", interval='1d')
        elif interval == "1W":
            df = yf.download(ticker, period=f"{num_candles*7}d", interval='1d')
            df = df.resample('W').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()

        # Convert index to DatetimeIndex if it's not already
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        # Filter to exclude weekends and ensure data is within trading hours
        df = df[df.index.dayofweek < 5]  # Exclude weekends
        if interval in ["1H", "3H"]:
            df = df.between_time('00:00', '23:59')  # Filter to include only trading hours
        
        return df
    except Exception as e:
        st.error(f"Error downloading data for {ticker}: {e}")
        return pd.DataFrame()

# Create a chart grid
def create_chart_grid(tickers, interval, num_candles):
    num_rows = -(-len(tickers) // num_columns)  # Ceiling division

    for row in range(num_rows):
        cols = st.columns(num_columns)
        for col in range(num_columns):
            index = row * num_columns + col
            if index < len(tickers):
                ticker = tickers[index]
                df = download_data(ticker, interval, num_candles)
                
                if df.empty:
                    cols[col].write(f"Data for {ticker} could not be retrieved.")
                    continue

                # Plot candlestick chart
                fig = go.Figure(data=[go.Candlestick(x=df.index,
                                                     open=df['Open'],
                                                     high=df['High'],
                                                     low=df['Low'],
                                                     close=df['Close'])])

                # Apply and plot EMA indicators with unique colors
                for i, (indicator, params) in enumerate(indicator_params.items()):
                    if "EMA" in indicator:
                        ema = EMAIndicator(close=df['Close'], window=params['window'])
                        df[f'EMA{params["window"]}'] = ema.ema_indicator()
                        color = colors[i % len(colors)]
                        fig.add_trace(go.Scatter(x=df.index, y=df[f'EMA{params["window"]}'], 
                                                 name=f'EMA {params["window"]}', 
                                                 line=dict(color=color, width=2)))

                # Update chart layout with customized x-axis formatting
                fig.update_layout(title=f'{ticker} ({interval})',
                                  yaxis_title='Price',
                                  xaxis_title='Date',
                                  xaxis_rangeslider_visible=False,
                                  height=chart_height,
                                  xaxis=dict(
                                      tickformat='%d-%b-%y %H:%M',  # Customize x-axis date-time format
                                      tickvals=df.index[::max(1, len(df.index)//10)],  # Show fewer ticks, avoid zero step size
                                      ticktext=[date.strftime('%d-%b-%y %H:%M') for date in df.index[::max(1, len(df.index)//10)]],  # Custom tick labels
                                      nticks=20  # Adjust number of ticks
                                  ))

                # Display the chart in the column
                cols[col].plotly_chart(fig, use_container_width=True)

# Display the charts grid
create_chart_grid(tickers, interval, num_candles)
