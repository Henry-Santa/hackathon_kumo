from __future__ import annotations

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from .db import fetch_one, execute
from .security import hash_password, verify_password, issue_jwt, decode_jwt
from enum import Enum
from .estimators import (
    estimate_act_from_sat_total,
    estimate_sat_total_from_act,
    estimate_sat_parts_from_total,
)
from .config import settings
import logging


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
        "Kumo key configured: %s",
        "yes" if settings.kumo_key else "no",
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
    gender: str | None = None
    state_abbreviation: StateFullName | None = None
    race_ethnicity: RaceEthnicity | None = None
    sat_erw: int | None = None
    sat_math: int | None = None
    act_composite: int | None = None


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

    sat_total: int | None = None
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


def require_auth(authorization: str | None = Header(default=None)) -> str:
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


@app.get("/me")
def me(user_id: str = Depends(require_auth)):
    return {"user_id": user_id}


class EstimateRequest(BaseModel):
    sat_erw: int | None = None
    sat_math: int | None = None
    sat_total: int | None = None
    act_composite: int | None = None


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


