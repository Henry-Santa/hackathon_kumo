from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd


def normalize_column_name(column_name: str) -> str:
    """Convert a column header to snake_case, removing extra symbols.

    Additionally, if the header contains a dot (.), drop any prefix before the dot.
    For example: "HD2023.City location of institution" -> "city_location_of_institution".
    """
    # If header has a prefix like "HD2023.", drop it
    if "." in column_name:
        column_name = column_name.split(".")[-1]

    name = column_name.strip().lower()
    # Replace possessives/apostrophes, slashes and parentheses with spaces
    name = re.sub(r"[\'\(\)\[\]\{\}]", "", name)
    name = re.sub(r"[\-/]+", " ", name)
    # Replace non-alphanumeric with underscore
    name = re.sub(r"[^0-9a-z]+", "_", name)
    # Collapse multiple underscores and trim
    name = re.sub(r"__+", "_", name).strip("_")
    return name


def ensure_url_scheme(url: str) -> str:
    if not isinstance(url, str) or url == "" or pd.isna(url):
        return np.nan
    u = url.strip()
    if not re.match(r"^[a-z]+://", u):
        u = "http://" + u
    return u


def coerce_bool(value: object) -> Optional[bool]:
    """Map textual membership/boolean values to True/False/NaN.

    Rules:
    - Yes/True -> True
    - No/Implied no/False -> False
    - Not applicable/blank/unknown -> NaN
    """
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float)):
        # Numeric 1/0 occasionally appears
        if pd.isna(value):
            return np.nan
        return bool(int(value))
    text = str(value).strip().lower()
    if text in {"yes", "y", "true", "t", "1"}:
        return True
    if text in {"no", "n", "false", "f", "0", "implied no", "implied_no"}:
        return False
    if text in {"not applicable", "na", "n/a", "none", ""}:
        return np.nan
    # Default: leave as NaN when not recognized
    return np.nan


def coerce_numeric(series: pd.Series) -> pd.Series:
    """Convert a pandas Series to numeric (float) safely, preserving NaNs."""
    return pd.to_numeric(series, errors="coerce")


def coerce_integer(series: pd.Series) -> pd.Series:
    """Convert a pandas Series to pandas nullable integer (Int64)."""
    coerced = pd.to_numeric(series, errors="coerce").round()
    return coerced.astype("Int64")


def extract_zip5(zip_value: object) -> Optional[str]:
    """Return 5-digit ZIP from ZIP or ZIP+4; keep as string, or NaN."""
    if pd.isna(zip_value):
        return np.nan
    s = str(zip_value).strip()
    # Extract first 5 consecutive digits
    m = re.search(r"(\d{5})", s)
    return m.group(1) if m else np.nan


def detect_boolean_columns(df: pd.DataFrame) -> list[str]:
    """Heuristically detect columns that look like boolean membership flags."""
    candidates = []
    for col in df.columns:
        values = set(
            str(v).strip().lower()
            for v in df[col].dropna().unique().tolist()[:50]
        )
        possible_bools = {"yes", "no", "implied no", "not applicable", "true", "false", "0", "1"}
        if values and values.issubset(possible_bools):
            candidates.append(col)
        # Also treat columns with names suggesting membership/yes-no
        elif re.search(r"\b(member|applicable|nca+a|naia|njcaa|football|basketball|baseball|track)\b", col):
            candidates.append(col)
    return sorted(set(candidates))


def detect_percentage_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if re.search(r"percent|rate", c)]


def detect_money_columns(df: pd.DataFrame) -> list[str]:
    patterns = r"tuition|fee|price|amount|net_price|grant"
    return [c for c in df.columns if re.search(patterns, c)]


def detect_ratio_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if "ratio" in c]


def detect_score_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if re.search(r"\b(sat|act)\b", c)]


def clean_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    # 1) Normalize column names to snake_case; handle duplicate headers gracefully
    normalized_names: list[str] = []
    seen: dict[str, int] = {}
    for original in df_raw.columns:
        base = normalize_column_name(str(original))
        if base in seen:
            seen[base] += 1
            base = f"{base}_{seen[base]}"
        else:
            seen[base] = 0
        normalized_names.append(base)
    df = df_raw.copy()
    df.columns = normalized_names

    # 2) Trim whitespace from all string-like cells
    df = df.apply(lambda s: s.str.strip() if s.dtype == "object" else s)

    # 3) Standardize URLs and ZIP codes where present
    for col in df.columns:
        if "website" in col or "internet" in col:
            df[col] = df[col].map(ensure_url_scheme)
        if "zip" in col:
            df[f"{col}_zip5"] = df[col].map(extract_zip5)

    # 4) Coerce booleans
    boolean_cols = detect_boolean_columns(df)
    for col in boolean_cols:
        df[col] = df[col].map(coerce_bool).astype("boolean")

    # 5) Coerce numeric classes
    percentage_cols = detect_percentage_columns(df)
    money_cols = detect_money_columns(df)
    ratio_cols = detect_ratio_columns(df)
    score_cols = detect_score_columns(df)

    # Make sure sets are disjoint when applying specific dtypes
    handled_cols: set[str] = set()

    # Percentages: keep as float 0-100 when source is like 66
    for col in percentage_cols:
        df[col] = coerce_numeric(df[col])
        handled_cols.add(col)

    # Money as nullable Int64
    for col in money_cols:
        if col in handled_cols:
            continue
        df[col] = coerce_integer(df[col])
        handled_cols.add(col)

    # Ratios as float
    for col in ratio_cols:
        if col in handled_cols:
            continue
        df[col] = coerce_numeric(df[col])
        handled_cols.add(col)

    # Scores as integer
    for col in score_cols:
        if col in handled_cols:
            continue
        df[col] = coerce_integer(df[col])
        handled_cols.add(col)

    # Remaining obvious numerics: unitid, year, applicants counts, staff
    numeric_name_hints = [
        r"\bunitid\b",
        r"\byear\b",
        r"applicants",
        r"fte",
        r"staff",
        r"retention",
        r"yield",
    ]
    numeric_pattern = re.compile("|".join(numeric_name_hints))
    for col in df.columns:
        if col in handled_cols:
            continue
        if numeric_pattern.search(col):
            # Use float for rates/retention, Int for counts
            if "rate" in col or "yield" in col:
                df[col] = coerce_numeric(df[col])
            else:
                df[col] = coerce_integer(df[col])

    # 6) Drop exact duplicate rows; then de-duplicate by unitid/year if both exist
    df = df.drop_duplicates()
    if "unitid" in df.columns and "year" in df.columns:
        df = df.sort_values(["unitid", "year"]).drop_duplicates(["unitid", "year"], keep="first")

    # 7) Consistent institution name casing/whitespace
    if "institution_name" in df.columns:
        df["institution_name"] = df["institution_name"].astype("string").str.strip()

    # 8) Derive cultural region from state
    df = add_region_from_state(df)

    return df.reset_index(drop=True)


