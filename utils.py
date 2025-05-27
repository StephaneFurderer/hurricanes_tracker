import pandas as pd

def calculate_weekly_frequency(df, selected_region, start_year, end_year, min_category=0):
    """
    Calculates the weekly frequency of hurricanes that crossed coastal counties 
    within a given year range, minimum category, and region.

    Args:
        df (pd.DataFrame): DataFrame containing hurricane data with 'year', 'date', 
                           'hurricane_id', 'category', and 'region' columns.
        selected_region (str): The region filter ('Any', 'Atlantic', 'Gulf of Mexico', 'Both').
        start_year (int): The start year for the frequency calculation.
        end_year (int): The end year for the frequency calculation.
        min_category (int): The minimum Saffir-Simpson category to include (default is 0).

    Returns:
        pd.DataFrame: DataFrame with 'Week' and 'Probability' columns for plotting.
    """
    # Filter data for the selected year range and minimum category
    df_filtered_year_cat = df[(df['year'] >= start_year) & (df['year'] <= end_year)].copy()

    # Only keep hurricanes that reached at least the minimum category within the selected year range
    hurricane_max_categories_in_period = df_filtered_year_cat.groupby('hurricane_id')['category'].max()
    valid_hurricanes_in_period = hurricane_max_categories_in_period[hurricane_max_categories_in_period >= min_category].index
    
    # Further filter data points to only include those from valid hurricanes
    df_valid_hurricanes = df_filtered_year_cat[df_filtered_year_cat['hurricane_id'].isin(valid_hurricanes_in_period)].copy()

    # Filter data to include only points that crossed Atlantic or Gulf counties
    df_coastal = df_valid_hurricanes[(df_valid_hurricanes['region'] == 'Atlantic') | (df_valid_hurricanes['region'] == 'Gulf of Mexico')].copy()

    # Apply region filter for frequency calculation based on coastal crossings
    if selected_region == 'Atlantic':
        df_freq = df_coastal[df_coastal['region'] == 'Atlantic'].copy()
    elif selected_region == 'Gulf of Mexico':
        df_freq = df_coastal[df_coastal['region'] == 'Gulf of Mexico'].copy()
    elif selected_region == 'Both':
        df_freq = df_coastal.copy() # 'Both' implies either Atlantic or Gulf crossing within the filtered set
    else:
        # If region is 'Any', use all coastal crossing points within the year/category filter
        df_freq = df_coastal.copy()
        
    # Convert date to datetime
    df_freq['date'] = pd.to_datetime(df_freq['date'])
    
    # Add week number (1-53 to cover all possible ISO weeks)
    df_freq['week'] = df_freq['date'].dt.isocalendar().week
    
    # Count unique hurricanes per week (each hurricane counted only once per week within the filtered region and year/cat range)
    # Group by year and week to find which valid hurricanes were active in coastal regions each week
    coastal_hurricanes_per_week_per_year = df_freq.groupby(['year', 'week'])['hurricane_id'].nunique().reset_index()

    # Now count the number of years for each week where there was at least one coastal hurricane meeting the criteria
    years_with_coastal_hurricanes = coastal_hurricanes_per_week_per_year[coastal_hurricanes_per_week_per_year['hurricane_id'] > 0].groupby('week')['year'].nunique()

    
    # Create a DataFrame with all weeks (1-53)
    all_weeks_df = pd.DataFrame({'Week': range(1, 54)})
    
    # Calculate probability (number of years with at least one hurricane in that week)
    years_in_period = end_year - start_year + 1
    weekly_probability = years_with_coastal_hurricanes / years_in_period
    
    # Create DataFrame for plotting, merging with all weeks and filling missing values with 0
    plot_df = all_weeks_df.merge(weekly_probability.rename('Probability'), left_on='Week', right_index=True, how='left').fillna(0)
    
    return plot_df 