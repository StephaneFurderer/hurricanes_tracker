import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from coastal_county_matcher import load_coastal_county_boundaries

def match_hurricane_points_to_counties(hurricane_df, 
                                        county_shapefile='cb_2023_us_county_500k.shp',
                                        county_excel='coastline-counties-list.xlsx',
                                        coastal_states=None):
    """
    Match hurricane path points to coastal counties.
    Args:
        hurricane_df (pd.DataFrame): Must have 'latitude' and 'longitude' columns.
        county_shapefile (str): Path to US counties shapefile.
        county_excel (str): Path to coastal counties Excel file.
        coastal_states (list or None): List of state names to filter (all caps). If None, uses all relevant states.
    Returns:
        GeoDataFrame: Hurricane points with county info (if matched).
    """
    # Load coastal county boundaries
    gdf_counties = load_coastal_county_boundaries(
        shapefile_path=county_shapefile,
        excel_path=county_excel,
        coastal_states=coastal_states
    )
    # Convert hurricane points to GeoDataFrame
    gdf_points = gpd.GeoDataFrame(
        hurricane_df.copy(),
        geometry=[Point(xy) for xy in zip(hurricane_df['longitude'], hurricane_df['latitude'])],
        crs='EPSG:4326'
    )
    # Ensure both are in the same CRS
    gdf_counties = gdf_counties.to_crs(gdf_points.crs)
    # Spatial join (left join: keep all hurricane points, add county info if matched)
    joined = gpd.sjoin(gdf_points, gdf_counties, how='left', predicate='within')
    return joined

if __name__ == "__main__":
    # Example usage with a small sample
    sample_points = pd.DataFrame({
        'latitude': [30.3322, 27.9506, 35.2271],
        'longitude': [-81.6557, -82.4572, -80.8431],
        'date': ['20230901', '20230902', '20230903']
    })
    result = match_hurricane_points_to_counties(sample_points)
    print(result[['latitude', 'longitude', 'date', 'state_name', 'county_name', 'region']]) 