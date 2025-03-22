import streamlit as st
import stateplane
import pandas as pd
from io import StringIO
import os

def convertToSPC(longitude, latitude):
    epsg_code = stateplane.identify(longitude, latitude)
    short_name = stateplane.identify(longitude, latitude, fmt='short')
    fips_code = stateplane.identify(longitude, latitude, fmt='fips')
    easting, northing = stateplane.from_lonlat(longitude, latitude)
    results = {
        'epsg_code': epsg_code,
        'short_name': short_name,
        'fips_code': fips_code,
        'easting': easting,
        'northing': northing,
    }
    return results

def export_to_csv(results_df):
    """
    Exports the results DataFrame to a CSV string.

    Args:
        results_df (pd.DataFrame): DataFrame containing the conversion results.

    Returns:
        str: CSV formatted string of the results.
    """
    csv_buffer = StringIO()
    results_df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()

st.title("SRI's SPC APP")
st.subheader("State Plane Coordinate Conversion for Backsights")

project_name = st.text_input("Project Name", value="Enter Project Name")
st.subheader("Enter up to 10 Data Points (Select points to include)")

select_all = st.checkbox("Select All")

data_points_input = []
ats_options = [1, 2, 3, 4, 5, 6, 7, 8]
for i in range(1, 11):
    cols = st.columns([0.1, 1, 1, 2])
    with cols[0]:
        include_point = st.checkbox("", value=select_all, key=f"include_{i}")
    with cols[1]:
        point_name_default = f"BS-{i:02d}"
        point_name = st.text_input("Point Name", value=point_name_default, key=f"point_name_{i}")
    with cols[2]:
        ats_no = st.selectbox("ATS No.", ats_options, index=0, key=f"ats_no_{i}")
    with cols[3]:
        coordinates_input = st.text_input("Latitude, Longitude", key=f"coordinates_{i}", help='Enter as "latitude, longitude"')
    data_points_input.append({"Include": include_point, "Point Name": point_name, "ATS No.": ats_no, "Coordinates": coordinates_input})

map_data = []
for point_data in data_points_input:
    if point_data['Include']:
        coordinates_str = point_data['Coordinates']
        try:
            latitude_str, longitude_str = map(str.strip, coordinates_str.split(','))
            latitude = float(latitude_str)
            longitude = float(longitude_str)
            map_data.append([latitude, longitude, point_data['Point Name']])
        except ValueError:
            pass  # Ignore invalid coordinate formats for the map
        except Exception as e:
            pass

if map_data:
    st.subheader("Map of Input Points")
    map_df = pd.DataFrame(map_data, columns=['latitude', 'longitude', 'point_name'])
    st.map(map_df)
else:
    st.subheader("Map of Input Points")
    st.info("Enter latitude and longitude coordinates to see them on the map.")

if st.button("Convert Selected Coordinates"):
    selected_data_points = [point for point in data_points_input if point['Include']]
    results = []
    fips_codes = set()
    epsg_codes = set()
    short_names = set()
    conversion_errors = {}

    if not selected_data_points:
        st.warning("Please select at least one point to convert.")
    else:
        for point_data in selected_data_points:
            coordinates_str = point_data['Coordinates']
            try:
                latitude_str, longitude_str = map(str.strip, coordinates_str.split(','))
                latitude = float(latitude_str)
                longitude = float(longitude_str)
                spc_info = convertToSPC(longitude, latitude)
                final_point_name = f"ATS{point_data['ATS No.']}-{point_data['Point Name']}"
                results.append({**point_data, 'Longitude': longitude, 'Latitude': latitude, **spc_info, "Final Point Name": final_point_name})
                fips_codes.add(spc_info['fips_code'])
                epsg_codes.add(spc_info['epsg_code'])
                short_names.add(spc_info['short_name'])
            except ValueError:
                conversion_errors[point_data['Point Name']] = f"Invalid format: '{coordinates_str}'. Please use 'latitude, longitude'."
            except Exception as e:
                conversion_errors[point_data['Point Name']] = f"An error occurred during conversion: {e}"

        if conversion_errors:
            st.error("The following points had issues with coordinate conversion:")
            for name, error in conversion_errors.items():
                st.error(f"- {name}: {error}")

        if results:
            if len(fips_codes) > 1 or len(epsg_codes) > 1 or len(short_names) > 1:
                st.warning("Warning: The selected latitude/longitude pairs belong to different State Plane Coordinate Systems.")
                common_epsg = "N/A"
                common_short_name = "N/A"
                common_fips_code = "N/A"
            else:
                common_epsg = epsg_codes.pop() if epsg_codes else "N/A"
                common_short_name = short_names.pop() if short_names else "N/A"
                common_fips_code = fips_codes.pop() if fips_codes else "N/A"

            st.subheader("Common Projection Information:")
            col_common1, col_common2, col_common3 = st.columns(3)
            with col_common1:
                st.metric("Common EPSG Code", common_epsg)
            with col_common2:
                st.metric("Common Short Name", common_short_name)
            with col_common3:
                st.metric("Common FIPS Code", common_fips_code)

            st.subheader("Conversion Results:")
            results_df = pd.DataFrame(results)
            st.dataframe(results_df)

            csv_filename = f"{project_name.replace(' ', '_')}_spc_results.csv"
            csv_data = export_to_csv(results_df)
            st.download_button(
                label="Download Results as CSV",
                data=csv_data,
                file_name=csv_filename,
                mime="text/csv",
            )

# --- Section for keeping track of generated CSVs ---
st.sidebar.subheader("Generated CSV Files")
if 'generated_csv_files' not in st.session_state:
    st.session_state['generated_csv_files'] = []

for filename in st.session_state['generated_csv_files']:
    st.sidebar.write(filename)

if st.button("Record Last Download"):
    if 'csv_filename' in locals():
        if csv_filename not in st.session_state['generated_csv_files']:
            st.session_state['generated_csv_files'].append(csv_filename)