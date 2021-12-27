import datetime
from collections import defaultdict

import dateparser
import numpy as np
import plotly.express as px
import pandas as pd
import streamlit as st


class Aggregation(object):
    def __init__(self, workouts_df, group_by=None):
        self.group_by = group_by

        # These accumulators hold the values over the iterations
        total_workouts = defaultdict(lambda: 0)
        total_time = defaultdict(lambda: 0.0)
        total_distance = defaultdict(lambda: 0.0)
        total_output = defaultdict(lambda: 0.0)
        total_output_minutes = defaultdict(lambda: 0.0)
        total_calories = defaultdict(lambda: 0.0)
        total_calories_minutes = defaultdict(lambda: 0.0)
        total_hr = defaultdict(lambda: 0.0)
        total_hr_minutes = defaultdict(lambda: 0.0)
        total_speed = defaultdict(lambda: 0.0)
        total_speed_minutes = defaultdict(lambda: 0.0)
        total_cadence = defaultdict(lambda: 0.0)
        total_cadence_minutes = defaultdict(lambda: 0.0)

        for _, row in workouts_df.iterrows():
            # Get the value for the group_by column
            if group_by:
                key = row[group_by]

                # Skip rows with an invalid key
                if pd.isnull(key):
                    continue
            else:
                key = "All Time"

            # Update the accumulators
            total_workouts[key] += 1
            if not pd.isna(row["Distance (mi)"]):
                total_distance[key] += row["Distance (mi)"]
            if not pd.isna(row["Length (minutes)"]):
                total_time[key] += row["Length (minutes)"]
                # These are nested inside the Length if-clause because we need to
                # weight the values by the workout length
                if not pd.isna(row["Total Output"]):
                    total_output[key] += row["Total Output"]
                    total_output_minutes[key] += row["Length (minutes)"]
                if not pd.isna(row["Calories Burned"]):
                    total_calories[key] += row["Calories Burned"]
                    total_calories_minutes[key] += row["Length (minutes)"]
                if not pd.isna(row["Avg. Heartrate"]):
                    total_hr[key] += row["Length (minutes)"] * row["Avg. Heartrate"]
                    total_hr_minutes[key] += row["Length (minutes)"]
                if not pd.isna(row["Avg. Speed (mph)"]):
                    total_speed[key] += (
                        row["Length (minutes)"] * row["Avg. Speed (mph)"]
                    )
                    total_speed_minutes[key] += row["Length (minutes)"]
                if not pd.isna(row["Avg. Cadence (RPM)"]):
                    total_cadence[key] += (
                        row["Length (minutes)"] * row["Avg. Cadence (RPM)"]
                    )
                    total_cadence_minutes[key] += row["Length (minutes)"]

        self.aggregated_df = pd.DataFrame(
            {
                "Total Workouts": pd.Series(total_workouts),
                "Total Minutes": pd.Series(total_time),
                "Total Distance": pd.Series(total_distance),
                "Total Output": pd.Series(total_output),
                "Total Calories": pd.Series(total_calories),
                "Output per Minute": pd.Series(total_output)
                / pd.Series(total_output_minutes),
                "Calories per Minute": pd.Series(total_calories)
                / pd.Series(total_calories_minutes),
                "Avg. Heartrate": pd.Series(total_hr) / pd.Series(total_hr_minutes),
                "Avg. Speed (mph)": pd.Series(total_speed)
                / pd.Series(total_speed_minutes),
                "Avg. Cadence (RPM)": pd.Series(total_cadence)
                / pd.Series(total_cadence_minutes),
            }
        )


