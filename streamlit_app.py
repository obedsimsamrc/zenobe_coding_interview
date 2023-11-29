import streamlit as st
from timeseries_echart.line_chart import render_timeseries_line_chart
import pandas as pd
import os


def main():

    st.title("100MW/100MWh BESS Operation Profile")
    st.markdown('A Web App by Obed Sims ([@obedsims](https://www.linkedin.com/in/obedsims/))')

    # Retrieve the saved optimised battery profile from the data file
    file_location = os.path.join(os.path.dirname(__file__), "results/").replace('\\', '/')

    results_data = pd.read_csv(file_location + "avg_1_cycle_optimised_df.csv")
    results_df = pd.DataFrame(results_data)
    results_df["datetime"] = pd.to_datetime(results_df["datetime"], format="%Y-%m-%d %H:%M:%S")

    render_timeseries_line_chart(results_df)


if __name__ == "__main__":
    st.set_page_config(
        page_title="100MW/100MWh BESS Operation Profile", page_icon=":chart_with_upwards_trend:", layout="wide"
    )

    main()

