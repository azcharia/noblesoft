# NobleSoft Backend - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Setup Supabase Database

1. Go to your Supabase project
2. Open SQL Editor
3. Execute SQL files in this exact order:

  - `supabase_setup.sql` (base schema + RLS helper functions)
  - `supabase_phase4_governance.sql` (roles/permissions/branches prerequisites)
  - `supabase_phase5_enterprise_engagement.sql` (Onboarding/Support/QBR tables + permission seeds)

4. Verify Phase 5 Operations tables are present:

  ```sql
  SELECT table_name
  FROM information_schema.tables
  WHERE table_schema = 'public'
    AND table_name IN (
      'onboarding_items',
      'support_tickets',
      'support_ticket_comments',
      'qbr_cycles',
      'qbr_goals'
    )
  ORDER BY table_name;
  ```

5. Verify seeded permissions exist:

  ```sql
  SELECT code
  FROM permissions
  WHERE code IN (
      'onboarding.read',
      'onboarding.write',
      'support.read',
      'support.write',
      'support.assign',
      'qbr.read',
      'qbr.write'
  )
  ORDER BY code;
  ```

### Step 3: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
JWT_SECRET=your-jwt-secret-from-supabase
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...
```

**Where to find these:**
- Supabase Dashboard → Project Settings → API
- JWT Secret: Project Settings → API → JWT Settings
- Groq API: https://console.groq.com/keys
- OpenAI API: https://platform.openai.com/api-keys

### Step 4: Run the Server

```bash
uvicorn app.main:app --reload
```

Server starts at: http://localhost:8000

### Step 5: Test the API

Open http://localhost:8000/api/docs in your browser

You'll see interactive API documentation with all endpoints!

## 🧪 Testing Authentication

### Get a Test JWT Token

1. Create a test user in Supabase:
   - Go to Authentication → Users → Add User
   - Or use Supabase Auth API from frontend

2. Login and get JWT token (you'll implement this in frontend)

3. Test protected endpoints:

```bash
# Replace <TOKEN> with your actual JWT
curl -H "Authorization: Bearer <TOKEN>" \
  http://localhost:8000/api/v1/test/me
```

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py              ✅ FastAPI app
│   ├── config.py            ✅ Settings
│   ├── core/
│   │   ├── database.py      ✅ Supabase client
│   │   ├── security.py      ✅ JWT validation
│   │   ├── dependencies.py  ✅ Auth dependencies
│   │   └── middleware.py    ✅ Tenant context
│   └── api/v1/
│       ├── router.py        ✅ Main router
│       └── test_auth.py     ✅ Test endpoints
├── requirements.txt         ✅
├── .env.example            ✅
└── README.md               ✅
```

## 🔐 Available Test Endpoints

| Endpoint | Auth Required | Tier Required | Description |
|----------|---------------|---------------|-------------|
| `GET /health` | ❌ | - | Health check |
| `GET /api/v1/test/me` | ✅ | Any | Get user info |
| `GET /api/v1/test/public-or-private` | ❌ | - | Works with/without auth |
| `GET /api/v1/test/pro-feature` | ✅ | Pro/Enterprise | Pro feature demo |
| `GET /api/v1/test/admin-only` | ✅ | Any (Admin role) | Admin access |
| `GET /api/v1/test/owner-only` | ✅ | Any (Owner role) | Owner access |
| `GET /api/v1/test/tier-info` | ✅ | Any | Subscription details |

## 🎯 Next Steps

Phase 2 is complete! Ready for:
- ✅ Phase 3: Products & Invoices CRUD
- ⏳ Phase 4: AI Agent (LlamaIndex + Groq)
- ⏳ Phase 5: Frontend (Next.js)

## 🐛 Troubleshooting

**Error: "Module not found"**
```bash
# Make sure you're in the backend directory
cd backend
pip install -r requirements.txt
```

**Error: "Invalid JWT"**
- Check JWT_SECRET matches your Supabase project
- Verify token is not expired
- Ensure Authorization header format: `Bearer <token>`

**Error: "Database connection failed"**
- Verify SUPABASE_URL and keys in .env
- Check Supabase project is active
- Test connection in Supabase dashboard

## 📚 Documentation

- Full architecture: `PHASE_1_ARCHITECTURE.md`
- Phase 2 details: `PHASE_2_COMPLETE.md`
- API docs: http://localhost:8000/api/docs (when running)

---

**Ready to build!** 🎉
