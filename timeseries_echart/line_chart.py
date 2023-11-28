from streamlit_echarts import st_echarts
import pandas as pd


def render_timeseries_line_chart(results_df: pd.DataFrame):

    x_axis_array = results_df["datetime"].dt.strftime('%H:%M %d-%m-%Y').tolist()

    charge_volume = [round(value, 1) for value in results_df["DC Charging power (MW)"]]
    discharge_volume = [round(value, 1) for value in results_df["DC Discharging power (MW)"]]
    price = results_df["Import Price (£/MWh)"].tolist()
    soc = [round(value, 1) for value in results_df["State of Charge (%)"]]

    options = {
        "grid": [
            {
                "left": '97%',
                "right": '96%',
                "top": '85%',
                "bottom": '80%',
            },
        ],
        "legend": {
            "show": True,
            "data": ["Charge (MW)", "Discharge (MW)", "Power Price (£/MWh)", "State of Charge (%)"],
        },
        "tooltip": {
            "trigger": 'axis',
            "axisPointer": {
                "type": 'cross',
                "label": {
                    "backgroundColor": '#6a7985',
                }
            },
        },

        "xAxis": {
            "type": "category",
            "data": x_axis_array,
            "nameTextStyle": {
                "fontWeight": 'bolder',
            },
        },
        "yAxis": {"type": "value",
                  "nameTextStyle": {
                      "fontWeight": 'bolder',
                  },
                  "splitLine": {
                      "show": False,
                  },

                  },
        "dataZoom": [
            {
                "type": 'inside',
                "start": 0,
                "end": 1
            },
            {
                "start": 0,
                "end": 10
            }
        ],
        "series": [{
            "name": 'Charge (MW)',
            "type": 'bar',
            "data": charge_volume,
            # "smooth": 0.2,
            "color": '#000000',
            "showSymbol": False,

            },
            {
                "name": 'Discharge (MW)',
                "type": 'bar',
                "data": discharge_volume,
                # "smooth": 0.2,
                "color": '#FFB892',
                "showSymbol": False,

            },
            {
                "name": 'Power Price (£/MWh)',
                "type": 'line',
                "data": price,
                "smooth": 0.2,
                "color": '#7A2A2A',
                "showSymbol": False,
            },
            {
                "name": 'State of Charge (%)',
                "type": 'line',
                "areaStyle": {'origin': 'auto',
                              'opacity': 0.4,
                  },
                "data": soc,
                "smooth": 0.2,
                "color": '#99A1B7',
                "showSymbol": False,
            }
    ],
    }
    st_echarts(
        options=options, height="500px",
    )
