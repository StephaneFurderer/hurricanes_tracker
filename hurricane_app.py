import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
import os
from datetime import datetime
from hurdat2parser import Hurdat2
import random
import plotly.express as px
from hurricane_county_matcher import match_hurricane_points_to_counties

def process_hurricane_data():
    # Use the local HURDAT2 file directly
    data_file = "hurdat2-1851-2024-040425.txt"
    
    if not os.path.exists(data_file):
        st.error(f"Error: {data_file} not found. Please download the HURDAT2 file from https://www.nhc.noaa.gov/data/#hurdat and place it in the same directory as this script.")
        return None
    
    # Parse the data using Hurdat2
    parser = Hurdat2(data_file)
    
    # Convert to DataFrame
    records = []
    for storm in parser.tc.values():
        # Use storm ID as name for unnamed hurricanes
        storm_name = storm.atcfid if storm.name == "UNNAMED" else storm.name
        for entry in storm.entry:
            records.append({
                'storm_id': storm.atcfid,
                'name': storm_name,
                'date': entry.date.strftime('%Y%m%d'),
                'time': entry.time.strftime('%H%M'),
                'status': entry.status,
                'latitude': entry.latitude,
                'longitude': entry.longitude,
                'wind_speed': entry.wind,
                'year': storm.year
            })
    
    return pd.DataFrame(records)

# Function to determine hurricane category based on wind speed
def get_hurricane_category(wind_speed):
    if wind_speed >= 157:
        return 5
    elif wind_speed >= 130:
        return 4
    elif wind_speed >= 111:
        return 3
    elif wind_speed >= 96:
        return 2
    elif wind_speed >= 74:
        return 1
    else:
        return 0

# Category color map
CATEGORY_COLORS = {
    0: 'gray',    # Tropical Depression/Storm
    1: 'blue',   # Category 1
    2: 'green',  # Category 2
    3: 'yellow', # Category 3
    4: 'orange', # Category 4
    5: 'red',    # Category 5
}

# For all-hurricane mode, assign a unique color per hurricane
PALETTE = [
    'red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'black', 'cyan', 'magenta',
    '#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe'
]

@st.cache_data(show_spinner=True)
def get_hurricane_points_with_county():
    df = process_hurricane_data()
    df['category'] = df['wind_speed'].apply(get_hurricane_category)
    df['hurricane_id'] = df['name'] + ' (' + df['year'].astype(str) + ')'
    # Only keep necessary columns for join
    join_cols = ['hurricane_id', 'name', 'year', 'date', 'time', 'latitude', 'longitude', 'category', 'wind_speed']
    df = df[join_cols]
    # Spatial join
    joined = match_hurricane_points_to_counties(df)
    return joined

def hurricane_map_page(df):
    st.title("Atlantic Hurricane Paths Visualization")
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Year filter
    years = sorted(df['year'].unique())
    selected_year = st.sidebar.selectbox("Select Year", years)
    
    # Region filter
    region_options = ['Any', 'Atlantic', 'Gulf of Mexico', 'Both']
    selected_region = st.sidebar.selectbox("Show hurricanes that crossed:", region_options, index=0)
    
    # Determine hurricanes that crossed each region
    hurricane_region_map = df.groupby('hurricane_id')['region'].agg(lambda x: set(x.dropna())).to_dict()
    
    # Filtering logic
    if selected_region == 'Any':
        hurricanes_in_year = df[df['year'] == selected_year]['hurricane_id'].unique()
    elif selected_region == 'Both':
        hurricanes_in_year = [hid for hid, regions in hurricane_region_map.items() if {'Atlantic', 'Gulf of Mexico'}.issubset(regions) and df[df['hurricane_id']==hid]['year'].iloc[0]==selected_year]
    else:
        hurricanes_in_year = [hid for hid, regions in hurricane_region_map.items() if selected_region in regions and df[df['hurricane_id']==hid]['year'].iloc[0]==selected_year]
    
    # Dropdown with region info
    dropdown_labels = [
        f"{hid} [crossed: {', '.join(sorted(hurricane_region_map.get(hid, [])))}]"
        for hid in hurricanes_in_year
    ]
    hurricane_id_to_label = dict(zip(hurricanes_in_year, dropdown_labels))
    hurricane_label_to_id = {v: k for k, v in hurricane_id_to_label.items()}
    selected_label = st.sidebar.selectbox("Select Hurricane", sorted(dropdown_labels))
    selected_hurricane = hurricane_label_to_id[selected_label]
    
    # Filter data for map
    filtered_df = df[(df['year'] == selected_year) & (df['hurricane_id'] == selected_hurricane)]
    
    # Create map
    if not filtered_df.empty:
        center_lat = filtered_df['latitude'].mean()
        center_lon = filtered_df['longitude'].mean()
        m = folium.Map(location=[center_lat, center_lon], zoom_start=4)
        
        storm_df = filtered_df.sort_values(['date', 'time'])
        path_points = storm_df[['latitude', 'longitude', 'category', 'name', 'date']].values
        for i in range(len(path_points) - 1):
            latlon1 = (path_points[i][0], path_points[i][1])
            latlon2 = (path_points[i+1][0], path_points[i+1][1])
            cat = int(path_points[i][2])
            name = path_points[i][3]
            date = path_points[i][4]
            folium.PolyLine(
                [latlon1, latlon2],
                color=CATEGORY_COLORS.get(cat, 'black'),
                weight=4,
                opacity=0.8,
                tooltip=f"{name} | Cat {cat} | {date}"
            ).add_to(m)
        folium.Marker(
            (path_points[0][0], path_points[0][1]),
            popup=f"Start: {name} ({path_points[0][4]})"
        ).add_to(m)
        folium.Marker(
            (path_points[-1][0], path_points[-1][1]),
            popup=f"End: {name} ({path_points[-1][4]})"
        ).add_to(m)
        
        folium_static(m)
        
        # Add legend
        legend_html = '''<div style="position: fixed; 
            bottom: 50px; left: 50px; width: 220px; height: 200px; 
            background-color: white; z-index:9999; font-size:14px; border:2px solid gray; padding: 10px;">
            <b>Category Colors</b><br>
            <span style="color:gray;">&#9632;</span> 0: TD/TS<br>
            <span style="color:blue;">&#9632;</span> 1: Cat 1<br>
            <span style="color:green;">&#9632;</span> 2: Cat 2<br>
            <span style="color:yellow;">&#9632;</span> 3: Cat 3<br>
            <span style="color:orange;">&#9632;</span> 4: Cat 4<br>
            <span style="color:red;">&#9632;</span> 5: Cat 5<br>
            <hr style='margin:4px 0;'>
            <b>All Hurricanes Mode:</b><br>
            Each hurricane gets a unique color.<br>
            Hover for name, category, date.
            </div>'''
        st.markdown(legend_html, unsafe_allow_html=True)
        
        # Display statistics
        st.subheader("Hurricane Statistics")
        st.write(f"Hurricane: {selected_hurricane}")
        st.write(f"Maximum wind speed: {filtered_df['wind_speed'].max()} knots")
        st.write(f"Duration: {filtered_df['date'].min()} to {filtered_df['date'].max()}")
        
        # Display raw data
        st.subheader("Raw Data")
        st.dataframe(filtered_df)
    else:
        st.warning("No hurricanes found for the selected criteria.")

