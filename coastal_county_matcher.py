import pandas as pd
import geopandas as gpd

COASTAL_REGIONS = ['Atlantic', 'Gulf of Mexico']

def get_all_coastal_states(excel_path='coastline-counties-list.xlsx'):
    df = pd.read_excel(excel_path, skiprows=3)
    df.columns = [
        'state_county_fips','state_fips','county_fips','county_name','state_name', 'region', 'population'
    ]
    df = df.dropna(subset=['county_fips', 'state_name'])
    df = df[df['region'].isin(COASTAL_REGIONS)]
    states = sorted(df['state_name'].str.upper().unique())
    return states

def load_coastal_counties(excel_path='coastline-counties-list.xlsx', coastal_states=None):
    """
    Load and filter coastal counties from the Excel file.
    Args:
        excel_path (str): Path to the Excel file.
        coastal_states (list or None): List of state names to filter (all caps). If None, uses all relevant states.
    Returns:
        pd.DataFrame: Filtered coastal counties.
    """
    if coastal_states is None:
        coastal_states = get_all_coastal_states(excel_path)
    df = pd.read_excel(excel_path, skiprows=3)
    df.columns = [
        'state_county_fips','state_fips','county_fips','county_name','state_name', 'region', 'population'
    ]
    df = df.dropna(subset=['county_fips', 'state_name'])
    df = df[
        df['state_name'].str.upper().isin(coastal_states) &
        df['region'].isin(COASTAL_REGIONS)
    ]
    df['county_fips'] = df['county_fips'].astype(str).str.zfill(3)
    df['state_fips'] = df['state_fips'].astype(str).str.zfill(2)
    df['state_county_fips'] = df['state_county_fips'].astype(str).str.zfill(5)
    return df[['state_name', 'county_name', 'state_county_fips', 'county_fips', 'region']].reset_index(drop=True)

def load_coastal_county_boundaries(
    shapefile_path='cb_2023_us_county_500k.shp',
    excel_path='coastline-counties-list.xlsx',
    coastal_states=None
):
    """
    Load US county boundaries and filter to only coastal counties (Atlantic/Gulf).
    Returns a GeoDataFrame with geometry and county info.
    """
    # Load all counties
    gdf = gpd.read_file(shapefile_path)
    # Load coastal counties list
    coastal_df = load_coastal_counties(excel_path, coastal_states)
    # The shapefile uses state and county FIPS codes (STATEFP, COUNTYFP)
    gdf['state_county_fips'] = gdf['STATEFP'].astype(str).str.zfill(2) + gdf['COUNTYFP'].astype(str).str.zfill(3)
    # Filter to only coastal counties
    gdf_coastal = gdf[gdf['state_county_fips'].isin(coastal_df['state_county_fips'])].copy()
    # Merge in region info
    gdf_coastal = gdf_coastal.merge(coastal_df, on='state_county_fips', how='left')
    return gdf_coastal

if __name__ == "__main__":
    states = get_all_coastal_states()
    print(f"All states with Atlantic or Gulf of Mexico coastline counties: {states}")
    df = load_coastal_counties()
    print(df.head(20))
    print(f"Total coastal counties in all relevant states (Atlantic/Gulf): {len(df)}")
    # Example: filter for just Florida
    df_fl = load_coastal_counties(coastal_states=['FLORIDA'])
    print(f"\nTotal coastal counties in Florida: {len(df_fl)}")
    # Load and preview coastal county boundaries
    gdf_coastal = load_coastal_county_boundaries()
    print(gdf_coastal[['state_name', 'county_name', 'region', 'geometry']].head())
    print(f"Total coastal county polygons: {len(gdf_coastal)}") 