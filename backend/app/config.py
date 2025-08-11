from pydantic import BaseModel
import os


class Settings(BaseModel):
    snowflake_account: str
    snowflake_user: str
    snowflake_password: str
    snowflake_warehouse: str = "COMPUTE_WH"
    snowflake_database: str = "DATA_LAKE"
    snowflake_schema: str = "PUBLIC"
    snowflake_insecure: bool = False
    kumo_key: str | None = None
    jwt_secret: str = "dev-secret-change-me"
    jwt_iss: str = "college-matcher"
    jwt_aud: str = "college-matcher-web"

    @staticmethod
    def load() -> "Settings":
        # Avoid external dotenv dependency in prod runners; rely on environment
        def _to_bool(v: str | None, default: bool = False) -> bool:
            if v is None:
                return default
            return v.strip().lower() in {"1", "true", "yes", "y", "on"}

        return Settings(
            snowflake_account=os.getenv("SNOWFLAKE_ACCOUNT", ""),
            snowflake_user=os.getenv("SNOWFLAKE_USER", ""),
            snowflake_password=os.getenv("SNOWFLAKE_PASSWORD", ""),
            snowflake_warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            snowflake_database=os.getenv("SNOWFLAKE_DATABASE", "DATA_LAKE"),
            snowflake_schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
            snowflake_insecure=_to_bool(os.getenv("SNOWFLAKE_INSECURE"), False),
            kumo_key=os.getenv("KUMO_KEY"),
            jwt_secret=os.getenv("JWT_SECRET", "dev-secret-change-me"),
            jwt_iss=os.getenv("JWT_ISS", "college-matcher"),
            jwt_aud=os.getenv("JWT_AUD", "college-matcher-web"),
        )


settings = Settings.load()