def hurricane_weekly_frequency_page(df):
    st.title("Weekly Hurricane Frequency")
    st.markdown("This chart shows the number of hurricane points (not unique storms) per week of the year. We'll refine to landfalls and coastlines next.")
    # Sidebar year range filter
    min_year = int(df['year'].min())
    max_year = int(df['year'].max())
    st.sidebar.header("Year Range Filter")
    start_year = st.sidebar.number_input("Start Year", min_value=min_year, max_value=max_year, value=1980)
    end_year = st.sidebar.number_input("End Year", min_value=min_year, max_value=max_year, value=max_year)
    if start_year > end_year:
        st.sidebar.error("Start year must be less than or equal to end year.")
        return
    # Filter by year range
    df = df[(df['year'] >= start_year) & (df['year'] <= end_year)]
    # Ensure date is datetime
    df['date_dt'] = pd.to_datetime(df['date'], format='%Y%m%d', errors='coerce')
    df = df.dropna(subset=['date_dt'])
    df['weekofyear'] = df['date_dt'].dt.isocalendar().week
    # Only count points where category >= 1 (hurricane strength)
    hurricane_points = df[df['category'] >= 1]
    week_counts = hurricane_points.groupby('weekofyear').size().reset_index(name='count')
    fig = px.bar(week_counts, x='weekofyear', y='count', labels={'weekofyear': 'Week of Year', 'count': 'Number of Hurricane Points'}, title=f'Weekly Hurricane Frequency ({start_year}-{end_year})')
    st.plotly_chart(fig, use_container_width=True)
    # Frequency chart
    num_years = end_year - start_year + 1
    week_counts['frequency'] = week_counts['count'] / num_years
    fig2 = px.bar(week_counts, x='weekofyear', y='frequency', labels={'weekofyear': 'Week of Year', 'frequency': 'Avg Hurricane Points per Year'}, title=f'Average Weekly Hurricane Frequency ({start_year}-{end_year})')
    st.plotly_chart(fig2, use_container_width=True)
    # Probability chart
    # For each year and week, check if there is at least one hurricane point
    year_week = hurricane_points.groupby(['year', 'weekofyear']).size().reset_index(name='has_hurricane')
    year_week['has_hurricane'] = 1  # presence indicator
    prob_df = year_week.groupby('weekofyear')['year'].count().reset_index(name='years_with_hurricane')
    prob_df['probability'] = prob_df['years_with_hurricane'] / num_years
    fig3 = px.bar(prob_df, x='weekofyear', y='probability', labels={'weekofyear': 'Week of Year', 'probability': 'Probability of ≥1 Hurricane'}, title=f'Probability of at Least One Hurricane per Week ({start_year}-{end_year})', range_y=[0,1])
    st.plotly_chart(fig3, use_container_width=True)

# Streamlit multi-page setup
PAGES = {
    "Interactive Map": hurricane_map_page,
    "Weekly Hurricane Frequency": hurricane_weekly_frequency_page,
}

def main():
    # Use the spatially joined DataFrame for the map page
    joined = get_hurricane_points_with_county()
    # For the map page, pass the joined DataFrame
    PAGES = {
        "Interactive Map": hurricane_map_page,
        "Weekly Hurricane Frequency": hurricane_weekly_frequency_page,
    }
    page = st.sidebar.selectbox("Select Page", list(PAGES.keys()))
    if page == "Interactive Map":
        hurricane_map_page(joined)
    else:
        # For the frequency page, use the original process_hurricane_data
        df = process_hurricane_data()
        df['category'] = df['wind_speed'].apply(get_hurricane_category)
        df['hurricane_id'] = df['name'] + ' (' + df['year'].astype(str) + ')'
        hurricane_weekly_frequency_page(df)

if __name__ == "__main__":
    main() 