import streamlit as st
import pandas as pd
import requests
import pydeck as pdk

# Streamlit app starts here
st.title("NYC Vehicle Accident Visualization")

st.markdown(
    """
    This app visualizes vehicle accidents in New York City. 
    Use the date picker to filter accidents by date and visualize them on a map.
    """
)

# Function to fetch data from the NYC vehicle accident API
@st.cache_data
def fetch_accident_data():
    url = "https://data.cityofnewyork.us/resource/h9gi-nx95.json"
    params = {
        "$limit": 1000,  # Limit to 1,000 records for now (you can adjust as needed)
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch data. Status code: {response.status_code}")
        return []

# Fetch the accident data
accidents = fetch_accident_data()

# If no accidents were fetched, display an error
if not accidents:
    st.error("No accident data found.")
else:
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(accidents)

    # Ensure necessary columns are present
    required_columns = ['crash_date', 'latitude', 'longitude', 'on_street_name', 'borough']
    if not all(col in df.columns for col in required_columns):
        st.error(f"The dataset does not contain the necessary columns: {', '.join(required_columns)}.")
    else:
        # Convert 'crash_date' column to datetime
        df['crash_date'] = pd.to_datetime(df['crash_date'], errors='coerce')

        # Filter out rows with missing latitude, longitude, or borough
        df = df.dropna(subset=['latitude', 'longitude', 'borough'])

        # Convert latitude and longitude to numeric
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

        # Date picker for user to select the range
        start_date = st.date_input("Select the start date", df['crash_date'].min().date())
        end_date = st.date_input("Select the end date", df['crash_date'].max().date())

        # Filter the DataFrame based on the selected date range
        filtered_df = df[(df['crash_date'] >= pd.to_datetime(start_date)) & (df['crash_date'] <= pd.to_datetime(end_date))]

        # Display filtered data (optional)
        st.subheader(f"Accidents between {start_date} and {end_date}")
        st.dataframe(filtered_df[['crash_date', 'latitude', 'longitude']].head())

        # Statistical Overview
        st.subheader("Statistical Overview")

        # Total number of accidents
        total_accidents = len(filtered_df)
        st.write(f"**Total number of accidents:** {total_accidents}")

        # Average number of accidents per day
        accidents_per_day = filtered_df.groupby(filtered_df['crash_date'].dt.date).size()
        avg_accidents_per_day = accidents_per_day.mean()
        st.write(f"**Average number of accidents per day:** {avg_accidents_per_day:.2f}")

        # Most frequent street name (on_street_name)
        most_common_street = filtered_df['on_street_name'].mode()[0]
        st.write(f"**Most common street for accidents:** {most_common_street}")

        # Most frequent borough
        most_common_borough = filtered_df['borough'].mode()[0]
        st.write(f"**Borough with most accidents:** {most_common_borough}")

        # Map visualization using pydeck
        st.subheader("Accidents on the Map")

        if len(filtered_df) > 0:
            # Define pydeck layers for accident data
            accident_layer = pdk.Layer(
                'ScatterplotLayer',
                filtered_df[['latitude', 'longitude']],
                get_position='[longitude, latitude]',
                get_radius=50,
                get_fill_color='[255, 0, 0, 160]',
                pickable=True,
                opacity=0.8
            )

            # Standardize borough names to lowercase for dictionary lookup
            most_common_borough = most_common_borough.lower()

            # Get borough boundary data (This will need to be manually added or fetched from another source)
            # For now, using a basic polygon for Manhattan as an example
            borough_boundaries = {
                'manhattan': [
                    [-74.0201, 40.7003],
                    [-73.9306, 40.7003],
                    [-73.9306, 40.8003],
                    [-74.0201, 40.8003],
                    [-74.0201, 40.7003]
                ],
                'brooklyn': [
                    [-73.9794, 40.5730],
                    [-73.8994, 40.5730],
                    [-73.8994, 40.6930],
                    [-73.9794, 40.6930],
                    [-73.9794, 40.5730]
                ]
            }

            # Check if the borough is in the dictionary and create the highlight layer
            if most_common_borough in borough_boundaries:
                borough_highlight_layer = pdk.Layer(
                    'PolygonLayer',
                    data=[{'coordinates': borough_boundaries[most_common_borough]}],
                    get_polygon='coordinates',
                    get_fill_color='[255, 165, 0, 180]',  # Orange color for highlighting
                    pickable=False,
                    opacity=0.5
                )
            else:
                borough_highlight_layer = None  # If borough boundary data is not available

            # Initialize pydeck map
            deck = pdk.Deck(
                initial_view_state=pdk.ViewState(
                    latitude=filtered_df['latitude'].mean(),
                    longitude=filtered_df['longitude'].mean(),
                    zoom=12,
                    pitch=0
                ),
                layers=[accident_layer] + ([borough_highlight_layer] if borough_highlight_layer else [])
            )

            st.pydeck_chart(deck)

        else:
            st.warning("No accidents found for the selected date range.")
