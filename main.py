import numpy as np
import pandas as pd
import zipfile
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from io import BytesIO
import streamlit as st

# Load name data
@st.cache_data
def load_name_data():
    names_file = 'https://www.ssa.gov/oact/babynames/names.zip'
    response = requests.get(names_file)
    with zipfile.ZipFile(BytesIO(response.content)) as z:
        dfs = []
        files = [file for file in z.namelist() if file.endswith('.txt')]
        for file in files:
            with z.open(file) as f:
                df = pd.read_csv(f, header=None)
                df.columns = ['name', 'sex', 'count']
                df['year'] = int(file[3:7])
                dfs.append(df)
        data = pd.concat(dfs, ignore_index=True)
    data['pct'] = data['count'] / data.groupby(['year', 'sex'])['count'].transform('sum')
    return data

# Identify one-hit wonders
@st.cache_data
def ohw(df):
    nunique_year = df.groupby(['name', 'sex'])['year'].nunique()
    one_hit_wonders = nunique_year[nunique_year == 1].index
    one_hit_wonder_data = df.set_index(['name', 'sex']).loc[one_hit_wonders].reset_index()
    return one_hit_wonder_data

# Load data
data = load_name_data()
ohw_data = ohw(data)

# App layout
st.title("My Baby Name App")

# Sidebar
st.sidebar.header("Filters")

# Default initial filter values
default_sex = "Both"
default_year_range = (data['year'].min(), data['year'].max())

# Initialize session state attributes if they don't exist
if 'selected_sex' not in st.session_state:
    st.session_state.selected_sex = default_sex

if 'year_range' not in st.session_state:
    st.session_state.year_range = default_year_range

# Reset button logic
reset_gender_button = st.sidebar.button("Reset Gender")
reset_year_button = st.sidebar.button("Reset Year Range")

# If reset gender button is clicked, reset the gender filter
if reset_gender_button:
    st.session_state.selected_sex = default_sex

# If reset year button is clicked, reset the year range filter
if reset_year_button:
    st.session_state.year_range = default_year_range

# Sidebar inputs
selected_sex = st.sidebar.radio("Select Gender", ["M", "F", "Both"], index=["M", "F", "Both"].index(st.session_state.selected_sex))
year_range = st.sidebar.slider("Select Year Range", 1880, 2022, st.session_state.year_range)

# Update session state with selected values
st.session_state.selected_sex = selected_sex
st.session_state.year_range = year_range

# Filter data based on sidebar inputs
if selected_sex != "Both":
    data_filtered = data[data['sex'] == selected_sex]
else:
    data_filtered = data
data_filtered = data_filtered[data_filtered['year'].between(*year_range)]

# Tabs
tab1, tab2 = st.tabs(["Name Trends", "Summary Statistics"])

# Tab 1: Name Trends
with tab1:
    st.header("Name Trends")

    # User input for name
    input_name = st.text_input("Enter a name:", value="Emma")
    name_data = data_filtered[data_filtered['name'].str.lower() == input_name.lower()]
    
    # Check if data exists for the input name
    if not name_data.empty:
        # Line chart for name trends
        fig = px.line(
            name_data, 
            x="year", 
            y="count", 
            color="sex", 
            title=f"Trend for the name '{input_name}'",
            labels={"year": "Year", "count": "Count"}
        )
        st.plotly_chart(fig)

        with st.expander("Name Popularity Over Time"):
            st.subheader("Name Popularity Over Time")
            st.write(f"Popularity of '{input_name}' as a percentage of total births each year.")
            fig_pct = px.area(
                name_data,
                x="year",
                y="pct",
                color="sex",
                title=f"Popularity of '{input_name}' Over Time",
                labels={"year": "Year", "pct": "Percentage"}
            )
            st.plotly_chart(fig_pct)

# Tab 2: Summary Statistics
with tab2:
    st.header("Summary Statistics")
    
    # One-hit wonders
    st.subheader("One-Hit Wonders")
    st.write("Names that appeared in only one year.")
    one_hit_sample = ohw_data.sample(10)
    st.dataframe(one_hit_sample)

    # Bar chart of most common names in the selected range
    st.subheader("Most Common Names")
    top_names = (
        data_filtered.groupby("name")["count"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    fig_bar = px.bar(
        top_names, 
        x="name", 
        y="count", 
        title="Top 10 Most Common Names", 
        labels={"name": "Name", "count": "Total Count"}
    )
    st.plotly_chart(fig_bar)
