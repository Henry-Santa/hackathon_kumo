from __future__ import annotations

import os
import pandas as pd
import snowflake.connector
import kumoai.experimental.rfm as rfm
from typing import List, Dict, Tuple, Optional
from .config import settings
from .cache_manager import graph_cache
import logging
import time

logger = logging.getLogger("uvicorn")


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
      SELECT UNITID, INSTITUTION_NAME, YEAR, CITY_LOCATION_OF_INSTITUTION, STATE_ABBREVIATION,
             ZIP_CODE, INSTITUTIONS_INTERNET_WEBSITE_ADDRESS, MEMBER_OF_NATIONAL_ATHLETIC_ASSOCIATION,
             MEMBER_OF_NATIONAL_COLLEGIATE_ATHLETIC_ASSOCIATION_NCAA, MEMBER_OF_NATIONAL_ASSOCIATION_OF_INTERCOLLEGIATE_ATHLETICS_NAIA,
             MEMBER_OF_NATIONAL_JUNIOR_COLLEGE_ATHLETIC_ASSOCIATION_NJCAA, MEMBER_OF_NATIONAL_SMALL_COLLEGE_ATHLETIC_ASSOCIATION_NSCAA,
             MEMBER_OF_NATIONAL_CHRISTIAN_COLLEGE_ATHLETIC_ASSOCIATION_NCCAA, MEMBER_OF_OTHER_NATIONAL_ATHLETIC_ASSOCIATION_NOT_LISTED_ABOVE,
             NCAA_NAIA_MEMBER_FOR_FOOTBALL, NCAA_NAIA_CONFERENCE_NUMBER_FOOTBALL, NCAA_NAIA_MEMBER_FOR_BASKETBALL,
             NCAA_NAIA_CONFERENCE_NUMBER_BASKETBALL, NCAA_NAIA_MEMBER_FOR_BASEBALL, NCAA_NAIA_CONFERENCE_NUMBER_BASEBALL,
             NCAA_NAIA_MEMBER_FOR_CROSS_COUNTRY_TRACK, NCAA_NAIA_CONFERENCE_NUMBER_CROSS_COUNTRY_TRACK,
             PERCENT_ADMITTED_TOTAL, PERCENT_ADMITTED_MEN, PERCENT_ADMITTED_WOMEN, ADMISSIONS_YIELD_TOTAL,
             ADMISSIONS_YIELD_MEN, ADMISSIONS_YIELD_WOMEN, TUITION_AND_FEES_2023_24,
             TOTAL_PRICE_FOR_IN_STATE_STUDENTS_LIVING_ON_CAMPUS_2023_24, TOTAL_PRICE_FOR_OUT_OF_STATE_STUDENTS_LIVING_ON_CAMPUS_2023_24,
             INSTITUTION_SIZE_CATEGORY, LEVEL_OF_INSTITUTION, CONTROL_OF_INSTITUTION, DEGREE_OF_URBANIZATION_URBAN_CENTRIC_LOCALE,
             PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_AMERICAN_INDIAN_OR_ALASKA_NATIVE, PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_ASIAN,
             PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_BLACK_OR_AFRICAN_AMERICAN, PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_HISPANIC_LATINO,
             PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_NATIVE_HAWAIIAN_OR_OTHER_PACIFIC_ISLANDER, PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_WHITE,
             PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_TWO_OR_MORE_RACES, PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_RACE_ETHNICITY_UNKNOWN,
             NONRESIDENT, PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_ASIAN_NATIVE_HAWAIIAN_PACIFIC_ISLANDER,
             PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_WOMEN, FULL_TIME_RETENTION_RATE_2023, PART_TIME_RETENTION_RATE_2023,
             STUDENT_TO_FACULTY_RATIO, ASSOCIATES_DEGREE, BACHELORS_DEGREE, GRADUATION_RATE_TOTAL_COHORT,
             PERCENT_OF_FULL_TIME_FIRST_TIME_UNDERGRADUATES_AWARDED_ANY_FINANCIAL_AID, AVERAGE_AMOUNT_OF_FEDERAL_STATE_LOCAL_OR_INSTITUTIONAL_GRANT_AID_AWARDED,
             AVERAGE_NET_PRICE_STUDENTS_AWARDED_GRANT_OR_SCHOLARSHIP_AID_2022_23, PHYSICAL_BOOKS_AS_A_PERCENT_OF_THE_TOTAL_LIBRARY_COLLECTION,
             PHYSICAL_MEDIA_AS_A_PERCENT_OF_THE_TOTAL_LIBRARY_COLLECTION, PHYSICAL_SERIALS_AS_A_PERCENT_OF_THE_TOTAL_LIBRARY_COLLECTION,
             DIGITAL_ELECTRONIC_BOOKS_AS_A_PERCENT_OF_THE_TOTAL_LIBRARY_COLLECTION, DATABASES_AS_A_PERCENT_OF_THE_TOTAL_LIBRARY_COLLECTION,
             DIGITAL_ELECTRONIC_MEDIA_AS_A_PERCENT_OF_THE_TOTAL_LIBRARY_COLLECTION, DIGITAL_ELECTRONIC_SERIALS_AS_A_PERCENT_OF_THE_TOTAL_LIBRARY_COLLECTION,
             TOTAL_LIBRARY_FTE_STAFF, APPLICANTS_TOTAL, APPLICANTS_MEN, APPLICANTS_WOMEN,
             PERCENT_OF_FIRST_TIME_DEGREE_CERTIFICATE_SEEKING_STUDENTS_SUBMITTING_SAT_SCORES, PERCENT_OF_FIRST_TIME_DEGREE_CERTIFICATE_SEEKING_STUDENTS_SUBMITTING_ACT_SCORES,
             SAT_EVIDENCE_BASED_READING_AND_WRITING_25TH_PERCENTILE_SCORE, SAT_EVIDENCE_BASED_READING_AND_WRITING_50TH_PERCENTILE_SCORE,
             SAT_EVIDENCE_BASED_READING_AND_WRITING_75TH_PERCENTILE_SCORE, SAT_MATH_25TH_PERCENTILE_SCORE, SAT_MATH_50TH_PERCENTILE_SCORE,
             SAT_MATH_75TH_PERCENTILE_SCORE, ACT_COMPOSITE_25TH_PERCENTILE_SCORE, ACT_COMPOSITE_50TH_PERCENTILE_SCORE,
             ACT_COMPOSITE_75TH_PERCENTILE_SCORE, ZIP_CODE_ZIP5, REGION
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


