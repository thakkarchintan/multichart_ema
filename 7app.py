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

# Date selection
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("today"))

# Ensure end_date is after start_date
if end_date < start_date:
    st.sidebar.error("End Date must be after Start Date.")
    st.stop()

# EMA indicators
selected_indicators = []
indicator_params = {}

# Allow adding multiple instances of EMA
add_ema = st.sidebar.checkbox("Add EMA")
if add_ema:
    num_instances = st.sidebar.number_input("How many EMAs?", min_value=1, max_value=5, value=1)
    for i in range(num_instances):
        with st.sidebar.expander(f"EMA Instance {i+1}"):
            window_key = f"ema_window_{i}"
            window = st.sidebar.number_input(f"EMA Window {i+1}", min_value=2, max_value=1000, value=14, key=window_key)
            selected_indicators.append("EMA")
            indicator_params[f"EMA_{i}"] = {"window": window}

# Pre-defined list of colors
colors = ['blue', 'orange', 'green', 'red', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']

# Number of columns in chart grid
num_columns = st.sidebar.number_input("Number of Columns", min_value=1, max_value=10, value=2)

# Height of the chart
chart_height = st.sidebar.number_input("Chart Height", min_value=100, max_value=1200, value=800)

# Function to download data based on date range and interval
def download_data(ticker, interval, start_date, end_date):
    try:
        # Download data from Yahoo Finance
        df = yf.download(ticker, start=start_date, end=end_date, interval='1d')

        # Resample data based on the selected interval
        if interval == "1H":
            df = df.resample('1H').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            })
        elif interval == "3H":
            df = df.resample('3H').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            })
        elif interval == "1D":
            df = df.asfreq('D')
        elif interval == "1W":
            df = df.resample('W').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            })

        # Interpolate missing values to ensure continuity
        df = df.interpolate(method='linear').fillna(method='ffill').fillna(method='bfill')

        # Convert index to DatetimeIndex if it's not already
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        # Filter to exclude weekends if using intraday intervals
        if interval in ["1H", "3H"]:
            df = df.between_time('00:00', '23:59')  # Filter to include only trading hours
        
        return df

    except Exception as e:
        st.error(f"Error downloading data for {ticker}: {e}")
        return pd.DataFrame()



# Create a chart grid
def create_chart_grid(tickers, interval, start_date, end_date):
    num_rows = -(-len(tickers) // num_columns)  # Ceiling division

    for row in range(num_rows):
        cols = st.columns(num_columns)
        for col in range(num_columns):
            index = row * num_columns + col
            if index < len(tickers):
                ticker = tickers[index]
                df = download_data(ticker, interval, start_date, end_date)
                
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
create_chart_grid(tickers, interval, start_date, end_date)
