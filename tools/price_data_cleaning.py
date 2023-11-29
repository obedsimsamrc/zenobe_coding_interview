import pandas as pd
import numpy as np
import os
import logging
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def replace_outliers_IQR(df, q1_threshold: float, q3_threshold: float, col: str):
    """
    Replace outliers in a DataFrame based on the IQR method with interpolation.

    :param df: DataFrame to process.
    :param q1_threshold: Lower threshold for the first quartile.
    :param q3_threshold: Upper threshold for the third quartile.
    :param col: Column containing the values to process.
    :return: df_interpolated: DataFrame with outliers replaced by interpolated values.
    """
    q1 = df[col].quantile(q1_threshold)
    q3 = df[col].quantile(q3_threshold)

    IQR = q3 - q1

    # Identify outliers
    outliers_mask = (df[col] < (q1 - 1.5 * IQR)) | (df[col] > (q3 + 1.5 * IQR))

    # Create a copy of the original DataFrame
    df_interpolated = df.copy()

    # Replace outliers with NaN
    df_interpolated.loc[outliers_mask, col] = np.nan

    logging.info(f"A total of {len(df_interpolated.loc[df_interpolated[col].isna()])} outliers were interpolated")

    # Interpolate missing values
    df_interpolated[col] = df_interpolated[col].interpolate()

    return df_interpolated


def missing_data_estimation(df: pd.DataFrame, col: str) -> pd.DataFrame | pd.DataFrame:
    """

    :param df: price dataframe including all the rows with missing prices from 10/2020 to 12/2020
    :param col: column to replace values
    :return: original dataframe with the missing values replaced with historical data
    """
    missing_rows_df = df[df[col].isna()]

    # Get the indexes of the missing rows region
    missing_rows_indexes = df[col].isna()

    if not missing_rows_df.empty:
        x = len(missing_rows_df)
        df_filled = missing_rows_df.copy()
        df_filled[col] = df[col].shift(periods=x)

        # Concatenate the filled and present rows
        df_combined = pd.concat([df_filled, df], axis=0).sort_index()

        # Remove duplicate time indexes
        df_combined = df_combined[~df_combined.index.duplicated(keep='last')]

        return df_combined, missing_rows_indexes
    else:
        return df.copy()


def process_price_data(filename: str, time_horizon: int) -> pd.DataFrame | pd.Index:
    """

    :param time_horizon: Time horizon to add as a column
    :param filename:
    :return:
    """

    parent_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    file_location = os.path.join(parent_directory, "data", filename).replace('\\', '/')
    price_data = pd.read_csv(file_location, usecols=["time", "prices"], skip_blank_lines=True)
    market_price_df = pd.DataFrame(price_data)

    logging.info(f"Length of dataframe imported: {len(market_price_df)}")

    # Need to convert the time column to a datetime format
    market_price_df["time"] = pd.to_datetime(market_price_df["time"], format="%d/%m/%Y %H:%M", errors="coerce")

    # This is the required datetime range to ensure no gaps in the price data
    required_range = pd.DataFrame(index=pd.date_range(start=market_price_df["time"].iloc[0],
                                                      end=market_price_df["time"].iloc[-1], freq="30T"))

    # Need to remove duplicate timestamps from the dataframe and keep the first entry
    market_price_df.drop_duplicates(subset="time", inplace=True, keep="first")
    market_price_df.set_index('time', inplace=True)

    # Resample with the desired frequency to add missing datetime rows
    market_price_df = market_price_df.resample('30T').asfreq()[1:]

    # Need to replace the blanks in the prices otherwise a simple interpolation will produce a poor estimation
    market_price_df, missing_rows_indexes = missing_data_estimation(market_price_df, col="prices")

    # Next if there are any empty rows we need to interpolate between the surrounding prices
    market_price_df["prices"].interpolate(method="linear", inplace=True)
    market_price_df.reset_index(inplace=True)

    # We need to clean up any anomalous/outlier prices using the IQR method and replace with an interpolation
    market_price_df = replace_outliers_IQR(market_price_df, col="prices", q1_threshold=0.005, q3_threshold=0.995)

    # Change the prices column to float32 type to halve the memory usage
    market_price_df.astype({'prices': 'float32'})

    # Need to add a day index column for the optimisation set - create a boolean mask for rows where time is '00:00'
    mask = market_price_df['time'].dt.strftime('%H:%M') == '00:00'
    # Use cumsum on the boolean mask to create a counter
    market_price_df['day_count'] = mask.cumsum()
    market_price_df['time_horizon'] = market_price_df.groupby(market_price_df.index // time_horizon).cumcount() + 1

    logging.info(f"Length of dataframe after cleaning: {len(market_price_df)}")

    assert len(market_price_df) == len(required_range), logging.error(f"{len(market_price_df)} != {len(required_range)}"
                                                                      f" - You are missing rows in the price data")

    return market_price_df, missing_rows_indexes



# market_price_df, missing_rows_indexes = process_price_data("input_data.csv",
#                                                            time_horizon=48)
#
# missing_rows_indexes = market_price_df.index[missing_rows_indexes]
#
# plt.figure(figsize=(16, 10))
#
# # Highlight the missing rows
# plt.scatter(missing_rows_indexes, market_price_df.loc[missing_rows_indexes]['prices'], color='red',
#             label='Missing Entries replaced', zorder=2)
# # Plot the entire dataset
# plt.plot(market_price_df.index, market_price_df['prices'], label='Entire Dataset', zorder=1)
#
# plt.xlabel('Time')
# plt.ylabel('Prices')
# plt.title('Price Data with Missing Rows Highlighted')
# plt.legend()
# plt.show()