def process_workouts_df():
    # Bail out if we don't have a workouts_df on the session_state
    if "workouts_df" not in st.session_state:
        return
    workouts_df = st.session_state["workouts_df"]

    # Convert to datetime
    def parse_datetime(date_str):
        # This is necessary because some Peloton workouts contain timezones
        # like (-05) which are not well-handled by dateparser
        return dateparser.parse(date_str.replace("(-", "(GMT-").replace("(+", "(GMT+"))

    # Parse the various versions of the Workout's Timestamp
    workouts_df["c_datetime"] = workouts_df["Workout Timestamp"].apply(
        lambda x: parse_datetime(x)
    )
    workouts_df["c_datetime"] = pd.to_datetime(workouts_df["c_datetime"], utc=True)
    workouts_df["c_day"] = workouts_df["c_datetime"].apply(lambda x: x.date())
    workouts_df["c_week"] = workouts_df["c_datetime"].apply(
        lambda x: datetime.datetime.strptime(
            "{}-{}-1".format(x.year, x.isocalendar()[1]), "%Y-%W-%w"
        ).date()
    )
    workouts_df["c_month"] = workouts_df["c_datetime"].apply(
        lambda x: x.strftime("%Y-%m")
    )
    workouts_df["c_year"] = workouts_df["c_datetime"].apply(lambda x: int(x.year))

    # Calculate some exercise-level stats
    workouts_df["c_calories_per_minute"] = (
        workouts_df["Calories Burned"] / workouts_df["Length (minutes)"]
    )
    workouts_df["c_output_per_minute"] = (
        workouts_df["Total Output"] / workouts_df["Length (minutes)"]
    )

    # After processing, reassign the processed DF to session_state
    st.session_state["workouts_df"] = workouts_df
    st.session_state["workouts_aggregation_all_time"] = Aggregation(workouts_df)
    st.session_state["workouts_aggregation_by_year"] = Aggregation(
        workouts_df, "c_year"
    )
    st.session_state["workouts_aggregation_by_month"] = Aggregation(
        workouts_df, "c_month"
    )
    st.session_state["workouts_aggregation_by_week"] = Aggregation(
        workouts_df, "c_week"
    )
    st.session_state["workouts_aggregation_by_day"] = Aggregation(workouts_df, "c_day")
    st.session_state["workouts_aggregation_by_instructor"] = Aggregation(
        workouts_df, "Instructor Name"
    )
    st.session_state["workouts_aggregation_by_class_length"] = Aggregation(
        workouts_df, "Length (minutes)"
    )


def render_upload_workouts():
    st.title("Upload Workouts")
    workouts_guide = """
    1. Go to https://members.onepeloton.com/profile/workouts
    2. Click 'DOWNLOAD WORKOUTS' and save your file
    3. Upload your saved workouts.csv file below
    """
    st.markdown(workouts_guide)

    workouts_help = """
    We do not log or save any of your personal data. To learn more, or
    to see the source code, go to https://github.com/jfkirk/pelotonnes.
    """
    raw_workouts = st.file_uploader(
        "Upload your workouts",
        type=["csv"],
        help=workouts_help,
    )

    if ("workouts_df" in st.session_state) and (raw_workouts is None):
        workouts_df = st.session_state["workouts_df"]

    if raw_workouts is not None:
        workouts_df = pd.read_csv(raw_workouts)
        workouts_df = workouts_df[workouts_df["Fitness Discipline"] == "Cycling"]
        st.session_state["workouts_df"] = workouts_df

        # Whether-or-not we've uploaded, process the DF
        st.markdown("Processing your workouts...")
        process_workouts_df()
        st.markdown("{} workouts processed!".format(len(workouts_df)))
        st.markdown("Use the sidebar to analyze your workouts.")

    if "workouts_df" in st.session_state:
        st.subheader("Cycling Workouts")
        st.dataframe(st.session_state["workouts_df"])


def render_all_time_stats():
    st.title("All-Time Stats")

    if "workouts_df" not in st.session_state:
        st.markdown(
            "Workouts have not been uploaded. See 'Upload Workouts' to the left."
        )
        return

    all_time_df = st.session_state["workouts_aggregation_all_time"].aggregated_df

    st.markdown(
        f"You have completed {all_time_df['Total Workouts'].sum()} cycling workouts with {len(st.session_state['workouts_aggregation_by_instructor'].aggregated_df)} different instructors."
    )

    total_mins = all_time_df["Total Minutes"].sum()
    total_hrs = total_mins / 60
    total_days = total_hrs / 24
    total_miles = all_time_df["Total Distance"].sum()
    st.markdown(
        "You have cycled for {:.0f} minutes (that's {:.2f} hours, or {:.2f} whole days) and rode {:.2f} miles in that time.".format(
            total_mins, total_hrs, total_days, total_miles
        )
    )

    st.markdown(
        "That makes for an all-time average speed of {:.2f} mph.".format(
            all_time_df["Avg. Speed (mph)"].mean()
        )
    )

    total_calories = all_time_df["Total Calories"].sum()
    total_pizzas = total_calories / 2240
    total_lbs_of_fat = total_calories / 3500
    st.markdown(
        "You've burned a total of {:.0f} calories in that time - that's equivalent to {:.2f} Large Pepperoni Pizzas from Domino's or {:.2f}lbs of body fat.".format(
            total_calories, total_pizzas, total_lbs_of_fat
        )
    )

    st.markdown("Keep it up!")

    st.dataframe(all_time_df.T)


