# DevDox AI Portal API

A backend API service for the DevDox AI Portal, built with Flask and Supabase.

## Project Overview

DevDox AI Portal API is part of the DevDox AI project, an open-source tool that helps developers automate their software development lifecycle (SDLC) by committing changes to git repositories. It serves as an AI-powered software engineer to help developers code, document, and ship faster without burnout.

This repository contains the backend API service for the portal, which handles:
- Authentication and authorization via Clerk
- Git token secure storage and management
- Repository listing and selection
- User preference storage
- Token usage tracking and analytics

## Architecture

DevDox AI Portal API is built with:
- **Flask**: Python web framework for API endpoints
- **Supabase**: Backend-as-a-Service for data storage, accessed via REST API
- **Clerk**: Authentication and authorization service
- **SonarQube**: Code quality scanning tool

The API service is part of a larger system:

| Repository | Jira Project Key | Description |
|------------|------------------|-------------|
| devdox-ai | DEV | Main documentation project and roadmap |
| devdox-ai-agent | DV | Core AI agent component |
| devdox-ai-context | DAC | Context building service |
| devdox-ai-portal | DAP | Frontend portal |
| devdox-ai-portal-api | DAPA | Backend portal API (this repository) |

## System Communication Flow

The DevDox AI Portal API communicates with:
1. **Frontend**: Receives requests from the devdox-ai-portal web interface
2. **Data Storage**: Interacts with Supabase (PostgreSQL) for data persistence
3. **Authentication**: Uses Clerk for user authentication and authorization
4. **Context Generation**: Creates tasks for the devdox-ai-context service when repository analysis is requested

## Project Structure

```
my_flask_supabase_app/
├── app/                            # Application package (actual Flask app code)
│   ├── __init__.py                 # Initialize Flask app, Supabase client, config
│   ├── config.py                   # Configuration settings (e.g., Supabase URL, API keys, etc.)
│   ├── routes/                     # Route definitions (Flask view functions)
│   │   ├── __init__.py             # Initialize blueprints for routes
│   │   └── example_routes.py       # Example route module (e.g., endpoints for one feature)
│   ├── services/                   # Service layer (business logic and external API calls)
│   │   ├── __init__.py
│   │   └── supabase_client.py      # Supabase API interaction logic (REST/RPC calls via HTTP)
│   ├── models/                     # Data models or schema definitions
│   │   └── __init__.py
│   ├── utils/                      # Utility functions (helpers, etc.)
│   │   └── __init__.py
│   └── main.py                     # Application entry point (creates Flask app and registers routes)
├── tests/                          # Test suite for TDD (mirrors app structure for clarity)
│   ├── __init__.py
│   ├── test_routes.py              # Tests for Flask endpoints (routes)
│   └── test_services.py            # Tests for service logic (including Supabase integration)
├── .env                            # Environment variables (Supabase URL, keys, secrets; not in version control)
├── requirements.txt                # Python dependencies
└── README.md                       # Project documentation and setup instructions
```

## Development Setup

### Prerequisites

- Python 3.9+
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

4. Create a `.env` file in the root directory with your credentials:
   ```
   FLASK_APP=app.main
   FLASK_ENV=development
   SUPABASE_URL=https://your-supabase-project.supabase.co
   SUPABASE_KEY=your-supabase-key
   CLERK_API_KEY=your-clerk-api-key
   ```

### Running the Application

```
flask run
```

### Running Tests

```
python -m unittest discover
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

SonarQube is used for code quality scanning. Set up SonarQube according to your environment and run scans regularly to maintain code quality.

## Key Jira Issues

| Issue Key | Summary | Description |
|-----------|---------|-------------|
| DAPA-1 | Create README.md for DevDox AI Portal API | Documentation for the backend API |

## Contributing

When contributing to this repository, please follow these guidelines:
1. Create a branch for each feature or bugfix
2. Write tests for your changes
3. Reference the Jira issue key in your commit messages (e.g., "Implemented user auth endpoints (DAPA-5)")
4. Submit a pull request for review

## License

This project is open source and available under the [MIT License](LICENSE).
