# DevDox AI Portal API

A backend API service for the DevDox AI Portal, built with FastAPI and Supabase.

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Supabase Setup](#setting-up-supabase-for-devdoxai-manual-via-web)
- [Clerk Authentication](#setting-up-clerk-authentication)
- [Running the Application](#running-the-application)
- [Testing](#running-tests)
- [TDD](#test-driven-development-approach)
- [License](#license)

## Project Overview

DevDox AI Portal API is part of the DevDox AI project, an open-source tool that helps developers automate their software
development lifecycle (SDLC) by committing changes to git repositories. It serves as an AI-powered software engineer to
help developers code, document, and ship faster without burnout.

This repository contains the backend API service for the portal, which handles:

- Authentication and authorization via Clerk
- Git token secure storage and management
- Repository listing and selection
- User preference storage
- Token usage tracking and analytics


[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=montymobile1_devdox-ai-portal-api&metric=alert_status)](https://sonarcloud.io/dashboard?id=montymobile1_devdox-ai-portal-api)



## Architecture

DevDox AI Portal API is built with:

- **FastAPI**: Python web framework for API endpoints with automatic OpenAPI documentation
- **Supabase**: Backend-as-a-Service for data storage, accessed via REST API
- **Clerk**: Authentication and authorization service
- **SonarQube**: Code quality scanning tool

The API service is part of a larger system:

| Repository           | Jira Project Key | Description                            |
|----------------------|------------------|----------------------------------------|
| devdox-ai            | DEV              | Main documentation project and roadmap |
| devdox-ai-agent      | DV               | Core AI agent component                |
| devdox-ai-context    | DAC              | Context building service               |
| devdox-ai-portal     | DAP              | Frontend portal                        |
| devdox-ai-portal-api | DAPA             | Backend portal API (this repository)   |

## System Communication Flow

The DevDox AI Portal API communicates with:

1. **Frontend**: Receives requests from the devdox-ai-portal web interface
2. **Data Storage**: Interacts with Supabase (PostgreSQL) for data persistence
3. **Authentication**: Uses Clerk for user authentication and authorization
4. **Context Generation**: Creates tasks for the devdox-ai-context service when repository analysis is requested

## Project Structure

```
my_flask_supabase_app/
├── app/                            # Application package (actual FastAPI app code)
│   ├── __init__.py                 # Initialize FastAPI app, Supabase client, config
│   ├── config.py                   # Configuration settings (e.g., Supabase URL, API keys, etc.)
│   ├── routes/                     # Route definitions (FastAPI route functions)
│   │   ├── __init__.py             # Initialize API routers
│   │   └── example_routes.py       # Example route module (e.g., endpoints for one feature)
│   ├── services/                   # Service layer (business logic and external API calls)
│   │   ├── __init__.py
│   │   └── supabase_client.py      # Supabase API interaction logic (REST/RPC calls via HTTP)
│   ├── models/                     # Data models using Pydantic
│   │   └── __init__.py
│   ├── utils/                      # Utility functions (helpers, etc.)
│   │   └── __init__.py
│   └── main.py                     # Application entry point (creates FastAPI app and registers routes)
├── tests/                          # Test suite for TDD (mirrors app structure for clarity)
│   ├── __init__.py
│   ├── test_routes.py              # Tests for FastAPI endpoints (routes)
│   └── test_services.py            # Tests for service logic (including Supabase integration)
├── .env                            # Environment variables (Supabase URL, keys, secrets; not in version control)
├── requirements.txt                # Python dependencies
└── README.md                       # Project documentation and setup instructions
```

## Development Setup

### Prerequisites

- Python **&ge;** 3.12
- Supabase account with API credentials
- Clerk account with API credentials
- SonarQube for code quality scanning

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/montymobile1/devdox-ai-portal-api.git
   cd devdox-ai-portal-api
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

   > ⚠️ **Important Note for Windows Users:**  
   > The library `uvloop` is **not supported on Windows**.  
   > This is a known limitation and is unlikely to change, as confirmed by the maintainers:  
   > https://github.com/MagicStack/uvloop/issues/25  
   > If you're on Windows, installation may fail or silently skip `uvloop`. The application will still run, but without
   the performance optimizations provided by `uvloop`.

4. Create a `.env` file in the root directory with your credentials:

   | Variable Name             | Required | Deprecated | Description                                                                 |
   |---------------------------|----------|------------|-----------------------------------------------------------------------------|
   | `API_ENV`                 | ✅ Yes   | ❌ No      | Set to `development`, `staging`, or `production`                           |
   | `API_DEBUG`               | ✅ Yes   | ❌ No      | Set to `true` or `false` to enable or disable debug mode                   |
   | `SECRET_KEY`              | ✅ Yes   | ❌ No      | A random string used for cryptographic operations (e.g., sessions)         |
   |                           |          |            |                                                                             |
   | `SUPABASE_URL`            | ✅ Yes   | ❌ No      | Your Supabase project URL (from Supabase dashboard → Project Settings)     |
   | `SUPABASE_SECRET_KEY`     | ✅ Yes   | ❌ No      | Supabase service role key (backend use only, not for frontend)             |
   |                           |          |            |                                                                             |
   | `CLERK_API_KEY`           | ✅ Yes   | ❌ No      | Clerk backend API key (Configure → Developers → API Keys)                 |
   | `CLERK_JWT_PUBLIC_KEY`    | ✅ Yes   | ❌ No      | Clerk public key string (under Publishable Key → Public Key)               |
   |                           |          |            |                                                                             |
   | `CORS_ORIGINS`            | ✅ Yes   | ❌ No      | A JSON array of allowed origins, e.g. `["http://localhost:3000"]`          |
   |                           |          |            |                                                                             |
   | `HOST`                    | ✅ Yes   | ❌ No      | The host address to bind the server to                                     |
   | `PORT`                    | ✅ Yes   | ❌ No      | The port for the FastAPI server                                            |

# Running the Application

```
uvicorn app.main:app --reload
```

> ⚠️ **Note:**  
> The `--reload` flag enables hot-reloading during development, but on some machines or larger projects it can
> noticeably slow down startup or cause inconsistent behavior.  
> If you experience slowness or delayed execution, try running the app without the flag

# Running Tests

  ```bash
  pytest tests
  ```

Runs **all test files** in the current and nested directories.

---

### 2. Display Enhancements

- Verbose output:
  ```bash
  pytest -v
  ```

- Show `print()` output:
  ```bash
  pytest -s
  ```

- Control traceback length:
  ```bash
  pytest --tb=short  # other options: auto, long, no, line, native
  ```

# Setting Up Supabase for devdoxAI (Manual via Web)

This guide explains how to manually set up the Supabase backend for local development of the `devdoxAI` FastAPI project,
using the hosted [Supabase website](https://supabase.com/).

---

## Step 1: Create a Supabase Account

1. Visit [https://supabase.com](https://supabase.com)
2. Click **Start your project** and sign in (you can use GitHub, Google, or email).

---

## Step 2: Create a New Supabase Project

1. After signing in, click the **New project** button.
2. Fill in the required details:
    - **Project name** (e.g. `devdox-local`)
    - **Database password** Choose a secure one and save it somewhere safe.
    - Choose your region (nearest to your location or team).
3. Click **Create new project** and wait for setup to complete.

---

## Step 3: Apply Database Migrations via SQL Editor

> ❗️ **Important:**  
> An **automated migration system is NOT implemented yet**. All migrations **must be manually applied via SQL Editor**
> on Supabase. Automation is **planned for a future update**.

Once the project is ready:

1. In your Supabase dashboard, go to:
   ```
   Left-hand menu → SQL Editor
   ```

2. Click **+ New Query** (top-right) if you were not automatically directed to the editor.

3. Paste the contents of each migration script located at:
   ```
   devdoxAI/migrations/
   ```

    - First: `create_git_label.sql`
    - Then: `update_git_label_table.sql`

4. Click **Run** for each script.

5. Wait for the confirmation message for successful execution.

---

## Step 4: Verify the Schema

1. Go to:
   ```
   Left-hand menu → Table Editor
   ```

2. Confirm the following:
    - A table named `git_label` exists
    - The table has columns including `masked_token`
    - RLS (Row Level Security) policies are applied (check the **Policies** tab of the table)

---

## Notes

- Do **not** run the same script twice, it may throw "already exists" errors.
- This setup does **not** require the Supabase CLI.
- Ideal for quick onboarding and developer testing.

Next step: Connecting FastAPI to Supabase.

## Step 5: Connect FastAPI to Supabase

The `devdoxAI` backend communicates with Supabase via its REST API interface. To enable this, you must configure the
following environment variables in your `.env` file:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SECRET_KEY=your-service-role-key
```

---

### Where to Get These Values

1. Go to your Supabase Dashboard
2. From the left-hand side Menu, Navigate to:
   ```
   Project Settings → Data API
   ```
3. Locate the following:

| Field                 | Value Location                      |
|-----------------------|-------------------------------------|
| `SUPABASE_URL`        | **Project URL** (top of the page)   |
| `SUPABASE_SECRET_KEY` | **Project API Keys → service_role** |

---

### ⚠️ Upcoming Change in API Key Naming (Q2 2025)

Supabase has announced that:

- `anon` → will be renamed to `publishable`
- `service_role` → will be renamed to `secret`

Keep this in mind when using future versions of Supabase

---

### ⚠️ API Rate Limiting

Supabase applies rate limiting to REST API traffic, even when using the `service_role` key. This can result in
unexpected connection errors, such as SSL handshake failures or timeouts after multiple requests in quick succession.

For context and developer discussions on this behavior, see:

- [Developer discussion on rate limiting and infrastructure impact](https://www.reddit.com/r/Supabase/comments/15chrqx/lack_of_rate_limiting_makes_supabase_unsuitable/)

This behavior is part of Supabase's underlying infrastructure and not an issue within the `devdoxAI` codebase.

# Setting Up Clerk Authentication

This guide explains how to manually set up the Clerk Auth backend for local development of the `devdoxAI` FastAPI
project, using the hosted [https://clerk.dev](https://clerk.dev).
> ❗️ **Important:**
> Authentication is not yet implemented in the backend, so this is a preparatory step only.

---

#### 1. Create a Clerk Account and Application

1. Visit [https://clerk.dev](https://clerk.dev) and sign in or create a new account.
2. Once logged in, click **“Create Application”** and follow the steps to set up your project (e.g., `devdox-local`).
3. Pick Loging by email option and disable everything else

---

#### 2. Retrieve `CLERK_API_KEY`

1. Enter the created application
2. In the Clerk dashboard, click **“Configure”** in the menu bar.
3. Under the **“Developers”** section, click **“API Keys”**.
4. Copy the value labeled **`CLERK_SECRET_KEY`**.

Add it to your `.env` file:

```env
CLERK_API_KEY=sk_test_vKcJ6AZi...........RBnO8Gw1wBEHdgTO
```

---

#### 3. Retrieve `CLERK_JWT_PUBLIC_KEY`

1. Enter the created application
2. In the Clerk dashboard, click **“Configure”** in the menu bar.
3. Under the **“Developers”** section, click **“API Keys”**.
4. Under that section, copy the value labeled **“Public Key”**.

Add it to your `.env` file:

```env
CLERK_JWT_PUBLIC_KEY=pk_test_cHJvbW90ZWQtc2..........ZXJrLmFjY291bnRzLmRldiQ
```

## Test-Driven Development Approach

This project follows a test-driven development (TDD) approach:

1. Write a test for a new feature
2. Run the test to ensure it fails
3. Implement the feature
4. Run the test to ensure it passes
5. Refactor code as necessary

All API routes are backed by unit tests to maintain 100% code coverage.

## Quality Assurance

SonarQube is used for code quality scanning. Set up SonarQube according to your environment and run scans regularly to
maintain code quality.

## License

This project is open source and available under the [MIT License](LICENSE).



