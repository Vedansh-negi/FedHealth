import streamlit as st
import pandas as pd
import plotly.express as px

from database.federated_db import get_federated_connection
from database.hospital_db import get_hospital_connection


st.set_page_config(
    page_title="FedHealth | Federated Healthcare Intelligence",
    page_icon="🏥",
    layout="wide",
)

st.title("🏥 FedHealth")
st.caption("Federated Healthcare Intelligence Platform | OS + DBMS + Machine Learning")

st.info(
    "Prototype status: hospital-local datasets, local model training, federated "
    "round history, global evaluation, centralized comparison, PostgreSQL persistence, "
    "and OS/DBMS demonstrations are implemented. Full end-to-end integration, "
    "additional validation, and performance improvements remain future work."
)


@st.cache_data(ttl=10)
def load_federated_data():
    conn = get_federated_connection()
    try:
        rounds = pd.read_sql_query(
            """
            SELECT round_id, round_number, global_model_version,
                   start_time, end_time, status, aggregation_method
            FROM federated_rounds
            ORDER BY round_number DESC
            """,
            conn,
        )
        models = pd.read_sql_query(
            """
            SELECT global_model_id, round_id, model_version, accuracy,
                   precision_score, recall_score, f1_score, created_at
            FROM global_models
            ORDER BY global_model_id DESC
            """,
            conn,
        )
        updates = pd.read_sql_query(
            """
            SELECT hospital_id, round_id, sample_count, accuracy,
                   precision_score, recall_score, f1_score,
                   training_time_seconds, created_at
            FROM model_updates
            ORDER BY update_id DESC
            """,
            conn,
        )
        hospitals = pd.read_sql_query(
            """
            SELECT hospital_id, hospital_name, database_name, status
            FROM hospitals
            ORDER BY hospital_id
            """,
            conn,
        )
        return rounds, models, updates, hospitals
    finally:
        conn.close()


@st.cache_data(ttl=10)
def load_hospital_training(hospital_id):
    conn = get_hospital_connection(int(hospital_id))
    try:
        return pd.read_sql_query(
            """
            SELECT round_number, model_version, sample_count, accuracy,
                   precision_score, recall_score, f1_score, loss,
                   training_time_seconds, status
            FROM training_runs
            ORDER BY run_id DESC
            LIMIT 20
            """,
            conn,
        )
    finally:
        conn.close()


@st.cache_data(ttl=10)
def load_model_comparison():
    conn = get_federated_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT model_name, accuracy, precision_score, recall_score,
                   f1_score, roc_auc, evaluation_set, comparison_run,
                   comparison_id
            FROM model_comparison
            WHERE comparison_run = (
                SELECT comparison_run
                FROM model_comparison
                ORDER BY comparison_id DESC
                LIMIT 1
            )
            ORDER BY comparison_id
            """,
            conn,
        )
    finally:
        conn.close()


@st.cache_data(ttl=10)
def load_os_process_logs():
    conn = get_federated_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT process_id, process_name, scheduling_algorithm,
                   arrival_time, start_time, completion_time,
                   waiting_time_seconds, turnaround_time_seconds,
                   response_time_seconds, cpu_usage, memory_usage_mb, status
            FROM os_process_logs
            ORDER BY process_id DESC
            LIMIT 100
            """,
            conn,
        )
    finally:
        conn.close()


