import hurdat2parser
import pandas as pd
import numpy as np

# Load the hurricane data
print("Loading hurricane data...")
atl = hurdat2parser.Hurdat2('hurdat2-1851-2024-040425.txt')

# Get all storms
storms = list(atl.tc.values())

# Print basic information
print("\nBasic Information:")
print(f"Number of storms: {len(storms)}")
years = list(atl.season.keys())
print(f"Years covered: {min(years)} to {max(years)}")

# Get the first storm
first_storm = storms[0]
print("\nFirst Storm Details:")
print(f"Storm ID: {first_storm.atcfid}")
print(f"Storm Name: {first_storm.name}")
print(f"Number of entries: {len(first_storm.entry)}")

# Show first entry details
first_entry = first_storm.entry[0]
print("\nFirst Entry Details:")
print(f"Date: {first_entry.date}")
print(f"Time: {first_entry.time}")
print(f"Status: {first_entry.status}")
print(f"Latitude: {first_entry.latitude}")
print(f"Longitude: {first_entry.longitude}")
print(f"Wind Speed: {first_entry.wind} knots")

# Print available methods and attributes
print("\nAvailable methods and attributes:")
print("\nHurdat2 object:")
print(dir(atl))
print("\nStorm object:")
print(dir(first_storm))
print("\nEntry object:")
print(dir(first_entry))

print("\n---\n")
# Analyze storms for years 2019 and 2024
for target_year in [2019, 2024]:
    print(f"Storms in {target_year}:")
    storms_in_year = [storm for storm in storms if storm.year == target_year]
    if not storms_in_year:
        print(f"  No storms found for {target_year}.")
        continue
    for storm in storms_in_year:
        print(f"- Storm ID: {storm.atcfid}, Name: {storm.name}, Entries: {len(storm.entry)}")
        # Show first and last entry for a quick overview
        if storm.entry:
            first = storm.entry[0]
            last = storm.entry[-1]
            print(f"    First: {first.date} {first.status} ({first.latitude}, {first.longitude}) Wind: {first.wind} kt")
            print(f"    Last:  {last.date} {last.status} ({last.latitude}, {last.longitude}) Wind: {last.wind} kt")
    print("") 