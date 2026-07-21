# MatchCast React Frontend

This is the primary UI for MatchCast and runs on localhost:5173 by default.

## Local Run

1. Install dependencies:

```bash
npm install
```

2. Create env file:

```bash
copy .env.example .env
```

3. Start frontend:

```bash
npm run dev
```

## Backend URL

Set API base in `.env`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

The app calls `${VITE_API_URL}/api/...` for upload, processing, analytics, and tracking.
