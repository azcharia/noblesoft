# Phase 4 Setup Guide: AI Chat

## Prerequisites

1. Supabase project with Phase 1 schema
2. Groq API key (for LLM)

## Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

New packages:
- `llama-index` - RAG orchestration
- `llama-index-vector-stores-postgres` - pgvector integration
- `groq` - Groq API client

## Step 2: Configure Environment

Add to `.env`:

```env
# Groq (for LLM)
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# Embedding config
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
USE_LOCAL_EMBEDDINGS=true
```

**Get API Key:**
- Groq: https://console.groq.com/keys

## Step 3: Setup Vector Search Function

1. Open Supabase SQL Editor
2. Copy content from `supabase_vector_search_function.sql`
3. Run the SQL
4. Verify: `SELECT * FROM match_documents(...)`

## Step 4: Embed Initial Data

Create a script `embed_data.py`:

```python
import asyncio
from app.ai.embeddings import EmbeddingService
from app.core.dependencies import CurrentUser

async def embed_all_data():
    service = EmbeddingService()
    
    # Mock current_user (replace with actual user)
    current_user = CurrentUser({
        "id": "user-uuid",
        "tenant_id": "tenant-uuid",
        "tenants": {"subscription_tier": "pro"}
    })
    
    print("Embedding products...")
    product_count = await service.embed_all_products(current_user)
    print(f"✅ Embedded {product_count} products")
    
    print("Embedding invoices...")
    invoice_count = await service.embed_all_invoices(current_user)
    print(f"✅ Embedded {invoice_count} invoices")

if __name__ == "__main__":
    asyncio.run(embed_all_data())
```

Run: `python embed_data.py`

After seeding data directly via SQL, embedding is NOT automatic. Validate and rebuild via API:

```bash
# Check coverage
curl -X GET http://localhost:8000/api/v1/chat/index-coverage \
  -H "Authorization: Bearer <JWT_TOKEN>"

# Rebuild embeddings for current tenant if coverage < 100%
curl -X POST http://localhost:8000/api/v1/chat/reindex \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

## Step 5: Test Chat Endpoint

Start server:
```bash
uvicorn app.main:app --reload
```

Test with curl:
```bash
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Berapa stok laptop yang tersedia?"
  }'
```

Or use Swagger UI: http://localhost:8000/api/docs

## Step 6: Verify Subscription Tier

Ensure test user has Pro or Enterprise tier:

```sql
UPDATE tenants 
SET subscription_tier = 'pro' 
WHERE id = 'your-tenant-uuid';
```

## Troubleshooting

### Error: "OpenAI API key not found"
- Check `.env` file has `OPENAI_API_KEY`
- Restart server after adding key

### Error: "Groq API error"
- Verify `GROQ_API_KEY` is correct
- Check Groq API status: https://status.groq.com

### Error: "Insufficient tier"
- Update tenant subscription_tier to 'pro' or 'enterprise'
- Check JWT token is valid

### No results from vector search
- Run embedding script first
- Check `document_embeddings` table has data
- Verify `match_documents` function exists
- Call `/api/v1/chat/index-coverage` and ensure product/invoice coverage is 100%
- If coverage is low, call `/api/v1/chat/reindex`

## Next Steps

1. Test various queries
2. Monitor response quality
3. Adjust prompts in `prompts.py` if needed
4. Implement auto-embedding on create/update (Phase 5)

## Example Queries to Test

```
"Berapa stok laptop yang tersedia?"
"Produk apa saja yang stoknya rendah?"
"Tampilkan invoice yang belum dibayar"
"Siapa customer dengan invoice terbesar?"
"Berapa total nilai inventory?"
```

Happy testing! 🚀
