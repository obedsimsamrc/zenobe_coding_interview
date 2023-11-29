import pandas as pd
import os


def cycling_limit_revenues(one_cycle_filename: str, two_cycle_filename: str) -> pd.DataFrame:

    # Get the parent directory
    parent_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Define filenames and file locations
    file_location = os.path.join(parent_directory, "results/").replace('\\', '/')

    # Read CSV files into DataFrames
    one_cycle_df = pd.read_csv(os.path.join(file_location, one_cycle_filename), parse_dates=["datetime"])
    two_cycle_df = pd.read_csv(os.path.join(file_location, two_cycle_filename), parse_dates=["datetime"])

    # Group by year and sum relevant columns
    one_cycle_annual = one_cycle_df.groupby(one_cycle_df["datetime"].dt.year)[
        ["DC Discharging power (MW)", "Trading Profits (£)"]].sum()
    two_cycle_annual = two_cycle_df.groupby(two_cycle_df["datetime"].dt.year)[
        ["DC Discharging power (MW)", "Trading Profits (£)"]].sum()

    # Calculate total discharge
    one_cycle_annual["Total Discharge (MWh)"] = one_cycle_annual["DC Discharging power (MW)"] / 2
    two_cycle_annual["Total Discharge (MWh)"] = two_cycle_annual["DC Discharging power (MW)"] / 2

    battery_power = 100
    one_cycle_annual["£_kW_year"] = one_cycle_annual["Trading Profits (£)"] / (battery_power * 1000)   # MW * 1000 =  kW
    two_cycle_annual["£_kW_year"] = two_cycle_annual["Trading Profits (£)"] / (battery_power * 1000)   # MW * 1000 =  kW

    cycle_comparison_df = pd.merge(one_cycle_annual, two_cycle_annual, left_index=True, right_index=True,
                                   suffixes=(' - One Cycle', ' - Two Cycle'))

    # merged_df.to_csv(file_location + "cycling_limit_results.csv")

    return cycle_comparison_df


merged_df = cycling_limit_revenues(one_cycle_filename="avg_1_cycle_optimised_df.csv",
                                   two_cycle_filename="avg_2_cycle_optimised_df.csv")