def _build_graph(force_refresh: bool = False, cache_key: str = "default") -> Tuple[any, any]:
    # Try to get from cache first
    if not force_refresh:
        graph, model = graph_cache.get(cache_key)
        if graph is not None and model is not None:
            return graph, model
    
    logger.info(f"Building graph for cache_key={cache_key}, force_refresh={force_refresh}")
    start_time = time.time()
    
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
    
    # Text fields
    for col in ["INSTITUTION_NAME", "CITY_LOCATION_OF_INSTITUTION", "INSTITUTIONS_INTERNET_WEBSITE_ADDRESS"]:
        if col in universities.columns:
            universities[col].stype = "text"
    
    # Categorical fields
    for col in ["STATE_ABBREVIATION", "ZIP_CODE", "ZIP_CODE_ZIP5", "REGION", "INSTITUTION_SIZE_CATEGORY", 
                "LEVEL_OF_INSTITUTION", "CONTROL_OF_INSTITUTION", "DEGREE_OF_URBANIZATION_URBAN_CENTRIC_LOCALE",
                "MEMBER_OF_NATIONAL_ATHLETIC_ASSOCIATION", "MEMBER_OF_NATIONAL_COLLEGIATE_ATHLETIC_ASSOCIATION_NCAA",
                "MEMBER_OF_NATIONAL_ASSOCIATION_OF_INTERCOLLEGIATE_ATHLETICS_NAIA", "MEMBER_OF_NATIONAL_JUNIOR_COLLEGE_ATHLETIC_ASSOCIATION_NJCAA",
                "MEMBER_OF_NATIONAL_SMALL_COLLEGE_ATHLETIC_ASSOCIATION_NSCAA", "MEMBER_OF_NATIONAL_CHRISTIAN_COLLEGE_ATHLETIC_ASSOCIATION_NCCAA",
                "MEMBER_OF_OTHER_NATIONAL_ATHLETIC_ASSOCIATION_NOT_LISTED_ABOVE", "NCAA_NAIA_MEMBER_FOR_FOOTBALL",
                "NCAA_NAIA_MEMBER_FOR_BASKETBALL", "NCAA_NAIA_MEMBER_FOR_BASEBALL", "NCAA_NAIA_MEMBER_FOR_CROSS_COUNTRY_TRACK"]:
        if col in universities.columns:
            universities[col].stype = "categorical"
    
    # Numerical fields
    for col in ["YEAR", "PERCENT_ADMITTED_TOTAL", "PERCENT_ADMITTED_MEN", "PERCENT_ADMITTED_WOMEN", "ADMISSIONS_YIELD_TOTAL",
                "ADMISSIONS_YIELD_MEN", "ADMISSIONS_YIELD_WOMEN", "TUITION_AND_FEES_2023_24", 
                "TOTAL_PRICE_FOR_IN_STATE_STUDENTS_LIVING_ON_CAMPUS_2023_24", "TOTAL_PRICE_FOR_OUT_OF_STATE_STUDENTS_LIVING_ON_CAMPUS_2023_24",
                "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_AMERICAN_INDIAN_OR_ALASKA_NATIVE", "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_ASIAN",
                "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_BLACK_OR_AFRICAN_AMERICAN", "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_HISPANIC_LATINO",
                "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_NATIVE_HAWAIIAN_OR_OTHER_PACIFIC_ISLANDER", "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_WHITE",
                "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_TWO_OR_MORE_RACES", "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_RACE_ETHNICITY_UNKNOWN",
                "NONRESIDENT", "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_ASIAN_NATIVE_HAWAIIAN_PACIFIC_ISLANDER",
                "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_WOMEN", "FULL_TIME_RETENTION_RATE_2023", "PART_TIME_RETENTION_RATE_2023",
                "STUDENT_TO_FACULTY_RATIO", "ASSOCIATES_DEGREE", "BACHELORS_DEGREE", "GRADUATION_RATE_TOTAL_COHORT",
                "PERCENT_OF_FULL_TIME_FIRST_TIME_UNDERGRADUATES_AWARDED_ANY_FINANCIAL_AID", "AVERAGE_AMOUNT_OF_FEDERAL_STATE_LOCAL_OR_INSTITUTIONAL_GRANT_AID_AWARDED",
                "AVERAGE_NET_PRICE_STUDENTS_AWARDED_GRANT_OR_SCHOLARSHIP_AID_2022_23", "PHYSICAL_BOOKS_AS_A_PERCENT_OF_THE_TOTAL_LIBRARY_COLLECTION",
                "PHYSICAL_MEDIA_AS_A_PERCENT_OF_THE_TOTAL_LIBRARY_COLLECTION", "PHYSICAL_SERIALS_AS_A_PERCENT_OF_THE_TOTAL_LIBRARY_COLLECTION",
                "DIGITAL_ELECTRONIC_BOOKS_AS_A_PERCENT_OF_THE_TOTAL_LIBRARY_COLLECTION", "DATABASES_AS_A_PERCENT_OF_THE_TOTAL_LIBRARY_COLLECTION",
                "DIGITAL_ELECTRONIC_MEDIA_AS_A_PERCENT_OF_THE_TOTAL_LIBRARY_COLLECTION", "DIGITAL_ELECTRONIC_SERIALS_AS_A_PERCENT_OF_THE_TOTAL_LIBRARY_COLLECTION",
                "TOTAL_LIBRARY_FTE_STAFF", "APPLICANTS_TOTAL", "APPLICANTS_MEN", "APPLICANTS_WOMEN",
                "PERCENT_OF_FIRST_TIME_DEGREE_CERTIFICATE_SEEKING_STUDENTS_SUBMITTING_SAT_SCORES", "PERCENT_OF_FIRST_TIME_DEGREE_CERTIFICATE_SEEKING_STUDENTS_SUBMITTING_ACT_SCORES",
                "SAT_EVIDENCE_BASED_READING_AND_WRITING_25TH_PERCENTILE_SCORE", "SAT_EVIDENCE_BASED_READING_AND_WRITING_50TH_PERCENTILE_SCORE",
                "SAT_EVIDENCE_BASED_READING_AND_WRITING_75TH_PERCENTILE_SCORE", "SAT_MATH_25TH_PERCENTILE_SCORE", "SAT_MATH_50TH_PERCENTILE_SCORE",
                "SAT_MATH_75TH_PERCENTILE_SCORE", "ACT_COMPOSITE_25TH_PERCENTILE_SCORE", "ACT_COMPOSITE_50TH_PERCENTILE_SCORE",
                "ACT_COMPOSITE_75TH_PERCENTILE_SCORE", "NCAA_NAIA_CONFERENCE_NUMBER_FOOTBALL", "NCAA_NAIA_CONFERENCE_NUMBER_BASKETBALL",
                "NCAA_NAIA_CONFERENCE_NUMBER_BASEBALL", "NCAA_NAIA_CONFERENCE_NUMBER_CROSS_COUNTRY_TRACK"]:
        if col in universities.columns:
            universities[col].stype = "numerical"

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
    
    # Cache the graph and model
    graph_cache.set(cache_key, graph, model)
    
    logger.info(f"Graph built and cached in {time.time() - start_time:.2f}s")
    return graph, model


