# Prompt Vault API

A minimal, production-quality FastAPI backend for saving prompts, AI responses, and managing personas.

## Tech Stack

- **Framework**: FastAPI (Python)
- **Database**: Supabase Postgres
- **ORM**: Async SQLAlchemy
- **Auth**: Supabase Auth (JWT)

## Quick Start

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_JWT_SECRET=your-jwt-secret
DATABASE_URL=postgresql+asyncpg://user:pass@db.supabase.co:5432/postgres
CORS_ORIGINS=http://localhost:3000
```

### 3. Run Database Migration

Execute `sql/001_initial_schema.sql` in your Supabase SQL Editor.

### 4. Start the Server

```bash
uvicorn app.main:app --reload
```

API docs available at: http://localhost:8000/docs

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/auth/me` | Get current user |

### Personas
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/personas` | Create persona |
| GET | `/api/personas` | List personas |
| GET | `/api/persona/{id}` | Get persona |
| PUT | `/api/persona/{id}` | Update persona |
| DELETE | `/api/persona/{id}` | Delete persona |

### Messages
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/messages` | Save message |
| GET | `/api/messages` | List messages |
| GET | `/api/message/{id}` | Get message |
| PUT | `/api/message/{id}` | Update message |
| DELETE | `/api/message/{id}` | Delete message |

## Features

- ✅ JWT authentication via Supabase Auth
- ✅ User-scoped data access (no cross-user access)
- ✅ Soft delete for all records
- ✅ Versioning on updates
- ✅ ULID primary keys
- ✅ Pagination support
- ✅ Message filtering by type/starred/persona