"""
This module runs the battery optimisation model
"""

from calculate_revenues import calculate_revenues
from tools.price_data_cleaning import process_price_data
from battery_model import Battery
import pandas as pd
import time
import math
import os

# Import the market price data using the prepared function
market_price_df = process_price_data("input_data.csv")

import_rate = export_rate = market_price_df.copy().reset_index().set_index(["day_count", "hh_counter"])[['prices']]

master_list = []
status_SOC = [0.5 * 100]        # Initial state of charge set to 50% of capacity
battery_cycle_per_day = 1

# Track simulation time
tic = time.time()
for day_count in range(1, import_rate.index.get_level_values(0)[-1] + 1):
    print('Optimising day {}/{}'.format(day_count, math.ceil(len(market_price_df) * 365 / (8760 * 2))))

    import_rate_sliced = export_rate_sliced = import_rate.iloc[(day_count - 1) * 48:day_count * 48]
    import_rate_sliced_c = export_rate_sliced_c = import_rate_sliced.reset_index().set_index("hh_counter")[["prices"]]

    battery = Battery(battery_capacity=100,  # MWh
                      discharge_power=100,  # MW
                      charge_power=100,  # MW
                      charging_eff=0.922,  # charge_eff * discharge_eff = round_trip_eff of 85%
                      discharging_eff=0.922,
                      import_grid_lim=100,  # MW
                      export_grid_lim=100,  # MW
                      export_rate=export_rate_sliced_c["prices"],
                      import_rate=import_rate_sliced_c["prices"],
                      max_soc=1,  # p.u.
                      min_soc=0,  # p.u.
                      time_horizon=48,      # HH - Daily time horizon
                      init_charge=status_SOC[-1],  # This is looped so retrieve the previous loop final SoC
                      )

    battery.add_objective_function()
    battery.add_storage_constraints()
    battery.add_max_cycles_constraint(max_daily_cycles=battery_cycle_per_day)
    battery.solve_problem(mip_rel_gap=0.01, time_limit=10, day_count=day_count, solver_selection="cplex")
    hh_iteration_list, soc_tracker = battery.collect_opt_results()

    master_list.extend(hh_iteration_list)  # Add each iteration to the list
    status_SOC.extend(soc_tracker)

toc = time.time()
print('\n')
print('############## Total Simulation Time: ' + str(round(toc - tic, 2)) + ' seconds ##############')


# Convert the hourly timeseries list and the frequency market list to a dataframe
optimised_df = pd.DataFrame.from_records(master_list)
hourly_timerange = pd.date_range(start=market_price_df["time"].iloc[0],
                                 end=market_price_df["time"].iloc[-1],
                                 freq='30T').astype(str)

# Set the "datetime" as the first column in the DataFrame
optimised_df.insert(0, "datetime", hourly_timerange)


# Calculate the simple market strategy revenues
daily_revenues_df, annual_revenues_df = calculate_revenues(market_price_df,
                                                           battery_power=100,  # MW
                                                           trading_volume=100,  # MWh
                                                           optimised_df=optimised_df)

file_location = os.path.join(os.path.dirname(__file__), "results", f"avg_{battery_cycle_per_day}_cycle_optimised_df.csv").replace('\\', '/')
optimised_df.to_csv(file_location)

