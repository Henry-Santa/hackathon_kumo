from __future__ import annotations

import os
import pandas as pd
import snowflake.connector
import kumoai.experimental.rfm as rfm
from typing import List, Dict
from .config import settings


def _sf_conn():
    # Hardened workaround for corp networks: disable OCSP fully when snowflake_insecure
    if bool(getattr(settings, "snowflake_insecure", False)):
        os.environ.setdefault("SF_OCSP_DISABLE", "true")
        os.environ.setdefault("SF_OCSP_RESPONSE_CACHE_SERVER_ENABLED", "false")
    return snowflake.connector.connect(
        account=os.environ.get("SNOWFLAKE_ACCOUNT", ""),
        user=os.environ.get("SNOWFLAKE_USER", ""),
        password=os.environ.get("SNOWFLAKE_PASSWORD", ""),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "DATA_LAKE"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC"),
        # Relax TLS/OCSP if requested (useful on restricted networks)
        ocsp_fail_open=bool(getattr(settings, "snowflake_insecure", False)),
        insecure_mode=bool(getattr(settings, "snowflake_insecure", False)),
    )


def _load_frames():
    q_users = """
      SELECT USER_ID, GENDER, STATE_ABBREVIATION, RACE_ETHNICITY,
             SAT_ERW, SAT_MATH, ACT_COMPOSITE
      FROM DATA_LAKE.PUBLIC.USERS
    """
    q_unis = """
      SELECT UNITID, INSTITUTION_NAME, STATE_ABBREVIATION,
             PERCENT_ADMITTED_TOTAL, TUITION_AND_FEES_2023_24
      FROM DATA_LAKE.PUBLIC.UNIVERSITY_DATA
    """
    q_likes = """
      SELECT USER_ID, UNITID, CREATED_AT
      FROM DATA_LAKE.PUBLIC.USER_LIKES
    """
    q_dislikes = """
      SELECT USER_ID, UNITID, CREATED_AT
      FROM DATA_LAKE.PUBLIC.USER_DISLIKES
    """
    with _sf_conn() as conn:
        users_df = pd.read_sql(q_users, conn)
        unis_df  = pd.read_sql(q_unis, conn)
        likes_df = pd.read_sql(q_likes, conn)
        dislikes_df = pd.read_sql(q_dislikes, conn)

    users_df["USER_ID"] = users_df["USER_ID"].astype("string")
    unis_df["UNITID"]   = pd.to_numeric(unis_df["UNITID"], errors="coerce").astype("Int64")

    for df in (likes_df, dislikes_df):
        df["USER_ID"] = df["USER_ID"].astype("string")
        df["UNITID"]  = pd.to_numeric(df["UNITID"], errors="coerce").astype("Int64")
        df["CREATED_AT"] = pd.to_datetime(df.get("CREATED_AT"), errors="coerce")

    # Clean
    users_df = users_df.dropna(subset=["USER_ID"]).drop_duplicates("USER_ID")
    unis_df  = unis_df.dropna(subset=["UNITID"]).drop_duplicates("UNITID")
    likes_df = likes_df.dropna(subset=["USER_ID", "UNITID"]).reset_index(drop=True)
    dislikes_df = dislikes_df.dropna(subset=["USER_ID", "UNITID"]).reset_index(drop=True)

    # Synthesize TS if needed (short horizon)
    base_time = pd.Timestamp.utcnow()
    def ensure_ts(df: pd.DataFrame) -> pd.DataFrame:
        ts = df["CREATED_AT"]
        need = ts.isna().all() or ts.nunique() <= 1
        if not need:
            try:
                need = (base_time - ts.min()) < pd.Timedelta(days=10)
            except Exception:
                need = True
        if need:
            start_time = base_time - pd.Timedelta(days=10)
            df["TS"] = pd.date_range(start=start_time, end=base_time, periods=len(df))
        else:
            df["TS"] = pd.to_datetime(ts, errors="coerce")
        return df

    likes_df = ensure_ts(likes_df)
    dislikes_df = ensure_ts(dislikes_df)

    # Keep only edges with known UNITIDs
    known_unis = set(unis_df["UNITID"].dropna().astype("Int64").tolist())
    likes_df = likes_df[likes_df["UNITID"].isin(known_unis)]
    dislikes_df = dislikes_df[dislikes_df["UNITID"].isin(known_unis)]
    return users_df, unis_df, likes_df, dislikes_df


