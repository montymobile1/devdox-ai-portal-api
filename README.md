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
- **SonarCloud**: Code quality scanning tool

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
- This project uses Tortoise ORM to interact with the PostgreSQL database hosted on Supabase.
- Supabase project with vault extension enabled
- Choose your preferred connection method: API-based connection using Supabase keys, or direct PostgreSQL connection using database credentials
- Clerk account with API credentials
- Required environment variables configured
- SonarCloud for code quality scanning

### Installation

1. [x] Clone the repository:
   ```
   git clone https://github.com/montymobile1/devdox-ai-portal-api.git
   cd devdox-ai-portal-api
   ```
2. [x] Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. [x] Install dependencies:
   ```
   pip install -r requirements.txt
   ```

   > ⚠️ **Important Note for Windows Users:**  
   > The library `uvloop` is **not supported on Windows**.  
   > This is a known limitation and is unlikely to change, as confirmed by the maintainers:  
   > https://github.com/MagicStack/uvloop/issues/25  
   > If you're on Windows, installation may fail or silently skip `uvloop`. The application will still run, but without
   the performance optimizations provided by `uvloop`.
4. [x] Supabase Vault Setup
   Your Supabase project should have the vault extension enabled with a decrypted_secrets view that returns:

   name: The environment variable name
   decrypted_secret: The decrypted secret value

   **Security Considerations**

   _Service Role Key_: The script uses the Supabase service role key, which has elevated permissions. Store this securely.
   _Vault Keys_: Multiple encryption keys can be specified (comma-separated) for vault access.
   _Local .env_: The generated .env file will contain sensitive data. Ensure it's in your .gitignore.

