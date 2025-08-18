from __future__ import annotations

import os
import random
import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence, Tuple
from datetime import datetime

import bcrypt
import pandas as pd
import snowflake.connector


@dataclass
class Persona:
    name: str
    email_prefix: str
    state_pool: Sequence[str]
    race_pool: Sequence[str]
    gender_pool: Sequence[str]
    likes_selector: Callable[[pd.DataFrame], List[int]]
    dislikes_selector: Callable[[pd.DataFrame, List[int]], List[int]]
    sat_erw_range: Tuple[int, int]
    sat_math_range: Tuple[int, int]
    act_range: Tuple[int, int]
    users_to_create: int


RACES = [
    "American Indian or Alaska Native",
    "Asian",
    "Black or African American",
    "Hispanic/Latino",
    "Native Hawaiian or Other Pacific Islander",
    "White",
    "Two or more races",
    "Unknown",
    "Nonresident",
    "Other",
    "Prefer not to say",
]

STATES_NORTHEAST = [
    "Connecticut",
    "Maine",
    "Massachusetts",
    "New Hampshire",
    "Rhode Island",
    "Vermont",
    "New York",
    "New Jersey",
    "Pennsylvania",
]

STATES_SOUTHWEST_SOUTH = [
    "California",
    "Arizona",
    "Nevada",
    "New Mexico",
    "Texas",
    "Oklahoma",
    "Arkansas",
    "Louisiana",
    "Mississippi",
    "Alabama",
    "Georgia",
    "Florida",
    "South Carolina",
    "North Carolina",
    "Tennessee",
]

STATES_BIG_FOOTBALL = [
    "Texas",
    "Florida",
    "California",
    "Ohio",
    "Michigan",
    "Pennsylvania",
    "Georgia",
    "Alabama",
    "Wisconsin",
]


def sf_connect():
    insecure = str(os.environ.get("SNOWFLAKE_INSECURE", "")).lower() in {"1", "true", "yes"}
    if insecure:
        os.environ.setdefault("SF_OCSP_DISABLE", "true")
        os.environ.setdefault("SF_OCSP_RESPONSE_CACHE_SERVER_ENABLED", "false")
    return snowflake.connector.connect(
        account=os.environ.get("SNOWFLAKE_ACCOUNT", ""),
        user=os.environ.get("SNOWFLAKE_USER", ""),
        password=os.environ.get("SNOWFLAKE_PASSWORD", ""),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "DATA_LAKE"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC"),
        ocsp_fail_open=insecure or True,
        insecure_mode=insecure,
        client_session_keep_alive=True,
    )


def load_universities(conn) -> pd.DataFrame:
    cols = [
        "UNITID",
        "INSTITUTION_NAME",
        "STATE_ABBREVIATION",
        "PERCENT_ADMITTED_TOTAL",
        "ADMISSIONS_YIELD_TOTAL",
        "TUITION_AND_FEES_2023_24",
        "AVERAGE_NET_PRICE_STUDENTS_AWARDED_GRANT_OR_SCHOLARSHIP_AID_2022_23",
        "SAT_EVIDENCE_BASED_READING_AND_WRITING_75TH_PERCENTILE_SCORE",
        "SAT_MATH_75TH_PERCENTILE_SCORE",
        "DEGREE_OF_URBANIZATION_URBAN_CENTRIC_LOCALE",
    ]
    df = pd.read_sql(
        f"SELECT {', '.join(cols)} FROM DATA_LAKE.PUBLIC.UNIVERSITY_DATA",
        conn,
    )
    df["UNITID"] = pd.to_numeric(df["UNITID"], errors="coerce").astype("Int64")
    for c in [
        "PERCENT_ADMITTED_TOTAL",
        "ADMISSIONS_YIELD_TOTAL",
        "TUITION_AND_FEES_2023_24",
        "AVERAGE_NET_PRICE_STUDENTS_AWARDED_GRANT_OR_SCHOLARSHIP_AID_2022_23",
        "SAT_EVIDENCE_BASED_READING_AND_WRITING_75TH_PERCENTILE_SCORE",
        "SAT_MATH_75TH_PERCENTILE_SCORE",
    ]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["INSTITUTION_NAME"] = df["INSTITUTION_NAME"].astype(str)
    df["STATE_ABBREVIATION"] = df["STATE_ABBREVIATION"].astype(str)
    return df.dropna(subset=["UNITID"])  # keep valid unitids only


