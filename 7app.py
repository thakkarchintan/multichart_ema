import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from ta.trend import EMAIndicator
import matplotlib.dates as mdates
import os

# Set the app to wide mode
st.set_page_config(layout="wide")

# Sidebar configuration
st.sidebar.title('Multicharts with EMA')

# Read the Excel file
stock_data = pd.read_excel('Symbol_list.xlsx')
tickers = stock_data['Ticker'].unique()

# Load Excel file and get tickers from the same directory as the script
# current_directory = os.path.dirname(os.path.abspath(__file__))
# file_path = os.path.join(current_directory, 'Symbol_list.xlsx')

# Read the Excel file
# if os.path.exists(file_path):
    # stock_data = pd.read_excel(file_path)
    # tickers = stock_data['Ticker'].unique()
# else:
    # st.sidebar.write("Symbol_list.xlsx not found in the current directory.")
    # st.stop()

# The rest of your code continues here

# Load Excel file and get tickers
# uploaded_file = st.sidebar.file_uploader("Upload an Excel file", type=["xlsx"])
# if uploaded_file is not None:
    # stock_data = pd.read_excel(uploaded_file)
    # tickers = stock_data['Ticker'].unique()
# else:
    # st.sidebar.write("Please upload an Excel file containing stock tickers.")
    # st.stop()

# Interval selection
interval = st.sidebar.selectbox("Select Interval", options=["1H", "3H", "1D", "1W"], index=2)

# Number of candles option
num_candles = st.sidebar.number_input("Number of Candles", min_value=1, max_value=10000, value=100)

# EMA indicators
selected_indicators = []
indicator_params = {}

# Allow adding multiple instances of EMA
add_ema = st.sidebar.checkbox(f"Add EMA")
if add_ema:
    num_instances = st.sidebar.number_input(f"How many EMAs?", min_value=1, max_value=5, value=1, key=f"EMA_num_instances")
    for i in range(num_instances):
        with st.sidebar.expander(f"EMA Instance {i+1}"):
            window = st.sidebar.number_input(f"EMA Window", min_value=2, max_value=1000, value=14, key=f"EMA_window_{i}")
            selected_indicators.append("EMA")
            indicator_params[f"EMA_{i}"] = {"window": window}

# Pre-defined list of colors
colors = ['blue', 'orange', 'green', 'red', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']

# Number of columns in chart grid
num_columns = st.sidebar.number_input("Number of Columns", min_value=1, max_value=10, value=2)

# Height of the chart
chart_height = st.sidebar.number_input("Chart Height", min_value=100, max_value=1200, value=800)

# Function to download data based on interval (OLD)
# def download_data(ticker, interval, num_candles):
    # if interval == "1H":
        # df = yf.download(ticker, period=f"{num_candles}h", interval='1h')
        # df = df[df.index.dayofweek < 5]  # Exclude weekends
        # df = df.between_time('00:00', '23:59')  # Filter to only include trading hours
    # elif interval == "3H":
        # df = yf.download(ticker, period=f"{num_candles*3}h", interval='1h')
        # df = df[df.index.dayofweek < 5]  # Exclude weekends
        # df = df.between_time('00:00', '23:59')  # Filter to only include trading hours
        # df = df.resample('3H').agg({
            # 'Open': 'first',
            # 'High': 'max',
            # 'Low': 'min',
            # 'Close': 'last',
            # 'Volume': 'sum'
        # }).dropna()
    # elif interval == "1D":
        # df = yf.download(ticker, period=f"{num_candles}d", interval='1d')
        # df = df[df.index.dayofweek < 5]  # Exclude weekends
    # elif interval == "1W":
        # df = yf.download(ticker, period=f"{num_candles*7}d", interval='1d')
        # df = df[df.index.dayofweek < 5]  # Exclude weekends
        # df = df.resample('W').agg({
            # 'Open': 'first',
            # 'High': 'max',
            # 'Low': 'min',
            # 'Close': 'last',
            # 'Volume': 'sum'
        # }).dropna()
    # return df

# NEW 

def download_data(ticker, interval, num_candles):
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
    
    # Ensure the index is a DatetimeIndex before filtering by dayofweek
    df.index = pd.to_datetime(df.index)
    df = df[df.index.dayofweek < 5]  # Exclude weekends
    
    if interval in ["1H", "3H"]:
        df = df.between_time('00:00', '23:59')  # Filter to only include trading hours
    
    return df


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
                    st.warning(f"No data available for {ticker}")
                    continue

                # Ensure the index is a DatetimeIndex
                df.index = pd.to_datetime(df.index)
                
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

                # Determine tick values and text for x-axis
                num_ticks = max(1, len(df.index) // 10)  # Ensure at least one tick
                tick_vals = df.index[::num_ticks]
                tick_text = [date.strftime('%d-%b-%y %H:%M') for date in df.index[::num_ticks]]

                # Update chart layout with customized x-axis formatting
                fig.update_layout(title=f'{ticker}({interval})',
                                  yaxis_title='Price',
                                  xaxis_title='Date',
                                  xaxis_rangeslider_visible=False,
                                  height=chart_height,
                                  xaxis=dict(
                                      type='date',  # Use 'date' for DatetimeIndex
                                      tickformat='%d-%b-%y %H:%M',  # Customize x-axis date-time format
                                      tickvals=tick_vals,  # Show fewer ticks
                                      ticktext=tick_text,  # Custom tick labels
                                      nticks=min(len(tick_vals), 20)  # Adjust number of ticks
                                  ))

                # Display the chart in the column
                cols[col].plotly_chart(fig, use_container_width=True)



# Display the charts grid
create_chart_grid(tickers, interval, num_candles)