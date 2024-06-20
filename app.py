import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import folium_static
import time

# Define the base URL of the public Google Spreadsheet
spreadsheet_id = '1goJqD5eK8J6bayJlqC0RgEmxkDnmTOW6Jfzr3_cjwAQ'
base_url = f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&sheet='

# Define the sheet names you want to read
sheet_names = ['device1', 'device2', 'device3', 'device4', 'device5', 'device6']

# Function to read data from Google Sheets based on device_id
def read_data_from_sheet(device_id):
    try:
        sheet_url = base_url + device_id
        data = pd.read_csv(sheet_url)

        # Combine Date and Time columns into Timestamp column
        data['Timestamp'] = pd.to_datetime(data['date'] + ' ' + data['time'])
        # Ensure latitude and longitude are numeric
        data['latitude'] = pd.to_numeric(data['latitude'], errors='coerce')
        data['longitude'] = pd.to_numeric(data['longitude'], errors='coerce')

        return data
    except Exception as e:
        st.error(f"Failed to fetch data from Google Sheets: {e}")
        return pd.DataFrame()

# Function to filter data based on daily or monthly selection
def filter_data_by_period(data, period, selected_date=None, selected_month=None):
    if period == 'Daily':
        if selected_date:
            data_filtered = data[data['Timestamp'].dt.date == pd.to_datetime(selected_date).date()]
        else:
            data_filtered = data[data['Timestamp'].dt.date == pd.Timestamp.now().date()]
    elif period == 'Monthly':
        if selected_month:
            year, month = map(int, selected_month.split('-'))
            data_filtered = data[(data['Timestamp'].dt.year == year) & (data['Timestamp'].dt.month == month)]
        else:
            data_filtered = data[(data['Timestamp'].dt.year == pd.Timestamp.now().year) & (data['Timestamp'].dt.month == pd.Timestamp.now().month)]
    else:
        data_filtered = data  # Display all data if no specific period is selected

    return data_filtered

# Streamlit app
st.title("Water Quality Monitoring System")

# Sidebar for device selection and period selection
devices = [f'device{i}' for i in range(1, 7)]
selected_device = st.sidebar.selectbox("Select a device to analyze", options=devices)

selected_period = st.sidebar.radio("Select period", options=['All', 'Daily', 'Monthly'])

# Add date and month pickers based on period selection
if selected_period == 'Daily':
    selected_date = st.sidebar.date_input("Select a date", value=pd.Timestamp.now())
    selected_month = None
elif selected_period == 'Monthly':
    selected_month = st.sidebar.selectbox("Select a month", options=pd.date_range(start=pd.Timestamp.now().date() - pd.DateOffset(months=5), end=pd.Timestamp.now().date(), freq='MS').strftime('%Y-%m').tolist())
    selected_date = None
else:
    selected_date = None
    selected_month = None

if selected_device != "All Devices":
    data = read_data_from_sheet(selected_device)
else:
    # Concatenate data from all devices if "All Devices" is selected
    data = pd.concat([read_data_from_sheet(device) for device in devices], ignore_index=True)

if data.empty:
    st.warning("No data available to display for the selected device(s).")
else:
    st.header("Latest Water Quality")

    # Filter data based on selected period and date/month
    data_filtered = filter_data_by_period(data, selected_period, selected_date, selected_month)

    if data_filtered.empty:
        if selected_period.lower() == 'daily':
            st.warning(f"No data available for the selected day.")
        else:
            st.warning(f"No data available for the selected Month.")
    else:
        # Get the latest readings
        latest_data = data_filtered.sort_values(by='Timestamp').iloc[-1]

        col1, col2, col3 = st.columns(3)

        col1.metric("Conductivity", f"{latest_data['conductivity']:.2f} ppm")
        col2.metric("Turbidity", f"{latest_data['turbidity']:.2f} NTU")
        col3.metric("Temperature", f"{latest_data['temperature']:.2f} °C")

        # Display data table for the selected device and period
        st.sidebar.header("Device data table")
        st.sidebar.dataframe(data_filtered[['Timestamp', 'conductivity', 'temperature', 'turbidity', 'latitude', 'longitude']])

        # Combined Graph
        fig = go.Figure()

        # Conductivity levels
        fig.add_trace(go.Scatter(x=data_filtered['Timestamp'], y=data_filtered['conductivity'], mode='lines+markers', name='conductivity'))

        # Turbidity levels
        fig.add_trace(go.Scatter(x=data_filtered['Timestamp'], y=data_filtered['turbidity'], mode='lines+markers', name='turbidity', yaxis='y2'))

        # Temperature levels
        fig.add_trace(go.Scatter(x=data_filtered['Timestamp'], y=data_filtered['temperature'], mode='lines+markers', name='temperature', yaxis='y3'))

        # Create axis objects
        fig.update_layout(
            xaxis=dict(domain=[0.1, 0.9]),
            yaxis=dict(title="Conductivity", titlefont=dict(color="#1f77b4"), tickfont=dict(color="#1f77b4")),
            yaxis2=dict(title="Turbidity", titlefont=dict(color="#ff7f0e"), tickfont=dict(color="#ff7f0e"), anchor="x", overlaying="y", side="right", position=1),
            yaxis3=dict(title="Temperature (°C)", titlefont=dict(color="#d62728"), tickfont=dict(color="#d62728"), anchor="free", overlaying="y", side="right", position=0.95)
        )

        fig.update_layout(title="Water Quality Over Time", xaxis_title="Time")

        st.plotly_chart(fig)

        st.header("Device Locations")

        # Map with English language tiles
        m = folium.Map(location=[latest_data['latitude'], latest_data['longitude']], zoom_start=10, tiles='OpenStreetMap')

        # Add a marker for the latest location
        folium.Marker(
            [latest_data['latitude'], latest_data['longitude']],
            popup=f"Time: {latest_data['Timestamp']}<br>Conductivity={latest_data['conductivity']}ppm<br>Turbidity={latest_data['turbidity']}NTU<br>Temperature={latest_data['temperature']}°C",
            icon=folium.Icon(color='red')
        ).add_to(m)

        folium_static(m)

        # Add a script to refresh the app every half second
        st.write('<script>setTimeout(function(){window.location.reload(1);}, 500);</script>', unsafe_allow_html=True)

        # Add a delay to prevent the script from running too quickly
        time.sleep(0.5)