def top_n_unitids(df: pd.DataFrame, score: pd.Series, n: int) -> List[int]:
    s = score.fillna(-1e9)
    order = s.sort_values(ascending=False)
    return [int(u) for u in df.loc[order.index, "UNITID"].head(n).tolist()]


def bottom_n_unitids(df: pd.DataFrame, score: pd.Series, n: int) -> List[int]:
    s = score.fillna(1e9)
    order = s.sort_values(ascending=True)
    return [int(u) for u in df.loc[order.index, "UNITID"].head(n).tolist()]


def regex_mask(series: pd.Series, patterns: Sequence[str]) -> pd.Series:
    combined = "|".join([f"({p})" for p in patterns])
    return series.str.contains(combined, flags=re.IGNORECASE, regex=True, na=False)


def persona_selectors(df: pd.DataFrame) -> Dict[str, Tuple[Callable[[pd.DataFrame], List[int]], Callable[[pd.DataFrame, List[int]], List[int]]]]:
    # Curated name groups to better target well-known Top-200 schools
    NEAR_IVY_NAMES = [
        "Boston College", "Boston University", "Northeastern University", "Georgetown University",
        "Villanova", "Fordham University", "College of William", "Wake Forest University",
        "Tufts University", "University of Rochester", "Lehigh University", "Brandeis University",
        "Case Western Reserve University", "New York University",
    ]
    DUKE_ADJ_NAMES = [
        "Duke University", "Vanderbilt University", "Rice University", "Emory University",
        "Washington University in St. Louis", "University of Notre Dame", "Tulane University",
        "University of Virginia", "University of North Carolina at Chapel Hill",
    ]
    PARTY_NAMES = [
        "Arizona State University", "University of Arizona", "West Virginia University", "San Diego State University",
        "Pennsylvania State University", "University of Wisconsin-Madison", "Indiana University", "University of Iowa",
        "Ohio University", "Michigan State University", "University of Alabama", "University of Georgia",
        "Florida State University", "University of Florida", "University of South Carolina", "University of Mississippi",
        "Louisiana State University", "Auburn University", "Texas Tech University", "Syracuse University",
    ]
    SLAC_NAMES = [
        "Amherst College", "Williams College", "Bowdoin College", "Middlebury College", "Hamilton College",
        "Colby College", "Bates College", "Wesleyan University", "Haverford College", "Swarthmore College",
        "Pomona College", "Claremont McKenna College", "Harvey Mudd College", "Davidson College", "Vassar College",
        "Carleton College", "Grinnell College", "Macalester College", "Kenyon College", "Oberlin College",
    ]
    JESUIT_NAMES = [
        "Boston College", "Georgetown University", "Fordham University", "Loyola Marymount University",
        "Loyola University Chicago", "Loyola University Maryland", "Loyola University New Orleans",
        "Marquette University", "Saint Louis University", "Creighton University", "Santa Clara University",
        "Xavier University", "Gonzaga University",
    ]
    COOP_NAMES = [
        "Northeastern University", "Drexel University", "Rochester Institute of Technology", "University of Cincinnati",
        "Worcester Polytechnic Institute", "Kettering University", "Georgia Institute of Technology",
    ]
    HBCU_NAMES = [
        "Howard University", "Spelman College", "Morehouse College", "Florida A&M University", "Hampton University",
        "Xavier University of Louisiana", "North Carolina A&T State University", "Tuskegee University", "Jackson State University",
        "Prairie View A&M University", "Morgan State University", "Norfolk State University",
    ]
    WOMENS_NAMES = [
        "Wellesley College", "Smith College", "Barnard College", "Bryn Mawr College", "Mount Holyoke College",
        "Spelman College", "Scripps College",
    ]
    UC_NAMES = [
        "University of California, Berkeley", "University of California, Los Angeles", "University of California, San Diego",
        "University of California, Santa Barbara", "University of California, Irvine", "University of California, Davis",
        "University of California, Santa Cruz", "University of California, Riverside", "University of California, Merced",
    ]
    CSU_NAMES = [
        "California Polytechnic State University", "California State Polytechnic University, Pomona", "San Diego State University",
        "San Jose State University", "California State University, Long Beach", "California State University, Fullerton",
        "California State University, Northridge", "California State University, Sacramento", "California State University, Fresno",
    ]
    SUNY_CUNY_PATTERNS = ["SUNY", "CUNY", "State University of New York", "City University of New York",
                           "Binghamton University", "Stony Brook University", "University at Buffalo", "University at Albany",
                           "Baruch College", "Hunter College", "Queens College", "Brooklyn College", "City College of New York"]

    def pick_by_names(d: pd.DataFrame, names: Sequence[str], n: int) -> List[int]:
        if not names:
            return []
        pattern = "|".join([re.escape(x) for x in names])
        mask = d["INSTITUTION_NAME"].str.contains(pattern, case=False, regex=True, na=False)
        uid = d.loc[mask, "UNITID"].dropna().astype(int).tolist()
        random.shuffle(uid)
        return uid[: n]
    def ivy_likes(d: pd.DataFrame) -> List[int]:
        sat_sum = (
            d["SAT_EVIDENCE_BASED_READING_AND_WRITING_75TH_PERCENTILE_SCORE"].fillna(0)
            + d["SAT_MATH_75TH_PERCENTILE_SCORE"].fillna(0)
        )
        selectivity = -d["PERCENT_ADMITTED_TOTAL"].fillna(100)
        northeast = d["STATE_ABBREVIATION"].isin(STATES_NORTHEAST).astype(int) * 100
        score = sat_sum * 1.0 + selectivity * 5.0 + northeast
        return top_n_unitids(d, score, 80)

    def ivy_dislikes(d: pd.DataFrame, liked: List[int]) -> List[int]:
        sat_sum = (
            d["SAT_EVIDENCE_BASED_READING_AND_WRITING_75TH_PERCENTILE_SCORE"].fillna(0)
            + d["SAT_MATH_75TH_PERCENTILE_SCORE"].fillna(0)
        )
        selectivity = d["PERCENT_ADMITTED_TOTAL"].fillna(100)
        score = sat_sum * -1.0 + selectivity * 5.0
        pool = [u for u in bottom_n_unitids(d, score, 300) if int(u) not in set(liked)]
        return pool[:120]

    def jock_likes(d: pd.DataFrame) -> List[int]:
        name_hit = regex_mask(d["INSTITUTION_NAME"], ["State", "University of", "Tech"]).astype(int) * 50
        football_states = d["STATE_ABBREVIATION"].isin(STATES_BIG_FOOTBALL).astype(int) * 100
        admit = d["PERCENT_ADMITTED_TOTAL"].fillna(50)
        score = name_hit + football_states + (admit.clip(50, 95) - 50)
        return top_n_unitids(d, score, 120)

    def jock_dislikes(d: pd.DataFrame, liked: List[int]) -> List[int]:
        name_anti = regex_mask(d["INSTITUTION_NAME"], ["Conservatory", "Art", "Music", "Design"]).astype(int) * 100
        score = name_anti + (100 - d["PERCENT_ADMITTED_TOTAL"].fillna(50))
        pool = [u for u in top_n_unitids(d, score, 200) if int(u) not in set(liked)]
        return pool[:120]

    def artsy_likes(d: pd.DataFrame) -> List[int]:
        patterns = ["Art", "Music", "Design", "Conservatory", "Performing", "Visual"]
        score = regex_mask(d["INSTITUTION_NAME"], patterns).astype(int) * 200
        ca_ny = d["STATE_ABBREVIATION"].isin(["California", "New York"]).astype(int) * 50
        return top_n_unitids(d, score + ca_ny, 80)

    def artsy_dislikes(d: pd.DataFrame, liked: List[int]) -> List[int]:
        score = regex_mask(d["INSTITUTION_NAME"], ["Institute of Technology", "Polytechnic"]).astype(int) * 100
        pool = [u for u in top_n_unitids(d, score, 200) if int(u) not in set(liked)]
        return pool[:120]

    def middle_likes(d: pd.DataFrame) -> List[int]:
        sat_sum = (
            d["SAT_EVIDENCE_BASED_READING_AND_WRITING_75TH_PERCENTILE_SCORE"].fillna(500)
            + d["SAT_MATH_75TH_PERCENTILE_SCORE"].fillna(500)
        )
        sat_midness = -abs(sat_sum - 1200)
        admit_mid = -abs(d["PERCENT_ADMITTED_TOTAL"].fillna(60) - 60)
        cost_mid = -abs(d["TUITION_AND_FEES_2023_24"].fillna(20000) - 20000) / 1000
        score = sat_midness + admit_mid + cost_mid
        return top_n_unitids(d, score, 120)

    def middle_dislikes(d: pd.DataFrame, liked: List[int]) -> List[int]:
        sat_sum = (
            d["SAT_EVIDENCE_BASED_READING_AND_WRITING_75TH_PERCENTILE_SCORE"].fillna(0)
            + d["SAT_MATH_75TH_PERCENTILE_SCORE"].fillna(0)
        )
        extreme = (sat_sum > 1450).astype(int) * 100 + (sat_sum < 900).astype(int) * 100
        pool = [u for u in top_n_unitids(d, extreme, 200) if int(u) not in set(liked)]
        return pool[:120]

    def anti_north_likes(d: pd.DataFrame) -> List[int]:
        score = d["STATE_ABBREVIATION"].isin(STATES_SOUTHWEST_SOUTH).astype(int) * 100
        return top_n_unitids(d, score, 150)

    def anti_north_dislikes(d: pd.DataFrame, liked: List[int]) -> List[int]:
        score = d["STATE_ABBREVIATION"].isin(STATES_NORTHEAST).astype(int) * 100
        pool = [u for u in top_n_unitids(d, score, 300) if int(u) not in set(liked)]
        return pool[:150]

    def ca_lover_likes(d: pd.DataFrame) -> List[int]:
        score = (d["STATE_ABBREVIATION"] == "California").astype(int) * 200
        name_hit = regex_mask(d["INSTITUTION_NAME"], ["University of California", "State University"]).astype(int) * 50
        return top_n_unitids(d, score + name_hit, 120)

    def ca_lover_dislikes(d: pd.DataFrame, liked: List[int]) -> List[int]:
        score = (d["STATE_ABBREVIATION"] != "California").astype(int) * 20
        pool = [u for u in top_n_unitids(d, score, 400) if int(u) not in set(liked)]
        return pool[:150]

    def stem_likes(d: pd.DataFrame) -> List[int]:
        math = d["SAT_MATH_75TH_PERCENTILE_SCORE"].fillna(0)
        stem_name = regex_mask(d["INSTITUTION_NAME"], ["Tech", "Institute", "Polytechnic"]).astype(int) * 100
        score = math * 1.0 + stem_name
        return top_n_unitids(d, score, 120)

    def stem_dislikes(d: pd.DataFrame, liked: List[int]) -> List[int]:
        score = regex_mask(d["INSTITUTION_NAME"], ["Art", "Music", "Conservatory"]).astype(int) * 100
        pool = [u for u in top_n_unitids(d, score, 200) if int(u) not in set(liked)]
        return pool[:120]

    def cost_sensitive_likes(d: pd.DataFrame) -> List[int]:
        net = d["AVERAGE_NET_PRICE_STUDENTS_AWARDED_GRANT_OR_SCHOLARSHIP_AID_2022_23"].fillna(
            d["TUITION_AND_FEES_2023_24"].fillna(1e9)
        )
        score = -net
        return top_n_unitids(d, score, 150)

    def cost_sensitive_dislikes(d: pd.DataFrame, liked: List[int]) -> List[int]:
        net = d["AVERAGE_NET_PRICE_STUDENTS_AWARDED_GRANT_OR_SCHOLARSHIP_AID_2022_23"].fillna(
            d["TUITION_AND_FEES_2023_24"].fillna(1e9)
        )
        score = net
        pool = [u for u in top_n_unitids(d, score, 200) if int(u) not in set(liked)]
        return pool[:150]

    def urbanite_likes(d: pd.DataFrame) -> List[int]:
        urb = d["DEGREE_OF_URBANIZATION_URBAN_CENTRIC_LOCALE"].astype(str).str.contains("City", na=False).astype(int) * 100
        score = urb + d["ADMISSIONS_YIELD_TOTAL"].fillna(0) / 2
        return top_n_unitids(d, score, 120)

    def urbanite_dislikes(d: pd.DataFrame, liked: List[int]) -> List[int]:
        rural = ~d["DEGREE_OF_URBANIZATION_URBAN_CENTRIC_LOCALE"].astype(str).str.contains("City", na=False)
        score = rural.astype(int) * 100
        pool = [u for u in top_n_unitids(d, score, 200) if int(u) not in set(liked)]
        return pool[:120]

    def selective_likes(d: pd.DataFrame) -> List[int]:
        mask = d["PERCENT_ADMITTED_TOTAL"].fillna(100) < 30
        return d.loc[mask, "UNITID"].dropna().astype(int).tolist()

    def selective_dislikes(d: pd.DataFrame, liked: List[int]) -> List[int]:
        mask = d["PERCENT_ADMITTED_TOTAL"].fillna(0) > 75
        ids = d.loc[mask, "UNITID"].dropna().astype(int).tolist()
        liked_set = set(int(u) for u in liked)
        return [int(u) for u in ids if int(u) not in liked_set]

    return {
        "ivy": (ivy_likes, ivy_dislikes),
        "jock": (jock_likes, jock_dislikes),
        "artsy": (artsy_likes, artsy_dislikes),
        "middle": (middle_likes, middle_dislikes),
        "anti_north": (anti_north_likes, anti_north_dislikes),
        "ca_lover": (ca_lover_likes, ca_lover_dislikes),
        "stem": (stem_likes, stem_dislikes),
        "cost": (cost_sensitive_likes, cost_sensitive_dislikes),
        "urban": (urbanite_likes, urbanite_dislikes),
        "selective": (selective_likes, selective_dislikes),
        # New curated selectors
        "near_ivy": (
            lambda d: pick_by_names(d, NEAR_IVY_NAMES, 100),
            lambda d, liked: [u for u in pick_by_names(d, PARTY_NAMES, 200) if u not in set(liked)][:120],
        ),
        "duke_adj": (
            lambda d: pick_by_names(d, DUKE_ADJ_NAMES, 80),
            lambda d, liked: [u for u in pick_by_names(d, SLAC_NAMES, 200) if u not in set(liked)][:120],
        ),
        "party": (
            lambda d: pick_by_names(d, PARTY_NAMES, 150),
            lambda d, liked: [u for u in pick_by_names(d, SLAC_NAMES, 200) if u not in set(liked)][:120],
        ),
        "slac": (
            lambda d: pick_by_names(d, SLAC_NAMES, 120),
            lambda d, liked: [u for u in pick_by_names(d, PARTY_NAMES, 200) if u not in set(liked)][:120],
        ),
        "jesuit": (
            lambda d: pick_by_names(d, JESUIT_NAMES, 100),
            lambda d, liked: [u for u in pick_by_names(d, PARTY_NAMES, 200) if u not in set(liked)][:120],
        ),
        "coop": (
            lambda d: pick_by_names(d, COOP_NAMES, 100),
            lambda d, liked: [u for u in pick_by_names(d, SLAC_NAMES, 200) if u not in set(liked)][:120],
        ),
        "hbcu": (
            lambda d: pick_by_names(d, HBCU_NAMES, 100),
            lambda d, liked: [u for u in pick_by_names(d, PARTY_NAMES, 200) if u not in set(liked)][:120],
        ),
        "womens": (
            lambda d: pick_by_names(d, WOMENS_NAMES, 80),
            lambda d, liked: [u for u in pick_by_names(d, PARTY_NAMES, 200) if u not in set(liked)][:120],
        ),
        "uc_focus": (
            lambda d: pick_by_names(d, UC_NAMES, 120),
            lambda d, liked: [u for u in pick_by_names(d, CSU_NAMES, 200) if u not in set(liked)][:120],
        ),
        "suny_cuny": (
            lambda d: pick_by_names(d, SUNY_CUNY_PATTERNS, 150),
            lambda d, liked: [u for u in pick_by_names(d, PARTY_NAMES, 200) if u not in set(liked)][:120],
        ),
    }


