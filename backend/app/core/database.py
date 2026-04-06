"""
Supabase Database Client Initialization
Provides both client and admin-level database access
"""
import logging
from typing import Optional

import httpx
from supabase import Client, ClientOptions, create_client

from app.config import settings

logger = logging.getLogger(__name__)


def _build_supabase_options() -> ClientOptions:
    """Configure Supabase clients with an explicit httpx client."""
    http_client = httpx.Client(
        timeout=httpx.Timeout(30.0),
        follow_redirects=True,
        http2=True,
    )
    return ClientOptions(httpx_client=http_client)


class SupabaseClient:
    """
    Singleton Supabase client manager
    Provides both user-level (with RLS) and admin-level (bypass RLS) clients
    """
    
    _client: Optional[Client] = None
    _admin_client: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """
        Get Supabase client with anon key (respects RLS policies)
        Use this for user-scoped operations
        """
        if cls._client is None:
            try:
                cls._client = create_client(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=settings.SUPABASE_ANON_KEY,
                    options=_build_supabase_options(),
                )
                logger.info("✅ Supabase client initialized (anon key)")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Supabase client: {str(e)}")
                raise
        return cls._client
    
    @classmethod
    def get_admin_client(cls) -> Client:
        """
        Get Supabase client with service role key (bypasses RLS)
        Use this ONLY for admin operations like:
        - Creating new tenants
        - System-level queries
        - Background jobs
        
        ⚠️ WARNING: This bypasses Row Level Security. Use with caution!
        """
        if cls._admin_client is None:
            try:
                cls._admin_client = create_client(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY,
                    options=_build_supabase_options(),
                )
                logger.info("✅ Supabase admin client initialized (service role key)")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Supabase admin client: {str(e)}")
                raise
        return cls._admin_client


# Convenience functions for dependency injection
def get_supabase_client() -> Client:
    """
    Dependency function to inject Supabase client
    Usage in FastAPI:
        @app.get("/endpoint")
        async def endpoint(db: Client = Depends(get_supabase_client)):
            ...
    """
    return SupabaseClient.get_client()


def get_supabase_admin_client() -> Client:
    """
    Dependency function to inject Supabase admin client
    ⚠️ Use only for admin operations!
    """
    return SupabaseClient.get_admin_client()


# Initialize clients on module import
try:
    supabase_client = SupabaseClient.get_client()
    supabase_admin_client = SupabaseClient.get_admin_client()
    logger.info("🗄️ Database clients ready")
except Exception as e:
    logger.error(f"🚨 Database initialization failed: {str(e)}")
    raise
