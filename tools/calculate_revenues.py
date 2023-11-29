"""
This function calculates the revenues from operating the battery according to two strategies:

1. Your boss tells you that the best trading strategy that a battery with those specs can achieve is the following:
every day buy 100 MWh of energy at the hour with the lowest price and sell 100 MWh of energy at the hour with
the highest price.

2. Using an MIP optimisation strategy

"""
import pandas as pd


def calculate_revenues(prices_df: pd.DataFrame, optimised_df: pd.DataFrame, trading_volume: float | int,
                       battery_power: float | int, round_trip_eff: float):
    """
    Calculate daily and annual revenues based on HH prices and trading volume for both strategies
    TODO: Ensure that the battery charges each day before it discharges.

    :param round_trip_eff: Round trip efficiency p.u.
    :param optimised_df: This is the result df from the optimisation
    :param battery_power: Battery discharge power in MW
    :param prices_df: DataFrame containing HH prices with a datetime column named "time".
    :param trading_volume: Trading volume in MWh.
    :return: daily_df: DataFrame with daily revenues.
             annual_df: DataFrame with annual revenues.
    """
    if 'time' not in prices_df:
        prices_df.reset_index(inplace=True)

    prices_df["time"] = pd.to_datetime(prices_df["time"], format="%Y-%m-%d %H:%M")
    optimised_df["datetime"] = pd.to_datetime(optimised_df["datetime"], format="%Y-%m-%d %H:%M:%S")

    ################################################################################################
    # every day buy 100 MWh of energy at the hour with the lowest price and sell 100 MWh of energy at the hour with
    # the highest price.
    ################################################################################################

    # First, set the datetime column as the index
    prices_df.set_index("time", inplace=True, drop=True)
    # So we need to convert the HH price profile to hourly and take the mean price in the 2 HH intervals
    hourly_price_df = prices_df.resample("60min").mean()
    hourly_price_df.reset_index(inplace=True)

    hourly_price_df.sort_values(by=["day_count", "prices"], ascending=[True, True], inplace=True)

    # Group by day_count and apply a function to get the highest and lowest prices else return 0 for that row
    daily_df = hourly_price_df.groupby("day_count").apply(
        lambda x: pd.Series({
            'max_price': x.loc[x['prices'].idxmax()]['prices'],
            'min_price': x.loc[x['prices'].idxmin()]['prices']
        }) if x['prices'].idxmax() > x['prices'].idxmin() else pd.Series({'max_price': 0, 'min_price': 0})
    )

    daily_df["daily_price_spread"] = daily_df["max_price"] - daily_df["min_price"]      # hourly spread
    daily_df["simple_daily_profit"] = daily_df["daily_price_spread"] * trading_volume * round_trip_eff # £/MWh * MWh = £
    daily_df.index = pd.date_range(start=prices_df.index[0], freq="1D", periods=len(daily_df))

    # Group by year
    annual_df = daily_df.groupby(daily_df.index.year)[["simple_daily_profit"]].sum()
    annual_df.rename(columns={"simple_daily_profit": "simple_annual_profit"}, inplace=True)
    annual_df["simple_£_kW_year"] = annual_df["simple_annual_profit"] / (battery_power * 1000)      # MW * 1000 =  kW

    ################################################################################################
    # Now need to calculate the revenues from the optimisation model
    ################################################################################################

    optimised_daily_df = optimised_df.groupby(optimised_df["datetime"].dt.date)[["Trading Profits (£)"]].sum()
    daily_df["optimised_daily_profit"] = optimised_daily_df["Trading Profits (£)"]

    optimised_daily_df.index = pd.to_datetime(optimised_daily_df.index, format="%Y-%m-%d")

    optimised_annual_df = optimised_daily_df.groupby(optimised_daily_df.index.year)[["Trading Profits (£)"]].sum()
    annual_df["optimised_annual_profit"] = optimised_annual_df["Trading Profits (£)"]
    annual_df["optimised_£_kW_year"] = annual_df["optimised_annual_profit"] / (battery_power * 1000)  # MW * 1000 =  kW

    return daily_df, annual_df


