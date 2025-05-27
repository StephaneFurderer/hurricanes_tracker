import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
import plotly.express as px
from hurricane_county_matcher import match_hurricane_points_to_counties
from coastal_county_matcher import load_coastal_county_boundaries
from utils import calculate_weekly_frequency

st.set_page_config(page_title="Hurricane Viewer", page_icon="🌊", layout="wide")

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
    elif region == 'Both':
        gdf = gdf[(gdf['region'] == 'Atlantic') | (gdf['region'] == 'Gulf of Mexico')]
        color = 'purple'
    else:  # 'Any'
        gdf = gdf[(gdf['region'] == 'Atlantic') | (gdf['region'] == 'Gulf of Mexico')]
        color = 'blue' # Or a different color for 'Any' if preferred
    folium.GeoJson(gdf, name=f'{region} Counties', style_function=lambda x: {'color': color, 'fillColor': color, 'weight': 2, 'fillOpacity': 0.15}).add_to(m)

def plot_hurricane_paths(m, filtered_df, hurricanes_to_plot):
    for hurricane_id in hurricanes_to_plot:
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
st.title("Hurricane Viewer")

# Get the data
df = get_joined_points()

# Sidebar filters
st.sidebar.header("Filters")
min_year_data = int(df['year'].min())
max_year_data = int(df['year'].max())
# st.text(min_year_data)
# st.text(max_year_data)
selected_year = st.sidebar.selectbox("Select Year", options=range(min_year_data, max_year_data + 1), index=max_year_data - min_year_data)
min_category = st.sidebar.selectbox("Minimum Category", options=[0, 1, 2, 3, 4, 5], index=0, 
                                  help="Show only hurricanes of this category or higher")
region_filter = st.sidebar.selectbox("Region", options=['Any', 'Atlantic', 'Gulf of Mexico', 'Both'], index=0)
show_all = st.sidebar.checkbox("Show all hurricanes for this period", value=True)

# Filter data by minimum category and selected year
filtered_df_category = df[
    (df['category'] >= min_category) & (df['year'] == selected_year)
].copy()

# Get hurricanes that match the region filter from the category-filtered data
hurricane_region_map = filtered_df_category.groupby('hurricane_id')['region'].agg(lambda x: set(x.dropna())).to_dict()

if region_filter == 'Any':
    hurricanes_in_region = [hid for hid, regions in hurricane_region_map.items() 
                            if ('Atlantic' in regions or 'Gulf of Mexico' in regions)]
elif region_filter == 'Both':
     hurricanes_in_region = [hid for hid, regions in hurricane_region_map.items() 
                             if ('Atlantic' in regions and 'Gulf of Mexico' in regions)]
else:
    hurricanes_in_region = [hid for hid, regions in hurricane_region_map.items() 
                            if region_filter in regions]

# Filter data by selected hurricanes
filtered_df = filtered_df_category[filtered_df_category['hurricane_id'].isin(hurricanes_in_region)].copy()

# Display map
st.subheader("Hurricane Map")

if show_all:
     hurricanes_to_plot = filtered_df['hurricane_id'].unique().tolist()
else:
    # Show dropdown for single hurricane selection for the filtered list
    dropdown_labels = [
         f"{hid} [crossed: {', '.join(sorted(hurricane_region_map.get(hid, [])))}]"
         for hid in hurricanes_in_region
     ]
    hurricane_id_to_label = dict(zip(hurricanes_in_region, dropdown_labels))
    hurricane_label_to_id = {v: k for k, v in hurricane_id_to_label.items()}
    
    if dropdown_labels:
        selected_label = st.sidebar.selectbox("Select Hurricane to plot", sorted(dropdown_labels))
        selected_hurricane = hurricane_label_to_id[selected_label]
        hurricanes_to_plot = [selected_hurricane]
    else:
        hurricanes_to_plot = [] # No hurricanes to plot if dropdown is empty

if not filtered_df.empty and hurricanes_to_plot:
    # Center map on the first point of the first hurricane to plot, or a default location
    first_hurricane_df = filtered_df[filtered_df['hurricane_id'] == hurricanes_to_plot[0]].sort_values(['date', 'time'])
    if not first_hurricane_df.empty:
         center_lat = first_hurricane_df.iloc[0]['latitude']
         center_lon = first_hurricane_df.iloc[0]['longitude']
    else:
        center_lat = 25.0
        center_lon = -80.0 # Default center near Florida
        
    m = folium.Map(location=[center_lat, center_lon], zoom_start=4)
    overlay_counties(m, region_filter)
    plot_hurricane_paths(m, filtered_df, hurricanes_to_plot)
    folium_static(m)
    st.write(f"Number of hurricanes displayed: {len(hurricanes_to_plot)}")
elif not filtered_df_category.empty and not hurricanes_in_region:
     st.warning(f"No hurricanes found for the selected region '{region_filter}' and criteria.")
elif not filtered_df_category.empty and hurricanes_in_region and not hurricanes_to_plot and not show_all:
     st.warning("Please select a hurricane from the dropdown.")
else:
    st.warning("No hurricanes found for the selected criteria.")

# Optional: Display filtered raw data
# st.subheader("Raw Data for Displayed Hurricanes")
# if not filtered_df.empty:
#     st.dataframe(filtered_df[filtered_df['hurricane_id'].isin(hurricanes_to_plot)])
# else:
#     st.write("No data to display.") 