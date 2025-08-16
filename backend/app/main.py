from __future__ import annotations

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from .db import fetch_one, execute, fetch_all
from .security import hash_password, verify_password, issue_jwt, decode_jwt
from enum import Enum
from .estimators import (
    estimate_act_from_sat_total,
    estimate_sat_total_from_act,
    estimate_sat_parts_from_total,
)
from .config import settings
import logging
from .images import (
    fetch_wikidata_images,
    commons_file_url,
    fetch_images_for_unitid,
    fetch_top_images_for_unitid,
)
from .rfm_reco import recommend_top_k, invalidate_cache
from .db_optimizer import BatchedQueries
from typing import Dict, Tuple, List, Optional, Union
import anyio
import asyncio
import os


app = FastAPI(title="College Matcher API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def log_startup_config():
    logger = logging.getLogger("uvicorn")
    logger.info(
        "Snowflake config (sanitized): account=%s, user=%s, warehouse=%s, database=%s, schema=%s",
        settings.snowflake_account,
        settings.snowflake_user,
        settings.snowflake_warehouse,
        settings.snowflake_database,
        settings.snowflake_schema,
    )
    logger.info(
        "JWT config (sanitized): iss=%s, aud=%s, secret_len=%s",
        settings.jwt_iss,
        settings.jwt_aud,
        len(settings.jwt_secret) if settings.jwt_secret else 0,
    )
    logger.info(
        "Kumo API key configured: %s",
        "yes" if getattr(settings, "kumo_api_key", None) else "no",
    )
    


class RaceEthnicity(str, Enum):
    AMERICAN_INDIAN_OR_ALASKA_NATIVE = "American Indian or Alaska Native"
    ASIAN = "Asian"
    BLACK_OR_AFRICAN_AMERICAN = "Black or African American"
    HISPANIC_LATINO = "Hispanic/Latino"
    NATIVE_HAWAIIAN_OR_OTHER_PACIFIC_ISLANDER = "Native Hawaiian or Other Pacific Islander"
    WHITE = "White"
    TWO_OR_MORE_RACES = "Two or more races"
    UNKNOWN = "Unknown"
    NONRESIDENT = "Nonresident"
    OTHER = "Other"
    PREFER_NOT_TO_SAY = "Prefer not to say"


class StateFullName(str, Enum):
    ALABAMA = "Alabama"
    ALASKA = "Alaska"
    ARIZONA = "Arizona"
    ARKANSAS = "Arkansas"
    CALIFORNIA = "California"
    COLORADO = "Colorado"
    CONNECTICUT = "Connecticut"
    DELAWARE = "Delaware"
    DISTRICT_OF_COLUMBIA = "District of Columbia"
    FLORIDA = "Florida"
    GEORGIA = "Georgia"
    HAWAII = "Hawaii"
    IDAHO = "Idaho"
    ILLINOIS = "Illinois"
    INDIANA = "Indiana"
    IOWA = "Iowa"
    KANSAS = "Kansas"
    KENTUCKY = "Kentucky"
    LOUISIANA = "Louisiana"
    MAINE = "Maine"
    MARYLAND = "Maryland"
    MASSACHUSETTS = "Massachusetts"
    MICHIGAN = "Michigan"
    MINNESOTA = "Minnesota"
    MISSISSIPPI = "Mississippi"
    MISSOURI = "Missouri"
    MONTANA = "Montana"
    NEBRASKA = "Nebraska"
    NEVADA = "Nevada"
    NEW_HAMPSHIRE = "New Hampshire"
    NEW_JERSEY = "New Jersey"
    NEW_MEXICO = "New Mexico"
    NEW_YORK = "New York"
    NORTH_CAROLINA = "North Carolina"
    NORTH_DAKOTA = "North Dakota"
    OHIO = "Ohio"
    OKLAHOMA = "Oklahoma"
    OREGON = "Oregon"
    PENNSYLVANIA = "Pennsylvania"
    RHODE_ISLAND = "Rhode Island"
    SOUTH_CAROLINA = "South Carolina"
    SOUTH_DAKOTA = "South Dakota"
    TENNESSEE = "Tennessee"
    TEXAS = "Texas"
    UTAH = "Utah"
    VERMONT = "Vermont"
    VIRGINIA = "Virginia"
    WASHINGTON = "Washington"
    WEST_VIRGINIA = "West Virginia"
    WISCONSIN = "Wisconsin"
    WYOMING = "Wyoming"
    AMERICAN_SAMOA = "American Samoa"
    GUAM = "Guam"
    NORTHERN_MARIANA_ISLANDS = "Northern Mariana Islands"
    PUERTO_RICO = "Puerto Rico"
    U_S_VIRGIN_ISLANDS = "U.S. Virgin Islands"


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    gender: Optional[str] = None
    state_abbreviation: Optional[StateFullName] = None
    race_ethnicity: Optional[RaceEthnicity] = None
    sat_erw: Optional[int] = None
    sat_math: Optional[int] = None
    act_composite: Optional[int] = None


class AuthResponse(BaseModel):
    token: str
    user_id: str


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


@app.post("/auth/signup", response_model=AuthResponse)
def signup(req: SignUpRequest):
    existing = fetch_one(
        "SELECT USER_ID FROM DATA_LAKE.PUBLIC.USERS WHERE EMAIL = %(email)s",
        {"email": str(req.email)},
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email already in use")

    password_hash = hash_password(req.password)
    # Estimate missing test scores so DB is consistently populated
    sat_erw_in = req.sat_erw
    sat_math_in = req.sat_math
    act_in = req.act_composite

    sat_total: Optional[int] = None
    if sat_erw_in is not None and sat_math_in is not None:
        sat_total = int(sat_erw_in) + int(sat_math_in)
    elif act_in is not None:
        sat_total = estimate_sat_total_from_act(int(act_in))

    if sat_total is not None:
        est_erw, est_math = estimate_sat_parts_from_total(sat_total, sat_erw_in, sat_math_in)
        est_act = act_in if act_in is not None else estimate_act_from_sat_total(sat_total)
    else:
        est_erw, est_math, est_act = sat_erw_in, sat_math_in, act_in
    # Insert row and fetch generated USER_ID
    execute(
        """
        INSERT INTO DATA_LAKE.PUBLIC.USERS (
            EMAIL, PASSWORD_HASH, GENDER, STATE_ABBREVIATION, RACE_ETHNICITY,
            SAT_ERW, SAT_MATH, ACT_COMPOSITE
        ) VALUES (
            %(email)s, %(password_hash)s, %(gender)s, %(state)s, %(race)s, %(sat_erw)s, %(sat_math)s, %(act)s
        )
        """,
        {
            "email": str(req.email),
            "password_hash": password_hash,
            "gender": req.gender,
            "state": (req.state_abbreviation.value if req.state_abbreviation is not None else None),
            "race": (req.race_ethnicity.value if req.race_ethnicity is not None else None),
            "sat_erw": est_erw,
            "sat_math": est_math,
            "act": est_act,
        },
    )
    user = fetch_one(
        "SELECT USER_ID FROM DATA_LAKE.PUBLIC.USERS WHERE EMAIL = %(email)s",
        {"email": str(req.email)},
    )
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user")

    token = issue_jwt(user["USER_ID"], req.email)
    return {"token": token, "user_id": user["USER_ID"]}


@app.post("/auth/signin", response_model=AuthResponse)
def signin(req: SignInRequest):
    row = fetch_one(
        "SELECT USER_ID, PASSWORD_HASH FROM DATA_LAKE.PUBLIC.USERS WHERE EMAIL = %(email)s",
        {"email": str(req.email)},
    )
    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(req.password, row["PASSWORD_HASH"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = issue_jwt(row["USER_ID"], req.email)
    return {"token": token, "user_id": row["USER_ID"]}


def require_auth(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload["sub"]


class SwipeRequest(BaseModel):
    unitid: int


@app.post("/likes")
def like(req: SwipeRequest, user_id: str = Depends(require_auth)):
    # Upsert-like behavior: ensure dislike removed, insert like
    execute(
        "DELETE FROM DATA_LAKE.PUBLIC.USER_DISLIKES WHERE USER_ID = %(user_id)s AND UNITID = %(unitid)s",
        {"user_id": user_id, "unitid": req.unitid},
    )
    execute(
        """
        MERGE INTO DATA_LAKE.PUBLIC.USER_LIKES t
        USING (
          SELECT %(user_id)s AS USER_ID, %(unitid)s AS UNITID
        ) s
        ON t.USER_ID = s.USER_ID AND t.UNITID = s.UNITID
        WHEN NOT MATCHED THEN
          INSERT (USER_ID, UNITID) VALUES (s.USER_ID, s.UNITID)
        """,
        {"user_id": user_id, "unitid": req.unitid},
    )
    return {"status": "ok"}


@app.post("/dislikes")
def dislike(req: SwipeRequest, user_id: str = Depends(require_auth)):
    execute(
        "DELETE FROM DATA_LAKE.PUBLIC.USER_LIKES WHERE USER_ID = %(user_id)s AND UNITID = %(unitid)s",
        {"user_id": user_id, "unitid": req.unitid},
    )
    execute(
        """
        MERGE INTO DATA_LAKE.PUBLIC.USER_DISLIKES t
        USING (
          SELECT %(user_id)s AS USER_ID, %(unitid)s AS UNITID
        ) s
        ON t.USER_ID = s.USER_ID AND t.UNITID = s.UNITID
        WHEN NOT MATCHED THEN
          INSERT (USER_ID, UNITID) VALUES (s.USER_ID, s.UNITID)
        """,
        {"user_id": user_id, "unitid": req.unitid},
    )
    return {"status": "ok"}


@app.delete("/likes")
def unlike(req: SwipeRequest, user_id: str = Depends(require_auth)):
    execute(
        "DELETE FROM DATA_LAKE.PUBLIC.USER_LIKES WHERE USER_ID = %(user)s AND UNITID = %(u)s",
        {"user": user_id, "u": req.unitid},
    )
    return {"status": "ok"}


@app.delete("/dislikes")
def undislike(req: SwipeRequest, user_id: str = Depends(require_auth)):
    execute(
        "DELETE FROM DATA_LAKE.PUBLIC.USER_DISLIKES WHERE USER_ID = %(user)s AND UNITID = %(u)s",
        {"user": user_id, "u": req.unitid},
    )
    return {"status": "ok"}


@app.get("/me")
def me(user_id: str = Depends(require_auth)):
    row = fetch_one(
        """
        SELECT USER_ID, EMAIL, GENDER, STATE_ABBREVIATION, RACE_ETHNICITY,
               SAT_ERW, SAT_MATH, ACT_COMPOSITE
        FROM DATA_LAKE.PUBLIC.USERS
        WHERE USER_ID = %(uid)s
        """,
        {"uid": user_id},
    )
    if not row:
        return {"user_id": user_id}
    return {
        "user_id": row["USER_ID"],
        "email": row["EMAIL"],
        "gender": row.get("GENDER"),
        "state": row.get("STATE_ABBREVIATION"),
        "race_ethnicity": row.get("RACE_ETHNICITY"),
        "sat_erw": row.get("SAT_ERW"),
        "sat_math": row.get("SAT_MATH"),
        "act_composite": row.get("ACT_COMPOSITE"),
    }


class UpdateMeRequest(BaseModel):
    gender: Optional[str] = None
    state_abbreviation: Optional[str] = None
    race_ethnicity: Optional[str] = None
    sat_erw: Optional[int] = None
    sat_math: Optional[int] = None
    act_composite: Optional[int] = None


@app.patch("/me")
def update_me(req: UpdateMeRequest, user_id: str = Depends(require_auth)):
    execute(
        """
        UPDATE DATA_LAKE.PUBLIC.USERS
        SET
          GENDER = COALESCE(%(gender)s, GENDER),
          STATE_ABBREVIATION = COALESCE(%(state)s, STATE_ABBREVIATION),
          RACE_ETHNICITY = COALESCE(%(race)s, RACE_ETHNICITY),
          SAT_ERW = COALESCE(%(sat_erw)s, SAT_ERW),
          SAT_MATH = COALESCE(%(sat_math)s, SAT_MATH),
          ACT_COMPOSITE = COALESCE(%(act)s, ACT_COMPOSITE)
        WHERE USER_ID = %(uid)s
        """,
        {
            "gender": req.gender,
            "state": req.state_abbreviation,
            "race": req.race_ethnicity,
            "sat_erw": req.sat_erw,
            "sat_math": req.sat_math,
            "act": req.act_composite,
            "uid": user_id,
        },
    )
    return {"status": "ok"}


class EstimateRequest(BaseModel):
    sat_erw: Optional[int] = None
    sat_math: Optional[int] = None
    sat_total: Optional[int] = None
    act_composite: Optional[int] = None


@app.post("/estimate")
def estimate(req: EstimateRequest):
    # Prefer explicit totals or compute from parts
    sat_total = req.sat_total
    if sat_total is None and (req.sat_erw is not None or req.sat_math is not None):
        erw = req.sat_erw if req.sat_erw is not None else 0
        math = req.sat_math if req.sat_math is not None else 0
        sat_total = erw + math if (req.sat_erw is not None and req.sat_math is not None) else None

    # If only ACT is provided, estimate SAT total
    if sat_total is None and req.act_composite is not None:
        sat_total = estimate_sat_total_from_act(req.act_composite)

    # If SAT total is provided but not parts, estimate parts
    sat_erw, sat_math = estimate_sat_parts_from_total(sat_total, req.sat_erw, req.sat_math) if sat_total else (req.sat_erw, req.sat_math)

    # If ACT missing and SAT available, estimate ACT
    act_est = req.act_composite
    if act_est is None and sat_total is not None:
        act_est = estimate_act_from_sat_total(sat_total)

    return {
        "sat_erw": sat_erw,
        "sat_math": sat_math,
        "sat_total": sat_total,
        "act_composite": act_est,
    }


@app.get("/images/sample")
async def images_sample(limit: int = 50):
    rows = await fetch_wikidata_images()
    rows = rows[: max(0, min(limit, len(rows)))]
    # Attach a fetchable URL
    for r in rows:
        r["image_url"] = commons_file_url(r["image"], width=800)
    return {"count": len(rows), "items": rows}


@app.get("/images/by-unitid/{unitid}")
async def images_by_unitid(unitid: int, limit: int = 5):
    rows = await fetch_top_images_for_unitid(unitid, limit=limit)
    return {"unitid": unitid, "count": len(rows), "items": rows}


UNIVERSITY_COLUMNS = [
    "UNITID",
    "INSTITUTION_NAME",
    "YEAR",
    "CITY_LOCATION_OF_INSTITUTION",
    "STATE_ABBREVIATION",
    "INSTITUTIONS_INTERNET_WEBSITE_ADDRESS",
    "PERCENT_ADMITTED_TOTAL",
    "ADMISSIONS_YIELD_TOTAL",
    "TUITION_AND_FEES_2023_24",
    "TOTAL_PRICE_FOR_IN_STATE_STUDENTS_LIVING_ON_CAMPUS_2023_24",
    "TOTAL_PRICE_FOR_OUT_OF_STATE_STUDENTS_LIVING_ON_CAMPUS_2023_24",
    "INSTITUTION_SIZE_CATEGORY",
    "LEVEL_OF_INSTITUTION",
    "CONTROL_OF_INSTITUTION",
    "DEGREE_OF_URBANIZATION_URBAN_CENTRIC_LOCALE",
    "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_AMERICAN_INDIAN_OR_ALASKA_NATIVE",
    "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_ASIAN",
    "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_BLACK_OR_AFRICAN_AMERICAN",
    "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_HISPANIC_LATINO",
    "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_NATIVE_HAWAIIAN_OR_OTHER_PACIFIC_ISLANDER",
    "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_WHITE",
    "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_TWO_OR_MORE_RACES",
    "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_RACE_ETHNICITY_UNKNOWN",
    "PERCENT_OF_UNDERGRADUATE_ENROLLMENT_THAT_ARE_WOMEN",
    "FULL_TIME_RETENTION_RATE_2023",
    "STUDENT_TO_FACULTY_RATIO",
    "GRADUATION_RATE_TOTAL_COHORT",
    "PERCENT_OF_FULL_TIME_FIRST_TIME_UNDERGRADUATES_AWARDED_ANY_FINANCIAL_AID",
    "AVERAGE_AMOUNT_OF_FEDERAL_STATE_LOCAL_OR_INSTITUTIONAL_GRANT_AID_AWARDED",
    "AVERAGE_NET_PRICE_STUDENTS_AWARDED_GRANT_OR_SCHOLARSHIP_AID_2022_23",
    "APPLICANTS_TOTAL",
    "PERCENT_OF_FIRST_TIME_DEGREE_CERTIFICATE_SEEKING_STUDENTS_SUBMITTING_SAT_SCORES",
    "PERCENT_OF_FIRST_TIME_DEGREE_CERTIFICATE_SEEKING_STUDENTS_SUBMITTING_ACT_SCORES",
    "SAT_EVIDENCE_BASED_READING_AND_WRITING_25TH_PERCENTILE_SCORE",
    "SAT_EVIDENCE_BASED_READING_AND_WRITING_50TH_PERCENTILE_SCORE",
    "SAT_EVIDENCE_BASED_READING_AND_WRITING_75TH_PERCENTILE_SCORE",
    "SAT_MATH_25TH_PERCENTILE_SCORE",
    "SAT_MATH_50TH_PERCENTILE_SCORE",
    "SAT_MATH_75TH_PERCENTILE_SCORE",
    "ACT_COMPOSITE_25TH_PERCENTILE_SCORE",
    "ACT_COMPOSITE_50TH_PERCENTILE_SCORE",
    "ACT_COMPOSITE_75TH_PERCENTILE_SCORE"
]


def _row_to_university(row: dict) -> dict:
    return {k.lower(): row.get(k) for k in UNIVERSITY_COLUMNS}


@app.get("/universities/random")
async def university_random():
    cols = ", ".join(UNIVERSITY_COLUMNS)
    query = f"""
        SELECT {cols}
        FROM DATA_LAKE.PUBLIC.UNIVERSITY_DATA
        ORDER BY RANDOM()
        LIMIT 1
    """
    row = await anyio.to_thread.run_sync(lambda: fetch_one(query))
    if not row:
        return {"error": "no data"}
    uni = _row_to_university(row)
    images = await fetch_top_images_for_unitid(int(uni["unitid"]))
    uni["images"] = images
    return uni


def _kumo_available() -> bool:
    try:
        import kumoai  # type: ignore
        return bool(settings.kumo_key)
    except Exception:
        return False




@app.get("/universities/recommendations")
async def universities_recommendations(user_id: str, top_k: int = 10):
    logger = logging.getLogger("uvicorn")
    if not (settings.kumo_api_key):
        logger.info("Recommendations fallback: Kumo unavailable for user %s", user_id)
        rand = await university_random()
        return {"items": [rand] if isinstance(rand, dict) else []}

    try:
        # Fetch seen unitids (likes + dislikes) using optimized query
        interactions = await anyio.to_thread.run_sync(
            lambda: BatchedQueries.fetch_user_interactions(user_id)
        )
        seen_unitids = interactions["likes"] | interactions["dislikes"]

        # Generate recommendations directly without caching
        recs = await anyio.to_thread.run_sync(
            lambda: recommend_top_k(
                user_id=user_id, 
                top_k=top_k, 
                horizon_days=180
            )
        )
        
        # Filter out seen units
        recs = [rec for rec in recs if int(rec.get("unitid")) not in seen_unitids]
        if not recs:
            # Fallback if RFM empty
            rand = await university_random()
            return {"items": [rand] if isinstance(rand, dict) else []}

        # Serve the first recommendation
        first_rec = recs[0]
        unitid = int(first_rec.get("unitid"))
        score = float(first_rec.get("score", 0.0))

        from .db import get_connection
        import snowflake.connector
        cols = ", ".join(UNIVERSITY_COLUMNS)

        def _fetch_one(uid_local: int):
            with get_connection() as conn:
                with conn.cursor(snowflake.connector.DictCursor) as cur:  # type: ignore
                    cur.execute(
                        f"SELECT {cols} FROM DATA_LAKE.PUBLIC.UNIVERSITY_DATA WHERE UNITID = %s",
                        (uid_local,),
                    )
                    return cur.fetchone()
        
        row = await anyio.to_thread.run_sync(lambda: _fetch_one(unitid))
        if not row:
            rand = await university_random()
            return {"items": [rand] if isinstance(rand, dict) else []}
        
        u = _row_to_university(row)
        u["score"] = score
        return {"items": [u]}
        
    except Exception as e:
        logger = logging.getLogger("uvicorn")
        logger.info("RFM recommendations error for user %s: %s; fallback to random", user_id, e)
        rand = await university_random()
        return {"items": [rand] if isinstance(rand, dict) else [], "error": str(e)}
@app.get("/me/likes")
def list_likes(user_id: str = Depends(require_auth)):
    rows = fetch_all(
        """
        SELECT l.UNITID, u.INSTITUTION_NAME, l.CREATED_AT
        FROM DATA_LAKE.PUBLIC.USER_LIKES l
        JOIN DATA_LAKE.PUBLIC.UNIVERSITY_DATA u ON u.UNITID = l.UNITID
        WHERE l.USER_ID = %(uid)s
        ORDER BY l.CREATED_AT DESC
        """,
        {"uid": user_id},
    )
    return {"items": rows}


@app.get("/me/dislikes")
def list_dislikes(user_id: str = Depends(require_auth)):
    rows = fetch_all(
        """
        SELECT d.UNITID, u.INSTITUTION_NAME, d.CREATED_AT
        FROM DATA_LAKE.PUBLIC.USER_DISLIKES d
        JOIN DATA_LAKE.PUBLIC.UNIVERSITY_DATA u ON u.UNITID = d.UNITID
        WHERE d.USER_ID = %(uid)s
        ORDER BY d.CREATED_AT DESC
        """,
        {"uid": user_id},
    )
    return {"items": rows}


@app.get("/universities/search")
async def universities_search(q: str, state: Optional[str] = None, limit: int = 20):
    cols = ", ".join(UNIVERSITY_COLUMNS)
    like = f"%{q}%"
    from .db import get_connection
    import snowflake.connector
    def _q():
        with get_connection() as conn:
            with conn.cursor(snowflake.connector.DictCursor) as cur:  # type: ignore
                if state:
                    cur.execute(
                        f"SELECT {cols} FROM DATA_LAKE.PUBLIC.UNIVERSITY_DATA WHERE INSTITUTION_NAME ILIKE %s AND STATE_ABBREVIATION = %s LIMIT %s",
                        (like, state, limit),
                    )
                else:
                    cur.execute(
                        f"SELECT {cols} FROM DATA_LAKE.PUBLIC.UNIVERSITY_DATA WHERE INSTITUTION_NAME ILIKE %s LIMIT %s",
                        (like, limit),
                    )
                return cur.fetchall()
    rows = await anyio.to_thread.run_sync(_q)
    return {"items": [_row_to_university(r) for r in rows]}

@app.get("/universities/{unitid}")
async def university_by_unitid(unitid: int):
    cols = ", ".join(UNIVERSITY_COLUMNS)
    row = await anyio.to_thread.run_sync(
        lambda: fetch_one(
            f"SELECT {cols} FROM DATA_LAKE.PUBLIC.UNIVERSITY_DATA WHERE UNITID = %(u)s",
            {"u": unitid},
        )
    )
    if not row:
        return {"error": "not found"}
    uni = _row_to_university(row)
    images = await fetch_top_images_for_unitid(int(uni["unitid"]))
    uni["images"] = images
    return uni




