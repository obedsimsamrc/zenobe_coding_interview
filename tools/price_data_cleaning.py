from scipy import stats
import pandas as pd
import numpy as np
import os
import logging
import statsmodels.api as sm

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


def missing_data_estimation(df: pd.DataFrame, col: str):

    missing_rows_df = df.loc[df[col].isna()]
    present_rows_df = df.loc[~df[col].isna()]

    # # Create some features to use for prediction
    # present_rows_df[""]
    #
    # # Add a constant column for the intercept
    # X = sm.add_constant(present_rows_df[feature_cols])
    # y = present_rows_df[col]
    #
    # # Fit the model
    # model = sm.OLS(y, X).fit()
    #
    # # Print the summary
    # print(model.summary())

    return missing_rows_df


def process_price_data(filename: str) -> pd.DataFrame:
    """

    :param filename:
    :return:
    """

    parent_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    file_location = os.path.join(parent_directory, "data", filename).replace('\\', '/')
    price_data = pd.read_csv(file_location, usecols=["time", "prices"], skip_blank_lines=True)
    market_price_df = pd.DataFrame(price_data)

    print(f"Length of dataframe imported: {len(market_price_df)}")

    # Need to convert the time column to a datetime format
    market_price_df["time"] = pd.to_datetime(market_price_df["time"], format="%d/%m/%Y %H:%M", errors="coerce")

    # This is the required datetime range to ensure no gaps in the pricing
    required_range = pd.DataFrame(index=pd.date_range(start=market_price_df["time"].iloc[0],
                                                      end=market_price_df["time"].iloc[-1], freq="30T"))

    # Need to remove duplicate timestamps from the dataframe and keep the first entry
    market_price_df.drop_duplicates(subset="time", inplace=True, keep="first")
    market_price_df.set_index('time', inplace=True)

    # Resample with the desired frequency to add missing datetime rows
    market_price_df = market_price_df.resample('30T').asfreq()[1:]

    missing_df = missing_data_estimation(market_price_df, col="prices")

    # Next if there are any empty rows we need to interpolate between the surrounding prices
    market_price_df["prices"].interpolate(method="linear", inplace=True)

    # Reset the index if needed
    market_price_df.reset_index(inplace=True)

    # We need to clean up any anomalous/outlier prices using the IQR method and replace with an interpolation
    market_price_df = replace_outliers_IQR(market_price_df, col="prices", q1_threshold=0.005, q3_threshold=0.995)

    # Change the prices column to float32 type to halve the memory usage
    market_price_df.astype({'prices': 'float32'})

    # Need to add a day index column for the optimisation set - create a boolean mask for rows where time is '00:00'
    mask = market_price_df['time'].dt.strftime('%H:%M') == '00:00'
    # Use cumsum on the boolean mask to create a counter
    market_price_df['day_count'] = mask.cumsum()

    # Add a column that increases by one each HH and resets at the end of the day
    market_price_df['hh_counter'] = market_price_df.groupby(market_price_df["time"].dt.date).cumcount() + 1

    print(f"Length of dataframe after cleaning: {len(market_price_df)}")

    assert len(market_price_df) == len(required_range), logging.error(f"{len(market_price_df)} != {len(required_range)}"
                                                                      f" - You are missing rows in the price data")

    return market_price_df


# market_price_df = process_price_data("input_data.csv")