5. [x] Create a `.env` file in the root directory with your credentials:

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
./entrypoint.sh
```

This bash script orchestrates the complete application initialization process by first fetching encrypted secrets from your Supabase vault and appending them to the local .env file,
then running the automated database migration system that handles both initial database setup and subsequent schema updates using Tortoise ORM and Aerich, 
and finally starting the FastAPI application server on host 0.0.0.0 port 8000 using Uvicorn. The script uses set -e to ensure it stops immediately if any step fails, providing a fail-fast approach that prevents the application from starting with incomplete configuration or database setup, making it ideal for containerized deployments where proper initialization is critical before serving requests.

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
4. Navigate to **Settings** > **Database**
    - Copy the following values:
      - **Host**: e.g. your-project.supabase.co
      - **Port**: usually 5432
      - **User**: usually postgres
      - **Database**: usually postgres
For more info visit: [Supabase Docs](https://supabase.com/docs/guides/database/connecting-to-postgres)

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

[//]: # ()
[//]: # ([//]: # &#40;### Where to Get These Values&#41;)
[//]: # ()
[//]: # ([//]: # &#40;&#41;)
[//]: # ([//]: # &#40;1. Go to your Supabase Dashboard&#41;)
[//]: # ()
[//]: # ([//]: # &#40;2. From the left-hand side Menu, Navigate to:&#41;)
[//]: # ()
[//]: # ([//]: # &#40;   ```&#41;)
[//]: # ()
[//]: # ([//]: # &#40;   Project Settings → Data API&#41;)
[//]: # ()
[//]: # ([//]: # &#40;   ```&#41;)
[//]: # ()
[//]: # ([//]: # &#40;3. Locate the following:&#41;)
[//]: # ()
[//]: # ([//]: # &#40;&#41;)
[//]: # ([//]: # &#40;| Field                 | Value Location                      |&#41;)
[//]: # ()
[//]: # ([//]: # &#40;|-----------------------|-------------------------------------|&#41;)
[//]: # ()
[//]: # ([//]: # &#40;| `SUPABASE_URL`        | **Project URL** &#40;top of the page&#41;   |&#41;)
[//]: # ()
[//]: # ([//]: # &#40;| `SUPABASE_SECRET_KEY` | **Project API Keys → service_role** |&#41;)
[//]: # ()
[//]: # (---)

[//]: # ()
[//]: # ([//]: # &#40;### ⚠️ Upcoming Change in API Key Naming &#40;Q2 2025&#41;&#41;)
[//]: # ()
[//]: # ([//]: # &#40;&#41;)
[//]: # ([//]: # &#40;Supabase has announced that:&#41;)
[//]: # ()
[//]: # ([//]: # &#40;&#41;)
[//]: # ([//]: # &#40;- `anon` → will be renamed to `publishable`&#41;)
[//]: # ()
[//]: # ([//]: # &#40;- `service_role` → will be renamed to `secret`&#41;)
[//]: # ()
[//]: # ([//]: # &#40;&#41;)
[//]: # ([//]: # &#40;Keep this in mind when using future versions of Supabase&#41;)
[//]: # ()
[//]: # ([//]: # &#40;&#41;)
[//]: # ([//]: # &#40;---&#41;)

### ⚠️ API Rate Limiting

Supabase applies rate limiting to REST API traffic, even when using the `service_role` key. This can result in
unexpected connection errors, such as SSL handshake failures or timeouts after multiple requests in quick succession.

For context and developer discussions on this behavior, see:

- [Developer discussion on rate limiting and infrastructure impact](https://www.reddit.com/r/Supabase/comments/15chrqx/lack_of_rate_limiting_makes_supabase_unsuitable/)

This behavior is part of Supabase's underlying infrastructure and not an issue within the `devdoxAI` codebase.

# Setting Up Clerk Authentication

This guide explains how to configure Clerk authentication for the `devdoxAI` FastAPI backend using [https://clerk.dev](https://clerk.dev).

✅ **Status:**  
Clerk authentication is now **fully implemented and enforced** in the backend.

All routes that require authentication use Clerk-issued JWT tokens. The backend validates these tokens using the Clerk SDK and extracts user metadata into a standardized `AuthenticatedUserDTO`.

---

## Step 1: Create a Clerk Account and Application

1. Visit [https://clerk.dev](https://clerk.dev) and sign in or create an account.
2. Click **"Create Application"** and follow the wizard (e.g., name it `devdox-local`).
3. Under **Sign-In Methods**, enable **Email** and disable others like OAuth for now (unless needed).

---

## Step 2: Retrieve Clerk Credentials

Navigate to your project in the Clerk dashboard:

### 🔑 Backend API Key

1. Click **"Configure"**
2. Under **"Developers" > "API Keys"**, find the `Clerk Secret Key`
3. Add to `.env`:

```env
CLERK_API_KEY=sk_test_XXXXXXXXXXXXXXXX
```

### 🔐 Public JWT Key

1. Still under **"API Keys"**, locate the **"JWT Public Key"**
2. Add to `.env`:

```env
CLERK_JWT_PUBLIC_KEY=pk_test_XXXXXXXXXXXXXXXX
```

---

## Step 3: Configure Environment Variables

Ensure your `.env` includes:

```env
CLERK_API_KEY=sk_test_...
CLERK_JWT_PUBLIC_KEY=pk_test_...
CLERK_USER_ID=user_...
CLERK_WEBHOOK_SECRET=whsec_...
```

---
## Step 4 :  Generates secure JWT tokens

The generate_clerk_token function in generate_token.py creates a new Clerk session for a specified user and generates a secure JWT token that can be used for authentication in your application.

**What it does:**

* Creates a new session in Clerk for the specified user using clerk.sessions.create()
* Generates a signed JWT token using clerk.sessions.create_token()
* Supports optional custom expiration times
* Includes comprehensive error handling and logging
* Validates that a JWT is actually returned before proceeding

## Step 5: Token Validation Logic

The FastAPI backend validates Clerk JWT tokens using the `clerk_backend_api` SDK. Tokens are extracted from either the `Authorization: Bearer <token>` header or the `__session` cookie.

### Authentication Flow:
1. Routes that require authentication depend on:  
   ```python
   user: AuthenticatedUserDTO = Depends(CurrentUser)
   ```
2. The `get_current_user()` function:
   - Extracts the JWT token
   - Verifies it using Clerk’s `CLERK_API_KEY` and `CLERK_JWT_PUBLIC_KEY`
3. If valid:
   - The token’s **payload** is parsed
   - User data is returned as `AuthenticatedUserDTO`
4. If invalid:
   - A `401 Unauthorized` is raised with a structured error message

---

### How to Customize JWT Payload in Clerk

To make Clerk include fields like `email` and `name` or any other fields inside your JWT tokens, you must manually configure the session token template.

**Location:**  
1. Go to your Clerk dashboard → **Configure** → **Sessions** (under *Session Management*)
2. Scroll down to the section titled **Customize session token**

You'll see a form like this:

```json
{
  "name": "{{user.full_name}}",
  "email": "{{user.primary_email_address}}",
   .....
}
```

You can use any field shown in the “Insert shortcodes” sidebar, including `user.public_metadata.role`, `user.username`, and more.

This configuration ensures that Clerk injects those values into the token payload, which you can decode in the backend.


---

## Step 6: Testing Clerk Auth (Mocked)

During testing, Clerk is **fully mocked** using `pytest` fixtures. This enables:

- Mocking signed-in users (`mock_clerk_signed_in`)
- Simulating sign-out or expired tokens (`mock_clerk_signed_out`)
- Generating valid test JWTs (`generate_test_jwt()`)

Tests can validate all auth flows without hitting Clerk’s servers.

See `tests/utils/test_auth.py` for examples of:

- Missing/malformed headers
- Auth failure reasons
- Valid user DTO parsing

---

## Step 7: Usage in Routes

```python
@router.get("/secure", response_model=...)
async def secure_endpoint(user: AuthenticatedUserDTO = Depends(CurrentUser)):
    return {"user_email": user.email}
```

All routes requiring authentication should use `user: AuthenticatedUserDTO = Depends(CurrentUser)`.

---

## Test-Driven Development Approach

This project follows a test-driven development (TDD) approach:

1. Write a test for a new feature
2. Run the test to ensure it fails
3. Implement the feature
4. Run the test to ensure it passes
5. Refactor code as necessary

All API routes are backed by unit tests to maintain 100% code coverage.

## Quality Assurance

SonarCloud is used for code quality scanning. Set up SonarCloud according to your environment and run scans regularly to
maintain code quality.

## License

This project is open source and available under the [MIT License](LICENSE).



