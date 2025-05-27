import streamlit as st
import pandas as pd
import plotly.express as px
from hurricane_county_matcher import match_hurricane_points_to_counties
from utils import calculate_weekly_frequency

st.set_page_config(page_title="Hurricane Frequency Analysis", page_icon="📊")

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

# --- PAGE CONTENT ---
st.title("Hurricane Frequency Analysis")

# Get the data
df = get_joined_points()
df_coastal = df[(df['region'] == 'Atlantic') | (df['region'] == 'Gulf of Mexico')].copy()

# Sidebar filters
st.sidebar.header("Filters")
min_year = int(df['year'].min())
max_year = int(df['year'].max())
start_year = st.sidebar.number_input("Start Year", min_value=min_year, max_value=max_year, value=max(min_year, 2014))
end_year = st.sidebar.number_input("End Year", min_value=min_year, max_value=max_year, value=max_year)
min_category = st.sidebar.selectbox("Minimum Category", options=[0, 1, 2, 3, 4, 5], index=0, 
                                  help="Show only hurricanes of this category or higher")

if start_year > end_year:
    st.sidebar.error("Start year must be less than or equal to end year.")
else:
    # Calculate frequencies for all regions
    freq_all = calculate_weekly_frequency(df, 'Any', start_year, end_year, min_category)
    freq_atlantic = calculate_weekly_frequency(df, 'Atlantic', start_year, end_year, min_category)
    freq_gulf = calculate_weekly_frequency(df, 'Gulf of Mexico', start_year, end_year, min_category)
    
    # Combine frequencies into a single DataFrame for export
    export_df = pd.DataFrame({
        'Week': freq_all['Week'],
        'Frequency_All': freq_all['Probability'],
        'Frequency_Atlantic': freq_atlantic['Probability'],
        'Frequency_Gulf': freq_gulf['Probability']
    })
    
    # Create a descriptive filename
    filename = f"hurricane_frequency_{start_year}-{end_year}_cat{min_category}+.csv"
    
    # Add download button at the top
    csv = export_df.to_csv(index=False)
    st.download_button(
        label="Download frequency data as CSV",
        data=csv,
        file_name=filename,
        mime="text/csv"
    )
    
    # Display all frequencies
    st.subheader("All Hurricanes Frequency")
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
    
    st.subheader("Atlantic Hurricanes Frequency")
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
    
    st.subheader("Gulf of Mexico Hurricanes Frequency")
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