def invalidate_cache(user_id: Optional[str] = None) -> None:
    """Invalidate the graph cache, optionally for a specific user."""
    if user_id:
        graph_cache.invalidate_user(user_id)
    else:
        graph_cache.invalidate()
    logger.info(f"Cache invalidated for user={user_id or 'all'}")


def recommend_top_k(user_id: str, top_k: int = 10, horizon_days: int = 180, force_refresh: bool = False) -> List[Dict]:
    # Use smart caching instead of always rebuilding
    cache_key = "default"  # Could be user-specific if needed
    _, model = _build_graph(force_refresh=force_refresh, cache_key=cache_key)
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
    df = model.predict(query, run_mode='normal', num_hops=6)
    out: List[Dict] = []
    
    # Fetch user's disliked unitids and filter them out
    try:
        with _sf_conn() as conn:
            disliked_df = pd.read_sql(
                "SELECT UNITID FROM DATA_LAKE.PUBLIC.USER_DISLIKES WHERE USER_ID = %(u)s",
                conn,
                params={"u": user_id},
            )
            disliked_set = set(pd.to_numeric(disliked_df.get("UNITID"), errors="coerce").dropna().astype(int).tolist())
    except Exception as e:
        logger.warning(f"Failed to fetch dislikes for user {user_id}: {e}")
        disliked_set = set()

    for _, row in df.iterrows():
        try:
            unitid_val = int(row["CLASS"])
            if unitid_val in disliked_set:
                continue
            out.append({"unitid": unitid_val, "score": float(row.get("SCORE", 0.0))})
        except Exception as e:
            logger.warning(f"Failed to process prediction row: {e}")
            continue
    
    logger.info(f"Generated {len(out)} recommendations for user {user_id}")
    return out


