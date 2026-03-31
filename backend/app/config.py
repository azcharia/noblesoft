"""
Configuration Management
Loads environment variables and provides application settings
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "NobleSoft"
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001,https://noblesoft.app"

    # Security headers and HTTPS
    SECURITY_HEADERS_ENABLED: bool = True
    SECURITY_CSP_PROD: str = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    SECURITY_CSP_DEV: str = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    SECURITY_REFERRER_POLICY: str = "strict-origin-when-cross-origin"
    SECURITY_PERMISSIONS_POLICY: str = "camera=(), microphone=(), geolocation=(), payment=()"
    SECURITY_FRAME_OPTIONS: str = "DENY"
    SECURITY_HSTS: str = "max-age=31536000; includeSubDomains; preload"
    ENFORCE_HTTPS: bool = True
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS string into list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str  # Public anon key for client-side
    SUPABASE_SERVICE_ROLE_KEY: str  # Service role key for server-side admin operations
    
    # JWT Configuration
    JWT_SECRET: str  # Supabase JWT secret for token verification
    JWT_ALGORITHM: str = "HS256"
    
    # AI/ML Configuration - 100% FREE with Groq
    GROQ_API_KEY: str
    GROQ_MODEL: str = "openai/gpt-oss-120b"  # FREE Groq model
    TAVILY_API_KEY: str = ""
    TAVILY_ENABLED: bool = True
    TAVILY_MAX_RESULTS: int = 5
    ORCHESTRATION_ENABLED: bool = True
    ORCHESTRATION_ENABLE_HYBRID_FOR_MIXED_INTENT: bool = True
    ORCHESTRATION_ENTERPRISE_ONLY: bool = False
    ORCHESTRATION_TIMEOUT_SECONDS: float = 10.0

    @property
    def tavily_api_key(self) -> str:
        """Resolve Tavily key for external web retrieval."""
        return (self.TAVILY_API_KEY or "").strip()

    @property
    def is_tavily_enabled(self) -> bool:
        """Whether Tavily web retrieval routing should be enabled."""
        return bool(self.TAVILY_ENABLED and self.tavily_api_key)

    @property
    def is_orchestration_enabled(self) -> bool:
        """Whether manager-auditor orchestration can be used."""
        return bool(self.ORCHESTRATION_ENABLED and self.is_tavily_enabled)

    # Midtrans Billing Configuration (optional until billing flow is enabled)
    MIDTRANS_SERVER_KEY: str = ""
    MIDTRANS_CLIENT_KEY: str = ""
    MIDTRANS_MERCHANT_ID: str = ""
    MIDTRANS_IS_PRODUCTION: bool = False

    @property
    def midtrans_api_base_url(self) -> str:
        """Resolve Midtrans API base URL based on environment mode."""
        if self.MIDTRANS_IS_PRODUCTION:
            return "https://app.midtrans.com"
        return "https://app.sandbox.midtrans.com"
    
    # Embedding Configuration - FREE local embeddings
    USE_LOCAL_EMBEDDINGS: bool = True
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"  # FREE local model
    EMBEDDING_DIMENSION: int = 384  # Dimension for all-MiniLM-L6-v2
    
    # Rate Limiting (requests per minute by tier)
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_STORE: str = "memory"
    REDIS_URL: str = ""
    RATE_LIMIT_TRIAL: int = 10
    RATE_LIMIT_BASIC: int = 30
    RATE_LIMIT_PRO: int = 100
    RATE_LIMIT_ENTERPRISE: int = 500
    
    # Subscription Tier Limits
    MAX_USERS_TRIAL: int = 2
    MAX_USERS_BASIC: int = 5
    MAX_USERS_PRO: int = 20
    MAX_USERS_ENTERPRISE: int = 999
    
    TRIAL_DURATION_DAYS: int = 14
    
    # Feature Flags by Tier
    FEATURES_TRIAL: List[str] = ["dashboard", "inventory", "invoices"]
    FEATURES_BASIC: List[str] = ["dashboard", "inventory", "invoices", "payment_tracking"]
    FEATURES_PRO: List[str] = ["dashboard", "inventory", "invoices", "payment_tracking", "ai_chat", "analytics"]
    FEATURES_ENTERPRISE: List[str] = ["dashboard", "inventory", "invoices", "payment_tracking", "ai_chat", "analytics", "multi_branch", "advanced_governance"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    @field_validator(
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "JWT_SECRET",
        "GROQ_API_KEY",
    )
    @classmethod
    def validate_required_secret_values(cls, value: str, info) -> str:
        """Reject empty or placeholder values for required credentials."""
        if not value or not value.strip():
            raise ValueError(f"{info.field_name} must not be empty")

        lowered = value.lower()
        placeholder_markers = (
            "your-",
            "your_",
            "example",
            "changeme",
            "replace",
            "placeholder",
        )

        if any(marker in lowered for marker in placeholder_markers):
            raise ValueError(f"{info.field_name} appears to be a placeholder value")

        return value

    @field_validator("TAVILY_API_KEY")
    @classmethod
    def validate_optional_secret_values(cls, value: str) -> str:
        """Allow empty optional secrets but reject obvious placeholders when present."""
        if value is None:
            return ""

        cleaned_value = value.strip()
        if not cleaned_value:
            return ""

        lowered = cleaned_value.lower()
        placeholder_markers = (
            "your-",
            "your_",
            "example",
            "changeme",
            "replace",
            "placeholder",
        )

        if any(marker in lowered for marker in placeholder_markers):
            raise ValueError("TAVILY_API_KEY appears to be a placeholder value")

        return cleaned_value

    @field_validator("REDIS_URL")
    @classmethod
    def validate_optional_redis_url(cls, value: str) -> str:
        """Allow empty optional Redis URL but reject obvious placeholders when present."""
        if value is None:
            return ""

        cleaned_value = value.strip()
        if not cleaned_value:
            return ""

        lowered = cleaned_value.lower()
        placeholder_markers = (
            "your-",
            "your_",
            "example",
            "changeme",
            "replace",
            "placeholder",
        )

        if any(marker in lowered for marker in placeholder_markers):
            raise ValueError("REDIS_URL appears to be a placeholder value")

        return cleaned_value

    @field_validator("RATE_LIMIT_STORE")
    @classmethod
    def validate_rate_limit_store(cls, value: str) -> str:
        """Validate rate limit store selection."""
        allowed_stores = {"memory", "redis"}
        normalized = value.strip().lower()
        if normalized not in allowed_stores:
            raise ValueError("RATE_LIMIT_STORE must be one of: memory, redis")
        return normalized

    @model_validator(mode="after")
    def validate_environment_safety(self):
        """Enforce safer defaults in production environment."""
        allowed_environments = {"development", "staging", "production"}
        environment = self.ENVIRONMENT.lower()

        if environment not in allowed_environments:
            raise ValueError(f"ENVIRONMENT must be one of: {', '.join(sorted(allowed_environments))}")

        if environment == "production":
            if self.DEBUG:
                raise ValueError("DEBUG must be false in production")

            localhost_origins = [
                origin for origin in self.allowed_origins_list
                if "localhost" in origin or "127.0.0.1" in origin
            ]
            if localhost_origins:
                raise ValueError("ALLOWED_ORIGINS cannot contain localhost/127.0.0.1 in production")

        if self.RATE_LIMIT_STORE == "redis" and not self.REDIS_URL:
            raise ValueError("REDIS_URL must be set when RATE_LIMIT_STORE is redis")

        return self


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance
    Use this function to get settings throughout the application
    """
    return Settings()


# Global settings instance
settings = get_settings()