def render_stats_by_time(aggregation, readable_time_unit):
    st.title(f"Stats By {readable_time_unit}")

    if "workouts_df" not in st.session_state:
        st.markdown(
            "Workouts have not been uploaded. See 'Upload Workouts' to the left."
        )
        return

    st.dataframe(aggregation.aggregated_df)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Total Minutes")
        fig = px.line(
            aggregation.aggregated_df["Total Minutes"].dropna(),
            labels={"index": f"{readable_time_unit}", "value": "Total Minutes"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Calories per Minute")
        fig = px.line(
            aggregation.aggregated_df["Calories per Minute"].dropna(),
            labels={"index": f"{readable_time_unit}", "value": "Calories per Minute"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Total Output")
        fig = px.line(
            aggregation.aggregated_df["Total Output"].dropna(),
            labels={"index": f"{readable_time_unit}", "value": "Total Output"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Total Workouts")
        fig = px.line(
            aggregation.aggregated_df["Total Workouts"].dropna(),
            labels={"index": f"{readable_time_unit}", "value": "Total Workouts"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Total Calories")
        fig = px.line(
            aggregation.aggregated_df["Total Calories"].dropna(),
            labels={"index": f"{readable_time_unit}", "value": "Total Calories"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Total Distance")
        fig = px.line(
            aggregation.aggregated_df["Total Distance"].dropna(),
            labels={"index": f"{readable_time_unit}", "value": "Total Distance"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Avg. Heartrate")
        fig = px.line(
            aggregation.aggregated_df["Avg. Heartrate"].dropna(),
            labels={"index": f"{readable_time_unit}", "value": "Avg. Heartrate"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Avg. Speed (mph)")
        fig = px.line(
            aggregation.aggregated_df["Avg. Speed (mph)"].dropna(),
            labels={"index": f"{readable_time_unit}", "value": "Avg. Speed (mph)"},
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


def render_stats_by_year():
    return render_stats_by_time(
        aggregation=st.session_state["workouts_aggregation_by_year"],
        readable_time_unit="Year",
    )


def render_stats_by_month():
    return render_stats_by_time(
        aggregation=st.session_state["workouts_aggregation_by_month"],
        readable_time_unit="Month",
    )


def render_stats_by_week():
    return render_stats_by_time(
        aggregation=st.session_state["workouts_aggregation_by_week"],
        readable_time_unit="Week",
    )


def render_stats_by_day():
    return render_stats_by_time(
        aggregation=st.session_state["workouts_aggregation_by_day"],
        readable_time_unit="Day",
    )


def render_stats_by_instructor():
    st.title("Stats By Instructor")

    if "workouts_df" not in st.session_state:
        st.markdown(
            "Workouts have not been uploaded. See 'Upload Workouts' to the left."
        )
        return

    aggregation = st.session_state["workouts_aggregation_by_instructor"]
    st.dataframe(aggregation.aggregated_df)

    with st.expander("Visualization Options"):
        log_scale = st.checkbox(
            "Use logarithmic scale for cumulative statistics",
            value=(
                True
                if aggregation.aggregated_df["Total Workouts"].max() >= 100
                else False
            ),
        )
        st.markdown(
            "Use logarithmic scale if you have a large number of workouts with your "
            + "top instructors and few workouts with others."
        )

    with st.expander("Visualize Output and Performance", expanded=True):

        c1, c2 = st.columns(2)
        with c1:
            fig = px.scatter(
                aggregation.aggregated_df,
                x="Total Minutes",
                y="Calories per Minute",
                text=aggregation.aggregated_df.index,
                log_x=log_scale,
            )
            fig.update_traces(marker_size=20)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.subheader("Calories per Minute vs Total Minutes")
            st.markdown(
                """
            This plot shows which instructors you spend the most time with vs how hard you work in their workouts. 
            
            Instructors in the top-left make you work hard, but you have not spent much time with them.

            Instructors in the bottom-right are ones you spend a lot of time with, but don't push you as hard.
            """
            )

        c1, c2 = st.columns(2)
        with c1:
            fig = px.scatter(
                aggregation.aggregated_df,
                x="Avg. Cadence (RPM)",
                y="Calories per Minute",
                text=aggregation.aggregated_df.index,
            )
            fig.update_traces(marker_size=20)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.subheader("Calories per Minute vs Avg. Cadence (RPM)")
            st.markdown(
                """
            This plot shows how hard you work with an instructor vs how fast you pedal with them.

            Instructors at the top-left get you working hard and pedaling slowly - usually at high resistance.

            Instructors at the bottom-right get you pedaling your quickest but not working very hard.
            """
            )

        c1, c2 = st.columns(2)
        with c1:
            sorted_opm = aggregation.aggregated_df["Output per Minute"].sort_values(
                ascending=False
            )
            fig = px.bar(
                sorted_opm, labels={"index": "Instructor", "value": "Output per Minute"}
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            sorted_cpm = aggregation.aggregated_df["Calories per Minute"].sort_values(
                ascending=False
            )
            fig = px.bar(
                sorted_cpm,
                labels={"index": "Instructor", "value": "Calories per Minute"},
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Avg. Speed (mph)")
            sorted_distance = (
                aggregation.aggregated_df["Avg. Speed (mph)"]
                .sort_values(ascending=False)
                .dropna()
            )
            fig = px.bar(
                sorted_distance,
                labels={"index": "Instructor", "value": "Avg. Speed (mph)"},
                log_y=log_scale,
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.subheader("Avg. Heartrate")
            sorted_calories = (
                aggregation.aggregated_df["Avg. Heartrate"]
                .sort_values(ascending=False)
                .dropna()
            )
            fig = px.bar(
                sorted_calories,
                labels={"index": "Instructor", "value": "Avg. Heartrate"},
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with st.expander("Visualize Totals", expanded=True):

        c1, c2 = st.columns(2)
        with c1:
            sorted_minutes = aggregation.aggregated_df["Total Minutes"].sort_values(
                ascending=False
            )
            fig = px.bar(
                sorted_minutes,
                labels={"index": "Instructor", "value": "Total Minutes"},
                log_y=log_scale,
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            sorted_output = (
                aggregation.aggregated_df["Total Output"]
                .sort_values(ascending=False)
                .dropna()
            )
            fig = px.bar(
                sorted_output,
                labels={"index": "Instructor", "value": "Total Output"},
                log_y=log_scale,
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            sorted_workouts = (
                aggregation.aggregated_df["Total Workouts"]
                .sort_values(ascending=False)
                .dropna()
            )
            fig = px.bar(
                sorted_workouts,
                labels={"index": "Instructor", "value": "Total Workouts"},
                log_y=log_scale,
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            sorted_calories = (
                aggregation.aggregated_df["Total Calories"]
                .sort_values(ascending=False)
                .dropna()
            )
            fig = px.bar(
                sorted_calories,
                labels={"index": "Instructor", "value": "Total Calories"},
                log_y=log_scale,
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            sorted_distance = (
                aggregation.aggregated_df["Total Distance"]
                .sort_values(ascending=False)
                .dropna()
            )
            fig = px.bar(
                sorted_distance,
                labels={"index": "Instructor", "value": "Total Distance"},
                log_y=log_scale,
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.empty()


def render_about():
    st.title("About Pelotonnes")
    st.markdown("Pelotonnes is a tool for visualizing your cycling workouts.")
    st.markdown(
        "Pelotonnes is not associated with Peloton Interactive, Inc. "
        + "- except as fans."
    )
    st.markdown("To learn more, [message James](https://twitter.com/Jiminy_Kirket).")
    st.markdown(
        "To see the source code, contribute, or report an issue,"
        + "[see GitHub](https://github.com/jfkirk/pelotonnes)."
    )


def main():
    st.set_page_config(page_title="Pelotonnes", layout="wide")
    st.sidebar.title("Pelotonnes")

    pages = {
        "Upload Workouts": render_upload_workouts,
        "All-Time Stats": render_all_time_stats,
        "Stats By Instructor": render_stats_by_instructor,
        "Stats By Year": render_stats_by_year,
        "Stats By Month": render_stats_by_month,
        "Stats By Week": render_stats_by_week,
        "Stats By Day": render_stats_by_day,
        "About": render_about,
    }
    app_mode = st.sidebar.radio("Tools", options=pages.keys())
    st.session_state["app_mode"] = app_mode

    # Render the selected page
    pages[app_mode]()


main()
