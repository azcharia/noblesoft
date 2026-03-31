# NobleSoft Backend API

FastAPI backend for NobleSoft - B2B SaaS Enterprise AI Operating System for Indonesian UMKM.

## Tech Stack

- **Framework:** FastAPI (Python)
- **Database:** Supabase (PostgreSQL + pgvector)
- **Authentication:** Supabase Auth (JWT)
- **AI/ML:** LlamaIndex + Groq API

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration management
│   ├── core/                # Core functionality
│   │   ├── database.py      # Supabase client
│   │   ├── security.py      # JWT validation
│   │   ├── dependencies.py  # FastAPI dependencies
│   │   └── middleware.py    # Custom middleware
│   ├── api/                 # API routes (coming in Phase 3)
│   ├── models/              # Pydantic models
│   ├── services/            # Business logic
│   └── ai/                  # AI/ML orchestration
├── requirements.txt
└── .env
```

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required environment variables:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Supabase anon/public key
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key (admin)
- `JWT_SECRET`: Supabase JWT secret (from Project Settings > API)
- `GROQ_API_KEY`: Groq API key for LLM
- `OPENAI_API_KEY`: OpenAI API key for embeddings

### 3. Setup Database

Run the SQL schema from `PHASE_1_ARCHITECTURE.md` in your Supabase SQL Editor:
- Enable extensions (uuid-ossp, vector)
- Create tables (tenants, users, products, invoices, etc.)
- Setup RLS policies

### 4. Run Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/api/docs
- Health: http://localhost:8000/health

### 5. Run Tests

```bash
pytest
```

## API Documentation

Once running, visit http://localhost:8000/api/docs for interactive API documentation (Swagger UI).

## Authentication Flow

1. User logs in via Supabase Auth (handled by frontend)
2. Frontend receives JWT token
3. Frontend includes token in `Authorization: Bearer <token>` header
4. Backend validates JWT and extracts user/tenant context
5. All database queries automatically filtered by tenant_id via RLS

## Subscription Tier Enforcement

Use the `require_tier` dependency to restrict endpoints:

```python
from app.core.dependencies import require_tier, CurrentUser
from fastapi import Depends

@app.post("/ai/chat")
async def ai_chat(
    message: str,
    current_user: CurrentUser = Depends(require_tier(["pro", "enterprise"]))
):
    # Only Pro and Enterprise users can access this
    return {"response": "AI response"}
```

## Next Steps

- Phase 3: Implement CRUD endpoints (products, invoices)
- Phase 4: Integrate LlamaIndex + Groq for AI agent
- Phase 5: Build frontend with Next.js

## License

Proprietary - NobleSoft