def pick_scores(low: int, high: int) -> Tuple[int, int, int]:
    erw = random.randint(max(200, low // 2), min(800, high // 2))
    math = random.randint(max(200, low // 2), min(800, high // 2))
    act = random.randint(max(1, low // 40), min(36, high // 40))
    return erw, math, act


def ensure_user(conn, email: str, password_hash: bytes, gender: str | None, state: str | None, race: str | None, sat_erw: int | None, sat_math: int | None, act: int | None) -> str:
    with conn.cursor(snowflake.connector.DictCursor) as cur:  # type: ignore
        cur.execute(
            """
            MERGE INTO DATA_LAKE.PUBLIC.USERS t
            USING (
              SELECT %(email)s AS EMAIL
            ) s
            ON t.EMAIL = s.EMAIL
            WHEN NOT MATCHED THEN
              INSERT (EMAIL, PASSWORD_HASH, GENDER, STATE_ABBREVIATION, RACE_ETHNICITY, SAT_ERW, SAT_MATH, ACT_COMPOSITE)
              VALUES (%(email)s, %(password_hash)s, %(gender)s, %(state)s, %(race)s, %(sat_erw)s, %(sat_math)s, %(act)s)
            """,
            {
                "email": email,
                "password_hash": password_hash.decode("utf-8"),
                "gender": gender,
                "state": state,
                "race": race,
                "sat_erw": sat_erw,
                "sat_math": sat_math,
                "act": act,
            },
        )
        cur.execute("SELECT USER_ID FROM DATA_LAKE.PUBLIC.USERS WHERE EMAIL = %s", (email,))
        row = cur.fetchone()
        return row["USER_ID"]


def insert_swipes(conn, user_id: str, likes: Sequence[int], dislikes: Sequence[int]) -> None:
    like_vals = list({int(u) for u in likes})
    dislike_vals = list({int(u) for u in dislikes})
    with conn.cursor() as cur:
        for u in like_vals:
            cur.execute(
                """
                MERGE INTO DATA_LAKE.PUBLIC.USER_LIKES t
                USING (SELECT %s AS USER_ID, %s AS UNITID) s
                ON t.USER_ID = s.USER_ID AND t.UNITID = s.UNITID
                WHEN NOT MATCHED THEN INSERT (USER_ID, UNITID) VALUES (s.USER_ID, s.UNITID)
                """,
                (user_id, u),
            )
        for u in dislike_vals:
            cur.execute(
                """
                MERGE INTO DATA_LAKE.PUBLIC.USER_DISLIKES t
                USING (SELECT %s AS USER_ID, %s AS UNITID) s
                ON t.USER_ID = s.USER_ID AND t.UNITID = s.UNITID
                WHEN NOT MATCHED THEN INSERT (USER_ID, UNITID) VALUES (s.USER_ID, s.UNITID)
                """,
                (user_id, u),
            )


def purge_synthetic(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM DATA_LAKE.PUBLIC.USER_LIKES WHERE USER_ID IN (SELECT USER_ID FROM DATA_LAKE.PUBLIC.USERS WHERE EMAIL LIKE '_%@%')")
        cur.execute("DELETE FROM DATA_LAKE.PUBLIC.USER_DISLIKES WHERE USER_ID IN (SELECT USER_ID FROM DATA_LAKE.PUBLIC.USERS WHERE EMAIL LIKE '_%@%')")
        cur.execute("DELETE FROM DATA_LAKE.PUBLIC.USERS WHERE EMAIL LIKE '_%@%'")
        return cur.rowcount or 0


def main():
    random.seed(32)
    purge_before_create = False  # do not wipe previous synthetic users
    default_password = "Test1234!"
    password_hash = bcrypt.hashpw(default_password.encode("utf-8"), bcrypt.gensalt(rounds=12))

    conn = sf_connect()
    try:
        if purge_before_create:
            purge_synthetic(conn)

        df = load_universities(conn)
        sel = persona_selectors(df)

        personas: List[Persona] = [
            Persona(
                name="ivy_chaser",
                email_prefix="ivy",
                state_pool=STATES_NORTHEAST,
                race_pool=RACES,
                gender_pool=["Male", "Female"],
                likes_selector=sel["ivy"][0],
                dislikes_selector=sel["ivy"][1],
                sat_erw_range=(680, 780),
                sat_math_range=(700, 800),
                act_range=(33, 36),
                users_to_create=20,
            ),
            Persona(
                name="selective_acceptance",
                email_prefix="sel",
                state_pool=[],
                race_pool=RACES,
                gender_pool=["Male", "Female"],
                likes_selector=sel["selective"][0],
                dislikes_selector=sel["selective"][1],
                sat_erw_range=(650, 760),
                sat_math_range=(670, 800),
                act_range=(32, 36),
                users_to_create=20,
            ),
            Persona(
                name="jock",
                email_prefix="jock",
                state_pool=STATES_BIG_FOOTBALL,
                race_pool=RACES,
                gender_pool=["Male", "Female"],
                likes_selector=sel["jock"][0],
                dislikes_selector=sel["jock"][1],
                sat_erw_range=(520, 650),
                sat_math_range=(520, 680),
                act_range=(21, 28),
                users_to_create=10,
            ),
            Persona(
                name="artsy",
                email_prefix="art",
                state_pool=["California", "New York", "Massachusetts"],
                race_pool=RACES,
                gender_pool=["Male", "Female"],
                likes_selector=sel["artsy"][0],
                dislikes_selector=sel["artsy"][1],
                sat_erw_range=(580, 720),
                sat_math_range=(560, 700),
                act_range=(24, 31),
                users_to_create=2,
            ),
            Persona(
                name="middle_of_the_road",
                email_prefix="mid",
                state_pool=["Ohio", "Indiana", "Missouri", "Pennsylvania", "Illinois", "Colorado"],
                race_pool=RACES,
                gender_pool=["Male", "Female"],
                likes_selector=sel["middle"][0],
                dislikes_selector=sel["middle"][1],
                sat_erw_range=(540, 640),
                sat_math_range=(540, 660),
                act_range=(22, 28),
                users_to_create=10,
            ),
            Persona(
                name="anti_north",
                email_prefix="south",
                state_pool=STATES_SOUTHWEST_SOUTH,
                race_pool=RACES,
                gender_pool=["Male", "Female"],
                likes_selector=sel["anti_north"][0],
                dislikes_selector=sel["anti_north"][1],
                sat_erw_range=(520, 620),
                sat_math_range=(520, 640),
                act_range=(20, 26),
                users_to_create=8,
            ),
            Persona(
                name="california_lover",
                email_prefix="calove",
                state_pool=["California"],
                race_pool=RACES,
                gender_pool=["Male", "Female"],
                likes_selector=sel["ca_lover"][0],
                dislikes_selector=sel["ca_lover"][1],
                sat_erw_range=(560, 700),
                sat_math_range=(560, 720),
                act_range=(23, 31),
                users_to_create=0,
            ),
            Persona(
                name="stem_fan",
                email_prefix="stem",
                state_pool=["California", "Massachusetts", "New York", "Texas", "Georgia"],
                race_pool=RACES,
                gender_pool=["Male", "Female"],
                likes_selector=sel["stem"][0],
                dislikes_selector=sel["stem"][1],
                sat_erw_range=(600, 720),
                sat_math_range=(650, 800),
                act_range=(27, 34),
                users_to_create=8,
            ),
            Persona(
                name="cost_sensitive",
                email_prefix="cost",
                state_pool=["Florida", "Texas", "Ohio", "Georgia", "North Carolina", "Arizona", "Utah"],
                race_pool=RACES,
                gender_pool=["Male", "Female"],
                likes_selector=sel["cost"][0],
                dislikes_selector=sel["cost"][1],
                sat_erw_range=(520, 640),
                sat_math_range=(520, 660),
                act_range=(20, 28),
                users_to_create=2,
            ),
            Persona(
                name="urbanite",
                email_prefix="urban",
                state_pool=["New York", "California", "Illinois", "Pennsylvania", "Massachusetts", "Washington"],
                race_pool=RACES,
                gender_pool=["Male", "Female"],
                likes_selector=sel["urban"][0],
                dislikes_selector=sel["urban"][1],
                sat_erw_range=(560, 700),
                sat_math_range=(560, 720),
                act_range=(24, 32),
                users_to_create=12,
            ),
        ]

        idx = 0
        for i in range(10):
            for persona in personas:
                liked_pool = persona.likes_selector(df)
                disliked_pool_all = persona.dislikes_selector(df, liked_pool)

                for i in range(persona.users_to_create):
                    idx += 1
                    # Stable but non-overwriting email: include date suffix
                    date_tag = datetime.utcnow().strftime("%Y%m%d")
                    email = f"_{persona.email_prefix}{i+1}-{date_tag}@example.com"
                    gender = random.choice(persona.gender_pool)
                    state = random.choice(persona.state_pool) if persona.state_pool else None
                    race = random.choice(persona.race_pool)
                    sat_erw = random.randint(*persona.sat_erw_range)
                    sat_math = random.randint(*persona.sat_math_range)
                    act = random.randint(*persona.act_range)

                    user_id = ensure_user(
                        conn,
                        email=email,
                        password_hash=password_hash,
                        gender=gender,
                        state=state,
                        race=race,
                        sat_erw=sat_erw,
                        sat_math=sat_math,
                        act=act,
                    )

                    likes = random.sample(liked_pool, k=min(10, len(liked_pool)))
                    not_overlap = [u for u in disliked_pool_all if u not in set(likes)]
                    dislikes = random.sample(not_overlap, k=min(8, len(not_overlap)))

                    insert_swipes(conn, user_id, likes, dislikes)

            print(f"Created synthetic users: {idx}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