_GRAPH = None
_MODEL = None
_INIT = False


def _ensure_init():
    global _INIT
    if _INIT:
        return
    api_key = os.environ.get("KUMO_API_KEY") or os.environ.get("KUMO_KEY")
    if api_key and "kumoai.cloud" in api_key:
        api_key = api_key.split(".kumoai.cloud")[0]
    rfm.init(api_key=api_key)
    _INIT = True


def _build_graph():
    global _GRAPH, _MODEL
    if _GRAPH is not None and _MODEL is not None:
        return _GRAPH, _MODEL

    _ensure_init()
    users_df, unis_df, likes_df, dislikes_df = _load_frames()

    users = rfm.LocalTable(users_df, name="users", primary_key="USER_ID")
    users["USER_ID"].stype = "ID"
    for col in ["GENDER", "STATE_ABBREVIATION", "RACE_ETHNICITY"]:
        if col in users.columns:
            users[col].stype = "categorical"
    for col in ["SAT_ERW", "SAT_MATH", "ACT_COMPOSITE"]:
        if col in users.columns:
            users[col].stype = "numerical"

    universities = rfm.LocalTable(unis_df, name="universities", primary_key="UNITID")
    universities["UNITID"].stype = "ID"
    if "INSTITUTION_NAME" in universities.columns:
        universities["INSTITUTION_NAME"].stype = "text"
    if "STATE_ABBREVIATION" in universities.columns:
        universities["STATE_ABBREVIATION"].stype = "categorical"

    # RFM mode with separate likes/dislikes tables
    likes = rfm.LocalTable(likes_df, name="likes", time_column="TS")
    likes["USER_ID"].stype = "ID"
    likes["UNITID"].stype  = "ID"

    dislikes = rfm.LocalTable(dislikes_df, name="dislikes", time_column="TS")
    dislikes["USER_ID"].stype = "ID"
    dislikes["UNITID"].stype  = "ID"

    graph = rfm.LocalGraph(tables=[users, universities, likes, dislikes])
    graph.link(src_table="likes", fkey="USER_ID", dst_table="users")
    graph.link(src_table="likes", fkey="UNITID", dst_table="universities")
    graph.link(src_table="dislikes", fkey="USER_ID", dst_table="users")
    graph.link(src_table="dislikes", fkey="UNITID", dst_table="universities")
    graph.validate()

    model = rfm.KumoRFM(graph)
    _GRAPH, _MODEL = graph, model
    return graph, model


def recommend_top_k(user_id: str, top_k: int = 10, horizon_days: int = 180) -> List[Dict]:
    _, model = _build_graph()
    # Foundation model limit is 20
    k = max(1, min(int(top_k), 20))
    uid = (user_id or "").replace("'", "''")
    # Temporal link prediction using likes as positives
    horizon_days = max(1, min(horizon_days, 7))
    query = (
        f"PREDICT LIST_DISTINCT(likes.UNITID, 0, {horizon_days}, days) "
        f"RANK TOP {k} "
        f"FOR users.USER_ID = '{uid}'"
    )
    df = model.predict(query, run_mode='normal')
    out: List[Dict] = []
    print(df)
    # Fetch user's disliked unitids and filter them out
    try:
        with _sf_conn() as conn:
            disliked_df = pd.read_sql(
                "SELECT UNITID FROM DATA_LAKE.PUBLIC.USER_DISLIKES WHERE USER_ID = %(u)s",
                conn,
                params={"u": user_id},
            )
            disliked_set = set(pd.to_numeric(disliked_df.get("UNITID"), errors="coerce").dropna().astype(int).tolist())
    except Exception:
        disliked_set = set()

    for _, row in df.iterrows():
        try:
            unitid_val = int(row["CLASS"])
            if unitid_val in disliked_set:
                continue
            out.append({"unitid": unitid_val, "score": float(row.get("SCORE", 0.0))})
        except Exception:
            continue
    print(out)
    return out