@st.cache_data(ttl=10)
def load_resource_logs():
    conn = get_federated_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT snapshot_id, cpu_percent, memory_percent,
                   system_memory_used_mb, process_memory_mb,
                   available_memory_mb, recorded_at
            FROM resource_monitor_logs
            ORDER BY snapshot_id DESC
            LIMIT 50
            """,
            conn,
        )
    finally:
        conn.close()


def metric_text(value, digits=3):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.{digits}f}"


try:
    rounds, models, updates, hospitals = load_federated_data()

    if hospitals.empty:
        st.warning("No hospitals are registered in the federated database.")
        st.stop()

    latest_model = models.iloc[0] if not models.empty else None
    total_rounds = len(rounds)
    completed_rounds = int((rounds["status"] == "COMPLETED").sum()) if not rounds.empty else 0
    failed_rounds = int((rounds["status"] == "FAILED").sum()) if not rounds.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registered Hospitals", len(hospitals))
    c2.metric("Federated Rounds", total_rounds)
    c3.metric("Completed Rounds", completed_rounds)
    accuracy = latest_model["accuracy"] if latest_model is not None else None
    c4.metric(
        "Latest Global Accuracy",
        f"{float(accuracy):.2%}"
        if accuracy is not None and pd.notna(accuracy)
        else "Not evaluated",
    )

    if failed_rounds:
        st.warning(
            f"{failed_rounds} round(s) failed. They remain in the audit history; "
            "the failed round is not counted as a completed round."
        )

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("Hospital Network")
        st.dataframe(
            hospitals.rename(
                columns={
                    "hospital_id": "ID",
                    "hospital_name": "Hospital",
                    "database_name": "Database",
                    "status": "Status",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )

    with right:
        st.subheader("Latest Global Model")
        if latest_model is not None:
            st.write(f"**Version:** {latest_model['model_version']}")
            cols = st.columns(3)
            for col, label, key in zip(
                cols,
                ["Precision", "Recall", "F1 Score"],
                ["precision_score", "recall_score", "f1_score"],
            ):
                col.metric(label, metric_text(latest_model[key]))
            st.caption("Global metrics are evaluated on the held-out common test set.")
        else:
            st.warning("No global model has been saved yet.")

    st.divider()
    st.subheader("Local Hospital Model Performance")

    if not updates.empty and latest_model is not None:
        latest_updates = updates[updates["round_id"] == latest_model["round_id"]].copy()
        if not latest_updates.empty:
            latest_updates["Hospital"] = latest_updates["hospital_id"].map(
                lambda value: f"Hospital {value}"
            )
            chart_data = latest_updates.melt(
                id_vars=["Hospital"],
                value_vars=["accuracy", "recall_score", "f1_score"],
                var_name="Metric",
                value_name="Score",
            )
            chart_data["Metric"] = chart_data["Metric"].replace(
                {
                    "accuracy": "Accuracy",
                    "recall_score": "Recall",
                    "f1_score": "F1 Score",
                }
            )
            fig = px.bar(
                chart_data,
                x="Hospital",
                y="Score",
                color="Metric",
                barmode="group",
                title="Local validation metrics — latest global round",
                range_y=[0, 1],
            )
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                latest_updates[
                    [
                        "Hospital",
                        "sample_count",
                        "accuracy",
                        "precision_score",
                        "recall_score",
                        "f1_score",
                        "training_time_seconds",
                    ]
                ].rename(
                    columns={
                        "sample_count": "Training Samples",
                        "accuracy": "Validation Accuracy",
                        "precision_score": "Validation Precision",
                        "recall_score": "Validation Recall",
                        "f1_score": "Validation F1",
                        "training_time_seconds": "Training Time (s)",
                    }
                ).round(4),
                hide_index=True,
                use_container_width=True,
            )
            st.caption(
                "Local update metrics are validation metrics; they are not directly "
                "interchangeable with global held-out test metrics."
            )
        else:
            st.info("No local updates are recorded for the latest global model's round.")
    else:
        st.info("No local model updates are available yet.")

    st.divider()
    st.header("Local vs Federated vs Centralized Learning")
    try:
        comparison = load_model_comparison()
    except Exception as comparison_error:
        comparison = pd.DataFrame()
        st.warning("Could not load model comparison results.")
        st.caption(str(comparison_error))

    if not comparison.empty:
        st.caption(
            "The models in this comparison were evaluated on the same held-out common test dataset."
        )
        chart_data = comparison.melt(
            id_vars=["model_name"],
            value_vars=["accuracy", "precision_score", "recall_score", "f1_score", "roc_auc"],
            var_name="Metric",
            value_name="Score",
        )
        chart_data["Metric"] = chart_data["Metric"].replace(
            {
                "accuracy": "Accuracy",
                "precision_score": "Precision",
                "recall_score": "Recall",
                "f1_score": "F1 Score",
                "roc_auc": "ROC-AUC",
            }
        )
        fig = px.bar(
            chart_data,
            x="model_name",
            y="Score",
            color="Metric",
            barmode="group",
            title="Model Performance on the Common Test Dataset",
            range_y=[0, 1],
        )
        fig.update_layout(xaxis_title="Model", yaxis_title="Score", legend_title="Metric")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            comparison[
                ["model_name", "accuracy", "precision_score", "recall_score", "f1_score", "roc_auc"]
            ].rename(
                columns={
                    "model_name": "Model",
                    "accuracy": "Accuracy",
                    "precision_score": "Precision",
                    "recall_score": "Recall",
                    "f1_score": "F1 Score",
                    "roc_auc": "ROC-AUC",
                }
            ).round(4),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No comparison run found yet. Run `python -m ml.centralized_training` when ready.")

    st.divider()
    st.subheader("Federated Round History")
    if not rounds.empty:
        st.dataframe(
            rounds.rename(
                columns={
                    "round_id": "Round ID",
                    "round_number": "Round",
                    "global_model_version": "Global Model",
                    "start_time": "Started",
                    "end_time": "Ended",
                    "status": "Status",
                    "aggregation_method": "Aggregation",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
        st.caption(
            "Rounds 2–3 used parameter averaging. Round 4 is recorded as iterative "
            "FedAvg using mini-batch SGD. Round 1 failed and remains in the audit history."
        )
    else:
        st.info("No federated rounds have been recorded.")

    st.divider()
    st.subheader("Hospital Training History")
    hospital_ids = hospitals["hospital_id"].astype(int).tolist()
    selected_hospital = st.selectbox(
        "Select a hospital",
        options=hospital_ids,
        format_func=lambda value: f"Hospital {value}",
    )
    try:
        history = load_hospital_training(selected_hospital)
        if not history.empty:
            st.dataframe(history, hide_index=True, use_container_width=True)
        else:
            st.info("No local training records found for this hospital.")
    except Exception as history_error:
        st.error("Could not load this hospital's training history.")
        st.exception(history_error)

    st.divider()
    st.header("Operating System: Process Scheduling")
    st.caption(
        "Round Robin results below are scheduler simulations with simulated time units; "
        "they are not measurements from the computer's real CPU scheduler."
    )

    try:
        os_logs = load_os_process_logs()
        if not os_logs.empty:
            rr_logs = os_logs[
                os_logs["scheduling_algorithm"].astype(str).str.casefold() == "round robin"
            ].copy()
            worker_logs = os_logs[
                os_logs["scheduling_algorithm"].astype(str).str.casefold() != "round robin"
            ].copy()

            if not rr_logs.empty:
                st.subheader("Round Robin Scheduling Simulation")
                os_c1, os_c2, os_c3, os_c4 = st.columns(4)
                os_c1.metric("Round Robin Records", len(rr_logs))
                os_c2.metric(
                    "Average Waiting Time",
                    f"{rr_logs['waiting_time_seconds'].mean():.2f}",
                )
                os_c3.metric(
                    "Average Turnaround Time",
                    f"{rr_logs['turnaround_time_seconds'].mean():.2f}",
                )
                os_c4.metric(
                    "Average Response Time",
                    f"{rr_logs['response_time_seconds'].mean():.2f}",
                )

                rr_chart = rr_logs.copy()
                rr_chart["Process"] = (
                    rr_chart["process_name"].astype(str)
                    + " (#"
                    + rr_chart["process_id"].astype(str)
                    + ")"
                )
                rr_chart = rr_chart.melt(
                    id_vars=["Process"],
                    value_vars=[
                        "waiting_time_seconds",
                        "turnaround_time_seconds",
                        "response_time_seconds",
                    ],
                    var_name="Metric",
                    value_name="Time",
                )
                rr_chart["Metric"] = rr_chart["Metric"].replace(
                    {
                        "waiting_time_seconds": "Waiting Time",
                        "turnaround_time_seconds": "Turnaround Time",
                        "response_time_seconds": "Response Time",
                    }
                )
                os_fig = px.bar(
                    rr_chart,
                    x="Process",
                    y="Time",
                    color="Metric",
                    barmode="group",
                    title="Round Robin Scheduling Metrics by Process",
                )
                st.plotly_chart(os_fig, use_container_width=True)

                rr_display = rr_logs.drop(columns=["process_id"], errors="ignore").rename(
                    columns={
                        "process_name": "Process",
                        "scheduling_algorithm": "Algorithm",
                        "arrival_time": "Arrival Time",
                        "start_time": "First Start Time",
                        "completion_time": "Completion Time",
                        "waiting_time_seconds": "Waiting Time",
                        "turnaround_time_seconds": "Turnaround Time",
                        "response_time_seconds": "Response Time",
                        "cpu_usage": "CPU Usage",
                        "memory_usage_mb": "Memory Usage (MB)",
                        "status": "Status",
                    }
                )
                st.dataframe(rr_display, hide_index=True, use_container_width=True)
            else:
                st.info("No Round Robin simulation records found.")

            st.divider()
            st.subheader("OS Worker Process Demonstration")
            st.caption(
                "These records come from ProcessPoolExecutor workers, not the Round Robin "
                "simulation. Their durations and resource fields have different meanings."
            )
            if not worker_logs.empty:
                completed_workers = int(
                    (worker_logs["status"].astype(str).str.upper() == "COMPLETED").sum()
                )
                failed_workers = int(
                    (worker_logs["status"].astype(str).str.upper() == "FAILED").sum()
                )
                w1, w2, w3 = st.columns(3)
                w1.metric("Worker Jobs Logged", len(worker_logs))
                w2.metric("Completed Jobs", completed_workers)
                w3.metric("Failed Jobs", failed_workers)
                worker_display = worker_logs.drop(columns=["process_id"], errors="ignore").rename(
                    columns={
                        "process_name": "Worker",
                        "scheduling_algorithm": "Execution Method",
                        "arrival_time": "Submitted At",
                        "start_time": "Worker Start Time",
                        "completion_time": "Observed Completion Time",
                        "waiting_time_seconds": "Queue/Observed Wait (s)",
                        "turnaround_time_seconds": "Observed Duration (s)",
                        "response_time_seconds": "Response/Observed Wait (s)",
                        "cpu_usage": "CPU Usage",
                        "memory_usage_mb": "Memory Usage (MB)",
                        "status": "Status",
                    }
                )
                st.dataframe(worker_display, hide_index=True, use_container_width=True)
            else:
                st.info("No worker-process demonstration records found.")
        else:
            st.info("No OS process logs yet. Run the relevant OS demonstration modules first.")
    except Exception as os_error:
        st.warning("Could not load OS process logs.")
        st.caption(str(os_error))

    st.divider()
    st.header("System Resource Monitoring")
    st.caption(
        "Snapshots are collected when the resource-monitor script runs. This is historical "
        "monitoring, not a continuous live stream."
    )

    try:
        resource_logs = load_resource_logs()
        if not resource_logs.empty:
            latest = resource_logs.iloc[0]
            r1, r2, r3 = st.columns(3)
            r1.metric("System CPU Usage", f"{float(latest['cpu_percent']):.2f}%")
            r2.metric("System Memory Usage", f"{float(latest['memory_percent']):.2f}%")
            r3.metric("FedHealth Process RAM", f"{float(latest['process_memory_mb']):.2f} MB")

            chart_data = resource_logs.sort_values("recorded_at")
            fig = px.line(
                chart_data,
                x="recorded_at",
                y=["cpu_percent", "memory_percent"],
                markers=True,
                title="CPU and System Memory Usage Over Time",
                labels={
                    "recorded_at": "Time",
                    "value": "Usage (%)",
                    "variable": "Resource",
                },
            )
            fig.update_layout(
                xaxis_title="Time",
                yaxis_title="Usage (%)",
                yaxis=dict(range=[0, 100]),
                legend_title="Resource",
            )
            st.plotly_chart(fig, use_container_width=True)

            display_resources = resource_logs.rename(
                columns={
                    "snapshot_id": "Snapshot",
                    "cpu_percent": "CPU Usage (%)",
                    "memory_percent": "System Memory Usage (%)",
                    "system_memory_used_mb": "System Memory Used (MB)",
                    "process_memory_mb": "FedHealth Process RAM (MB)",
                    "available_memory_mb": "Available Memory (MB)",
                    "recorded_at": "Recorded At",
                }
            )
            st.dataframe(display_resources, hide_index=True, use_container_width=True)
        else:
            st.info("No resource snapshots found. Run `python -m os_layer.resource_monitor` first.")
    except Exception as resource_error:
        st.warning("Could not load resource monitoring data.")
        st.caption(str(resource_error))

    st.divider()
    st.caption(
        "FedHealth is an academic prototype. Model outputs are experimental and are not "
        "intended for clinical diagnosis. Round 4 is recorded as iterative FedAvg using "
        "mini-batch SGD; earlier rounds used parameter averaging. Full end-to-end "
        "integration and performance validation remain future work."
    )

except Exception as exc:
    st.error("Unable to load dashboard data.")
    st.exception(exc)
    st.info(
        "Check that PostgreSQL is running, database connection settings are correct, "
        "and the expected tables exist."
    )