def read_raw_csv(path: Path) -> pd.DataFrame:
    # Read with dtype=str first to avoid unintended coercions; pandas will parse NaNs
    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=True,
        na_values=["", " ", "NA", "N/A", "Not applicable"],
        quoting=1,  # csv.QUOTE_MINIMAL
    )


def write_output(df: pd.DataFrame, output_path: Path, output_format: str) -> None:
    output_format = output_format.lower()
    if output_format == "csv":
        df.to_csv(output_path, index=False)
    elif output_format in {"parquet", "pq"}:
        # Requires pyarrow or fastparquet
        df.to_parquet(output_path, index=False)
    else:
        raise ValueError(f"Unsupported output format: {output_format}")


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean the IPEDS-like institutional dataset.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("raw_data.csv"),
        help="Path to the raw CSV file (default: raw_data.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("cleaned_data.csv"),
        help="Output file path (default: cleaned_data.csv)",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "parquet"],
        default="csv",
        help="Output format (csv or parquet). Default: csv",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    raw_df = read_raw_csv(args.input)
    cleaned_df = clean_dataframe(raw_df)

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_output(cleaned_df, args.output, args.format)
    print(f"Wrote cleaned dataset to {args.output} ({args.format}) with {len(cleaned_df):,} rows and {len(cleaned_df.columns)} columns.")
# ---------------------
# Region mapping helpers
# ---------------------

_ABBR_TO_NAME = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
}

_REGION_TO_STATES = {
    # User preference examples: Alabama -> south, Florida -> southeast
    "south": {"Alabama", "Mississippi", "Louisiana", "Tennessee", "Kentucky", "Arkansas"},
    "southeast": {"Florida", "Georgia", "South Carolina", "North Carolina"},
    "mid-atlantic": {"Virginia", "District of Columbia", "Maryland", "Delaware", "New Jersey", "Pennsylvania", "New York"},
    "new england": {"Maine", "New Hampshire", "Vermont", "Massachusetts", "Rhode Island", "Connecticut"},
    "midwest": {"Ohio", "Michigan", "Indiana", "Illinois", "Wisconsin", "Minnesota", "Iowa", "Missouri"},
    "great plains": {"North Dakota", "South Dakota", "Nebraska", "Kansas", "Oklahoma"},
    "southwest": {"Texas", "New Mexico", "Arizona"},
    "mountain west": {"Colorado", "Utah", "Wyoming", "Montana", "Idaho", "Nevada"},
    "pacific": {"California", "Oregon", "Washington", "Alaska", "Hawaii"},
    "appalachia": {"West Virginia"},
}

_NAME_TO_REGION = {
    state: region for region, states in _REGION_TO_STATES.items() for state in states
}


def _normalize_state_value(value: object) -> Optional[str]:
    if pd.isna(value):
        return None
    s = str(value).strip()
    if not s:
        return None
    # Try abbreviation first
    upper = s.upper()
    if upper in _ABBR_TO_NAME:
        return _ABBR_TO_NAME[upper]
    # Title-case full names for matching
    return s.title()


def map_state_to_region(value: object) -> Optional[str]:
    name = _normalize_state_value(value)
    if not name:
        return np.nan
    return _NAME_TO_REGION.get(name, np.nan)


def add_region_from_state(df: pd.DataFrame) -> pd.DataFrame:
    # Find a state column to use
    candidate_order = [c for c in df.columns if re.fullmatch(r"state(_abbreviation)?(_\d+)?", c)]
    if not candidate_order:
        # Fallback: any column containing 'state'
        candidate_order = [c for c in df.columns if "state" in c]
    state_col = candidate_order[0] if candidate_order else None
    if state_col is None:
        return df

    df = df.copy()
    df["region"] = df[state_col].map(map_state_to_region).astype("string")
    return df


if __name__ == "__main__":
    main()
