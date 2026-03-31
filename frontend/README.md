# NobleSoft Frontend

Next.js 14 frontend for NobleSoft - B2B SaaS Enterprise AI Operating System.

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **UI Components:** shadcn/ui
- **Authentication:** Supabase Auth
- **API Client:** Native fetch with JWT token injection

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx          # Dashboard layout with sidebar
│   │   │   ├── chat/
│   │   │   │   └── page.tsx        # AI Chat interface
│   │   │   └── inventory/
│   │   │       └── page.tsx        # Inventory management
│   │   └── (auth)/
│   │       ├── login/
│   │       └── register/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx         # Navigation with tier enforcement
│   │   │   └── Header.tsx          # Dashboard header
│   │   ├── chat/
│   │   │   ├── ChatInterface.tsx   # Main chat component
│   │   │   ├── MessageBubble.tsx   # Message display
│   │   │   ├── SourcesPanel.tsx    # RAG sources display
│   │   │   └── SuggestedQuestions.tsx
│   │   └── ui/                     # shadcn/ui components
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts           # Browser client
│   │   │   └── server.ts           # Server client
│   │   ├── api/
│   │   │   └── client.ts           # FastAPI client with JWT
│   │   └── utils.ts                # Utility functions
│   └── types/
│       └── database.ts             # Supabase types
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── .env.local
```

## Setup Instructions

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

Copy `.env.local.example` to `.env.local`:

```bash
cp .env.local.example .env.local
```

Edit `.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 3. Run Development Server

```bash
npm run dev
```

Open http://localhost:3000

## Key Features

### Authentication Flow

1. User logs in via Supabase Auth
2. Supabase returns JWT token
3. Token stored in browser session
4. All API requests include `Authorization: Bearer <token>` header
5. FastAPI validates token and extracts tenant context

### Subscription Tier Enforcement

- **Trial/Basic**: AI Assistant menu item shown but locked with padlock icon
- **Pro/Enterprise**: Full access to AI Assistant
- Visual indicators (badges, locks) for premium features
- Upgrade CTA in sidebar for non-Pro users

### AI Chat Interface

- Beautiful, modern ChatGPT-style UI
- Real-time message streaming (ready for WebSocket)
- Source attribution panel (shows RAG documents used)
- Suggested questions
- Conversation history
- Error handling with user-friendly messages

### Inventory Management

- Product list with search and filters
- Real-time stock status
- Low stock alerts
- Pagination
- Responsive data table

## API Integration

All API calls go through `apiClient` in `src/lib/api/client.ts`:

```typescript
import { apiClient } from '@/lib/api/client'

// Products
const products = await apiClient.products.list({ page: 1 })
const product = await apiClient.products.get(id)

// Invoices
const invoices = await apiClient.invoices.list({ page: 1 })

// AI Chat
const response = await apiClient.chat.send('Berapa stok laptop?')
```

JWT token automatically attached to all requests.

## Development

### Type Safety

All API responses are fully typed:

```typescript
interface Product {
  id: string
  sku: string
  name: string
  // ... full type definition
}
```

### Error Handling

```typescript
try {
  const data = await apiClient.products.list()
} catch (error) {
  if (error instanceof APIError) {
    console.error(error.status, error.message)
  }
}
```

### Utility Functions

```typescript
import { formatCurrency, formatDate } from '@/lib/utils'

formatCurrency(15000000) // "Rp 15.000.000"
formatDate('2024-01-15') // "15 Januari 2024"
```

## Building for Production

```bash
npm run build
npm run start
```

## Next Steps

- Implement authentication pages (login, register)
- Add invoice management UI
- Build analytics dashboard
- Implement real-time features (WebSocket)
- Add mobile responsiveness
- Implement dark mode

## License

Proprietary - NobleSoft
