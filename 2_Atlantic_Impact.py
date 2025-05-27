import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
import plotly.express as px
from hurricane_county_matcher import match_hurricane_points_to_counties
from coastal_county_matcher import load_coastal_county_boundaries
from utils import calculate_weekly_frequency

st.set_page_config(page_title="Hurricane Analysis", page_icon="🌊", layout="wide")

CATEGORY_COLORS = {
    0: 'gray', 1: 'blue', 2: 'green', 3: 'yellow', 4: 'orange', 5: 'red'
}

@st.cache_data(show_spinner=True)
def get_joined_points():
    from hurricane_app import process_hurricane_data, get_hurricane_category
    df = process_hurricane_data()
    df['category'] = df['wind_speed'].apply(get_hurricane_category)
    df['hurricane_id'] = df['name'] + ' (' + df['year'].astype(str) + ')'
    join_cols = ['hurricane_id', 'name', 'year', 'date', 'time', 'latitude', 'longitude', 'category', 'wind_speed']
    df = df[join_cols]
    joined = match_hurricane_points_to_counties(df)
    return joined

def overlay_counties(m, region):
    gdf = load_coastal_county_boundaries()
    if region == 'Atlantic':
        gdf = gdf[gdf['region'] == 'Atlantic']
        color = 'blue'
    elif region == 'Gulf of Mexico':
        gdf = gdf[gdf['region'] == 'Gulf of Mexico']
        color = 'green'
    else:  # 'Any' or 'Both'
        gdf = gdf[(gdf['region'] == 'Atlantic') | (gdf['region'] == 'Gulf of Mexico')]
        color = 'blue'
    folium.GeoJson(gdf, name=f'{region} Counties', style_function=lambda x: {'color': color, 'fillColor': color, 'weight': 2, 'fillOpacity': 0.15}).add_to(m)

def plot_hurricane_paths(m, filtered_df, hurricanes_in_range):
    for hurricane_id in hurricanes_in_range:
        storm_df = filtered_df[filtered_df['hurricane_id'] == hurricane_id].sort_values(['date', 'time'])
        if not storm_df.empty:
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
            # Add start and end markers
            if len(path_points) > 0:
                folium.Marker(
                    (path_points[0][0], path_points[0][1]),
                    popup=f"Start: {name} ({path_points[0][4]})"
                ).add_to(m)
                if len(path_points) > 1:
                    folium.Marker(
                        (path_points[-1][0], path_points[-1][1]),
                        popup=f"End: {name} ({path_points[-1][4]})"
                    ).add_to(m)

# --- PAGE CONTENT ---
st.title("Hurricane Analysis")

# Get the data
df = get_joined_points()

# Sidebar filters
st.sidebar.header("Filters")
min_year = int(df['year'].min())
max_year = int(df['year'].max())
start_year = st.sidebar.number_input("Start Year", min_value=min_year, max_value=max_year, value=max(min_year, 2014))
end_year = st.sidebar.number_input("End Year", min_value=min_year, max_value=max_year, value=max_year)
min_category = st.sidebar.selectbox("Minimum Category", options=[0, 1, 2, 3, 4, 5], index=0, 
                                  help="Show only hurricanes of this category or higher")
show_all = st.sidebar.checkbox("Show all hurricanes for this period", value=True)

if start_year > end_year:
    st.sidebar.error("Start year must be less than or equal to end year.")
