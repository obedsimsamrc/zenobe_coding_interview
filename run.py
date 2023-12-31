"""
This module runs the battery optimisation model
"""

from tools.calculate_revenues import calculate_revenues
from tools.price_data_cleaning import process_price_data
from battery_model import Battery
import pandas as pd
import numpy as np
import time
import math
import os

master_list = []
status_SOC = [0.5 * 100]        # Initial state of charge set to 50% of 100MWh capacity
cycles_per_time_horizon = 1*365     # Total number of cycles per time horizon
time_horizon = 48*365               # Time horizon in half hours


# Import the market price data using the prepared function
market_price_df, missing_rows_indexes = process_price_data("input_data.csv", time_horizon=time_horizon)
import_rate = export_rate = market_price_df.copy().reset_index().set_index(["day_count", "time_horizon"])[['prices']]


# Track simulation time
tic = time.time()
for day_count in range(1, math.ceil(import_rate.index.get_level_values(0)[-1] / (time_horizon / 48)) + 1):

    import_rate_sliced = export_rate_sliced = import_rate.iloc[(day_count - 1) * time_horizon:day_count * time_horizon]
    if len(import_rate_sliced) < time_horizon:
        import_rate_sliced = export_rate_sliced = import_rate.iloc[(day_count - 1) * time_horizon:]

    import_rate_sliced.index = export_rate_sliced.index = np.arange(1, len(import_rate_sliced) + 1)

    print('\n')
    print('Optimising horizon {}/{}'.format(day_count,
                                            math.ceil(import_rate.index.get_level_values(0)[-1] / (time_horizon / 48))))

    battery = Battery(battery_capacity=100,  # MWh
                      discharge_power=100,  # MW
                      charge_power=100,  # MW
                      charging_eff=0.922,  # charge_eff * discharge_eff = round_trip_eff of 85%
                      discharging_eff=0.922,
                      import_grid_lim=100,  # MW
                      export_grid_lim=100,  # MW
                      export_rate=export_rate_sliced["prices"],
                      import_rate=import_rate_sliced["prices"],
                      max_soc=1,  # p.u.
                      min_soc=0,  # p.u.
                      init_charge=status_SOC[-1],  # This is looped so retrieve the previous loop final SoC
                      )

    battery.add_objective_function()
    battery.add_storage_constraints()
    battery.add_max_cycles_constraint(max_daily_cycles=cycles_per_time_horizon)
    battery.solve_problem(mip_rel_gap=0.0001, time_limit=20, day_count=day_count, solver_selection="cplex")
    hh_iteration_list, soc_tracker = battery.collect_opt_results()

    master_list.extend(hh_iteration_list)  # Add each iteration to the list
    status_SOC.extend(soc_tracker)

toc = time.time()
print('\n')
print('############## Total Simulation Time: ' + str(round(toc - tic, 2)) + ' seconds ##############')


# Convert the hourly timeseries list and the frequency market list to a dataframe
optimised_df = pd.DataFrame.from_records(master_list)
hourly_timerange = pd.date_range(start=market_price_df["time"].iloc[0], end=market_price_df["time"].iloc[-1],
                                 freq='30T').astype(str)
# Set the "datetime" as the first column in the DataFrame
optimised_df.insert(0, "datetime", hourly_timerange)

assert not ((optimised_df['Charge Bool'] == 1) & (optimised_df['Discharge Bool'] == 1)).any(),\
    "Error: Occurrences where both discharge and charge are occurring at the same time."


# Calculate the simple market strategy revenues
daily_revenues_df, annual_revenues_df = calculate_revenues(market_price_df,
                                                           battery_power=100,  # MW
                                                           trading_volume=100,  # MWh
                                                           optimised_df=optimised_df,
                                                           round_trip_eff=0.85)


file_location = os.path.join(os.path.dirname(__file__), "results/").replace('\\', '/')
annual_revenues_df.to_csv(file_location + f"annual_profit_by_scenario.csv")
daily_revenues_df.to_csv(file_location + f"daily_profit_by_scenario.csv")


# optimised_df.to_csv(file_location + f"avg_{1}_cycle_optimised_df.csv")



