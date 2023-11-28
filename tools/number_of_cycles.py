import pandas as pd
import os


def cycling_limit_revenues(one_cycle_filename: str, two_cycle_filename: str):

    parent_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    file_location = os.path.join(parent_directory, "results/").replace('\\', '/')
    one_cycle = pd.read_csv(file_location + one_cycle_filename, date_format="%Y-%m-%d %H:%M:%S", parse_dates=["datetime"])
    two_cycle = pd.read_csv(file_location + two_cycle_filename, date_format="%Y-%m-%d %H:%M:%S", parse_dates=["datetime"])
    one_cycle_df = pd.DataFrame(one_cycle)
    two_cycle_df = pd.DataFrame(two_cycle)

    one_cycle_annual = one_cycle_df.groupby(one_cycle_df["datetime"].dt.year)[["DC Discharging power (MW)",
                                                                               "Trading Profits (£)"]].sum()

    two_cycle_annual = two_cycle_df.groupby(two_cycle_df["datetime"].dt.year)[["DC Discharging power (MW)",
                                                                               "Trading Profits (£)"]].sum()

    one_cycle_annual["Total Discharge (MWh)"] = one_cycle_annual["DC Discharging power (MW)"] / 2
    two_cycle_annual["Total Discharge (MWh)"] = two_cycle_annual["DC Discharging power (MW)"] / 2

    battery_power = 100
    one_cycle_annual["£_kW_year"] = one_cycle_annual["Trading Profits (£)"] / (battery_power * 1000)      # MW * 1000 =  kW
    two_cycle_annual["£_kW_year"] = two_cycle_annual["Trading Profits (£)"] / (battery_power * 1000)      # MW * 1000 =  kW

    merged_df = pd.merge(one_cycle_annual, two_cycle_annual, left_index=True, right_index=True,
                         suffixes=(' - One Cycle', ' - Two Cycle'))

    merged_df.to_csv(file_location + "cycling_limit_results.csv")

    return merged_df


merged_df = cycling_limit_revenues(one_cycle_filename="avg_1_cycle_optimised_df.csv",
                                   two_cycle_filename="avg_2_cycle_optimised_df.csv")