else:
    # Create tabs for different regions
    tab1, tab2, tab3 = st.tabs(["All Regions", "Atlantic", "Gulf of Mexico"])
    
    # Get hurricanes for the selected period and category
    hurricane_region_map = df.groupby('hurricane_id')['region'].agg(lambda x: set(x.dropna())).to_dict()
    
    # Function to get hurricanes for a specific region
    def get_hurricanes_for_region(region):
        if region == 'Any':
            return [hid for hid, regions in hurricane_region_map.items() 
                   if ('Atlantic' in regions or 'Gulf of Mexico' in regions)
                   and start_year <= df[df['hurricane_id']==hid]['year'].iloc[0] <= end_year
                   and df[df['hurricane_id']==hid]['category'].max() >= min_category]
        else:
            return [hid for hid, regions in hurricane_region_map.items() 
                   if region in regions 
                   and start_year <= df[df['hurricane_id']==hid]['year'].iloc[0] <= end_year
                   and df[df['hurricane_id']==hid]['category'].max() >= min_category]
    
    # Tab 1: All Regions
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Weekly Hurricane Frequency")
            freq_all = calculate_weekly_frequency(df, 'Any', start_year, end_year, min_category)
            fig_all = px.bar(freq_all, 
                           x='Week', 
                           y='Probability',
                           title=f'Probability of Hurricane Occurrence by Week ({start_year}-{end_year}) - Category {min_category}+',
                           labels={'Probability': 'Probability of at least one hurricane'})
            fig_all.update_layout(
                xaxis_title="Week of Year",
                yaxis_title="Probability",
                yaxis_tickformat='.1%',
                showlegend=False
            )
            st.plotly_chart(fig_all, use_container_width=True)
        
        with col2:
            st.subheader("Hurricane Map")
            hurricanes_all = get_hurricanes_for_region('Any')
            filtered_df = df[(df['hurricane_id'].isin(hurricanes_all)) & 
                           (df['year'] >= start_year) & 
                           (df['year'] <= end_year)]
            if not filtered_df.empty:
                center_lat = filtered_df['latitude'].mean()
                center_lon = filtered_df['longitude'].mean()
                m = folium.Map(location=[center_lat, center_lon], zoom_start=4)
                overlay_counties(m, 'Any')
                plot_hurricane_paths(m, filtered_df, hurricanes_all)
                folium_static(m)
                st.write(f"Number of hurricanes: {len(hurricanes_all)}")
            else:
                st.warning("No hurricanes found for the selected criteria.")
    
    # Tab 2: Atlantic
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Weekly Hurricane Frequency")
            freq_atlantic = calculate_weekly_frequency(df, 'Atlantic', start_year, end_year, min_category)
            fig_atlantic = px.bar(freq_atlantic, 
                                x='Week', 
                                y='Probability',
                                title=f'Probability of Atlantic Hurricane Occurrence by Week ({start_year}-{end_year}) - Category {min_category}+',
                                labels={'Probability': 'Probability of at least one hurricane'})
            fig_atlantic.update_layout(
                xaxis_title="Week of Year",
                yaxis_title="Probability",
                yaxis_tickformat='.1%',
                showlegend=False
            )
            st.plotly_chart(fig_atlantic, use_container_width=True)
        
        with col2:
            st.subheader("Hurricane Map")
            hurricanes_atlantic = get_hurricanes_for_region('Atlantic')
            filtered_df = df[(df['hurricane_id'].isin(hurricanes_atlantic)) & 
                           (df['year'] >= start_year) & 
                           (df['year'] <= end_year)]
            if not filtered_df.empty:
                center_lat = filtered_df['latitude'].mean()
                center_lon = filtered_df['longitude'].mean()
                m = folium.Map(location=[center_lat, center_lon], zoom_start=4)
                overlay_counties(m, 'Atlantic')
                plot_hurricane_paths(m, filtered_df, hurricanes_atlantic)
                folium_static(m)
                st.write(f"Number of hurricanes: {len(hurricanes_atlantic)}")
            else:
                st.warning("No hurricanes found for the selected criteria.")
    
    # Tab 3: Gulf of Mexico
    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Weekly Hurricane Frequency")
            freq_gulf = calculate_weekly_frequency(df, 'Gulf of Mexico', start_year, end_year, min_category)
            fig_gulf = px.bar(freq_gulf, 
                            x='Week', 
                            y='Probability',
                            title=f'Probability of Gulf Hurricane Occurrence by Week ({start_year}-{end_year}) - Category {min_category}+',
                            labels={'Probability': 'Probability of at least one hurricane'})
            fig_gulf.update_layout(
                xaxis_title="Week of Year",
                yaxis_title="Probability",
                yaxis_tickformat='.1%',
                showlegend=False
            )
            st.plotly_chart(fig_gulf, use_container_width=True)
        
        with col2:
            st.subheader("Hurricane Map")
            hurricanes_gulf = get_hurricanes_for_region('Gulf of Mexico')
            filtered_df = df[(df['hurricane_id'].isin(hurricanes_gulf)) & 
                           (df['year'] >= start_year) & 
                           (df['year'] <= end_year)]
            if not filtered_df.empty:
                center_lat = filtered_df['latitude'].mean()
                center_lon = filtered_df['longitude'].mean()
                m = folium.Map(location=[center_lat, center_lon], zoom_start=4)
                overlay_counties(m, 'Gulf of Mexico')
                plot_hurricane_paths(m, filtered_df, hurricanes_gulf)
                folium_static(m)
                st.write(f"Number of hurricanes: {len(hurricanes_gulf)}")
            else:
                st.warning("No hurricanes found for the selected criteria.") 