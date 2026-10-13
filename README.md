# ACEest Fitness & Gym – DevOps CI/CD

A Flask-based fitness and gym management application developed as part of the **Introduction to DEVOPS (Merged - CSIZG514/SEZG514)** assignment.

The project demonstrates a complete DevOps workflow using **Git, GitHub, Pytest, Docker, Jenkins, and GitHub Actions**. The application provides REST APIs for managing fitness clients, fitness programs, progress tracking, and workout records.

---

## Table of Contents
- Project Overview
- Objectives
- Features
- Technology Stack
- Project Structure
- Prerequisites
- Local Setup
- Running the Application
- API Reference
- Testing
- Code Quality
- Docker
- Jenkins CI Pipeline
- GitHub Actions CI/CD
- DevOps Workflow
- Version Control
- Security and Quality Practices
- Database
- Troubleshooting
- Assignment Coverage
- Project Information


---

## Project Overview

**ACEest Fitness & Gym** is a lightweight fitness management application implemented using Flask.

The application allows fitness administrators to:

- Manage fitness clients
- Assign fitness programs
- Calculate recommended daily calories
- Track client progress
- Record workout information
- Retrieve client and workout details
- Monitor application health through a health-check endpoint

The project follows a DevOps-oriented development workflow in which application changes are validated through automated testing, code-quality checks, build validation, containerization, and CI pipelines.

---

## Objectives

The main objectives of the project are:

1. Develop a modular Flask-based fitness management application.
2. Maintain the source code using Git and GitHub.
3. Implement automated testing using Pytest.
4. Containerize the application using Docker.
5. Implement a Jenkins build and quality gate.
6. Implement a GitHub Actions CI/CD workflow.
7. Provide clear documentation for developers and maintainers.

---

## Features

### Client Management

The application supports:

- Creating new clients
- Retrieving all clients
- Retrieving an individual client
- Validating client information
- Preventing duplicate client records

Client information includes:

- Name
- Age
- Height
- Weight
- Fitness program
- Recommended calories
- Target weight
- Adherence
- Membership information

### Fitness Programs

The application provides three predefined fitness programs:

| Program | Description |
|---|---|
| **Fat Loss** | Program focused on reducing body weight |
| **Muscle Gain** | Program focused on muscle development |
| **Beginner** | General fitness program for new participants |

### Progress Tracking

Client progress can be recorded using:

- Client ID
- Week number
- Adherence percentage

Adherence values are validated between:

```text
0 – 100%

This endpoint can be used by:

- Developers
- CI/CD pipelines
- Container health checks
- Operational monitoring

---

# Technology Stack

| Technology | Purpose |
|---|---|
| **Python 3.12** | Application and CI runtime |
| **Flask 3.1.3** | Web application framework |
| **SQLite** | Lightweight database |
| **Pytest 9.1.1** | Automated testing |
| **pytest-flask 1.3.0** | Flask testing support |
| **Flake8 7.4.1** | Code quality and linting |
| **Docker** | Application containerization |
| **Git** | Version control |
| **GitHub** | Remote source repository |
| **Jenkins** | CI build and quality gate |
| **GitHub Actions** | CI/CD automation |

---

# Project Structure

```text
ACEest-Fitness-DevOps/
│
├── app.py
├── requirements.txt
├── pytest.ini
├── Dockerfile
├── .dockerignore
├── .gitignore
├── Jenkinsfile
├── README.md
│
├── tests/
│   └── test_app.py
│
└── .github/
    └── workflows/
        └── main.yml
```

## Important Files

| File | Description |
|---|---|
| `app.py` | Main Flask application and REST API implementation |
| `tests/test_app.py` | Automated Pytest test suite |
| `requirements.txt` | Project dependencies |
| `pytest.ini` | Pytest configuration |
| `Dockerfile` | Docker image definition |
| `.dockerignore` | Files excluded from Docker build context |
| `.gitignore` | Files excluded from Git |
| `Jenkinsfile` | Jenkins CI pipeline definition |
| `.github/workflows/main.yml` | GitHub Actions workflow |
| `README.md` | Project documentation |

---

# Prerequisites

The following software is required for local development:

- Python 3.12 or later
- Git
- pip

Docker is required when building or running the application container locally.

Verify Python:

```bash
python3 --version
```

Verify Git:

```bash
git --version
```

Verify Docker, if installed:

```bash
docker --version
```

---

# Local Setup

## 1. Clone the Repository

```bash
git clone https://github.com/2026ht66052/ACEest-Fitness-DevOps.git
cd ACEest-Fitness-DevOps
```

## 2. Create a Virtual Environment

Using Python 3.12:

```bash
python3.12 -m venv venv
```

## 3. Activate the Virtual Environment

### macOS / Linux

```bash
source venv/bin/activate
```

### Windows

```powershell
venv\Scripts\activate
```

## 4. Upgrade pip

```bash
python -m pip install --upgrade pip
```

## 5. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Running the Application

Start the Flask application:

```bash
python app.py
```

The application starts on:

```text
http://127.0.0.1:5000
```

The application can be accessed from a browser or tested using `curl`.

For example:

```bash
curl http://127.0.0.1:5000/health
```

A successful response confirms that the application is running.

---

# API Endpoints

## Application Status

### `GET /`

Returns basic application information.

Example:

```bash
curl http://127.0.0.1:5000/
```

---

## Health Check

### `GET /health`

Returns the current application health status.

Example:

```bash
curl http://127.0.0.1:5000/health
```

This endpoint is also used by the Docker container health check.

---

## Fitness Programs

### `GET /programs`

Returns the available fitness programs.

Example:

```bash
curl http://127.0.0.1:5000/programs
```

---

## Client Management

### `GET /clients`

Returns all registered clients.

Example:

```bash
curl http://127.0.0.1:5000/clients
```

### `POST /clients`

Creates a new client.

Example:

```bash
curl -X POST http://127.0.0.1:5000/clients \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John",
    "age": 25,
    "height": 175,
    "weight": 70,
    "program": "Beginner"
  }'
```

### `GET /clients/<client_id>`

Returns details for a specific client.

Example:

```bash
curl http://127.0.0.1:5000/clients/1
```

---

# Progress Tracking

## `GET /clients/<client_id>/progress`

Retrieves progress records for a client.

Example:

```bash
curl http://127.0.0.1:5000/clients/1/progress
```

## `POST /clients/<client_id>/progress`

Adds a progress record.

Example:

```bash
curl -X POST http://127.0.0.1:5000/clients/1/progress \
  -H "Content-Type: application/json" \
  -d '{
    "week": 1,
    "adherence": 90
  }'
```

---

# Workout Tracking

## `GET /clients/<client_id>/workouts`

Retrieves workout records for a client.

Example:

```bash
curl http://127.0.0.1:5000/clients/1/workouts
```

## `POST /clients/<client_id>/workouts`

Adds a workout record.

Example:

```bash
curl -X POST http://127.0.0.1:5000/clients/1/workouts \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-10-08",
    "type": "Strength Training",
    "duration": 60,
    "notes": "Upper body workout"
  }'
```

---

# Testing

The project uses **Pytest** for automated testing.

## Run the Complete Test Suite

```bash
pytest -v
```

The current automated test suite contains **14 tests** covering:

- Application home endpoint
- Health endpoint
- Fitness programs
- Client creation
- Required field validation
- Program validation
- Weight validation
- Client retrieval
- Non-existent client handling
- Progress creation
- Progress validation
- Progress retrieval
- Workout creation
- Workout retrieval

Expected result:

```text
14 passed
```

## Test Isolation

The automated tests use a temporary SQLite database.

This prevents test execution from modifying the application's normal development database.

---

# Code Quality

Flake8 is used to enforce basic Python code-quality standards.

Run Flake8 locally:

```bash
flake8 app.py
```

The application is also syntax-checked using Python's built-in compiler:

```bash
python -m py_compile app.py
```

These checks are automatically executed by the CI pipelines.

---

# Docker

The application includes a Dockerfile for containerization.

## Dockerfile Design

The Docker image uses:

- A lightweight Python base image
- Pinned application dependencies
- `pip --no-cache-dir`
- A dedicated non-root application user
- Docker `HEALTHCHECK`
- `.dockerignore` to exclude unnecessary development files

The application therefore does not run as the root user inside the container.

## Build the Docker Image

```bash
docker build -t aceest-fitness .
```

## Run the Container

```bash
docker run --rm -p 5000:5000 aceest-fitness
```

The application will then be available at:

```text
http://127.0.0.1:5000
```

## Verify the Container

Use the health endpoint:

```bash
curl http://127.0.0.1:5000/health
```

---

# Jenkins CI Pipeline

The Jenkins pipeline is defined in:

```text
Jenkinsfile
```

Jenkins retrieves the source code from the GitHub repository and executes the pipeline defined in source control.

## Jenkins Pipeline

The pipeline consists of the following stages:

```text
Checkout
    │
    ▼
Install Dependencies
    │
    ▼
Build
    │
    ▼
Quality Gate - Lint
    │
    ▼
Quality Gate - Tests
    │
    ▼
SUCCESS
```

## Stage 1 – Checkout

Jenkins retrieves the project source code from the GitHub `main` branch.

## Stage 2 – Install Dependencies

Jenkins creates a Python 3.12 virtual environment:

```bash
/opt/homebrew/bin/python3.12 -m venv venv
```

The dependencies are then installed from:

```text
requirements.txt
```

## Stage 3 – Build

The application is syntax-checked using:

```bash
./venv/bin/python -m py_compile app.py
```

## Stage 4 – Quality Gate – Lint

Flake8 is executed:

```bash
./venv/bin/flake8 app.py
```

## Stage 5 – Quality Gate – Tests

Pytest executes the complete automated test suite:

```bash
./venv/bin/pytest -v --junitxml=test-results.xml
```

The generated JUnit XML report is then published by Jenkins.

## Jenkins Validation

The Jenkins pipeline has successfully completed all quality-gate stages:

```text
Build                  PASSED
Flake8                 PASSED
Pytest                 PASSED
Automated Tests        14/14 PASSED
Jenkins Quality Gate   PASSED
```

The successful pipeline confirms that the application can be checked out from GitHub, dependencies can be installed, the application can be compiled, linting passes, and all automated tests pass.

---

# GitHub Actions CI/CD

The GitHub Actions workflow is located at:

```text
.github/workflows/main.yml
```

The workflow is triggered automatically on:

```yaml
push:
pull_request:
```

## GitHub Actions Pipeline

The workflow contains three jobs:

```text
Build and Lint
      │
      ▼
Docker Image Assembly
      │
      ▼
Automated Testing
```

---

## Job 1 – Build and Lint

The job:

1. Checks out the source code.
2. Sets up Python 3.12.
3. Installs project dependencies.
4. Compiles `app.py`.
5. Runs Flake8.

The application must pass these checks before the next job runs.

---

## Job 2 – Docker Image Assembly

The workflow builds the Docker image:

```bash
docker build -t aceest-fitness:${{ github.sha }} .
```

The Git commit SHA is used as the Docker image tag so that each build has a unique identifier.

---

## Job 3 – Automated Testing

The Docker image is built and Pytest is executed inside the container:

```bash
docker run --rm aceest-fitness:${{ github.sha }} pytest -v
```

This validates that the automated test suite can execute successfully within the containerized application environment.

---

# DevOps Workflow

The overall project workflow is:

```text
                    Developer
                        │
                        ▼
                Local Development
                        │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼
           Pytest               Flake8
              │                   │
              └─────────┬─────────┘
                        │
                        ▼
                    Git Commit
                        │
                        ▼
                   GitHub Main
                        │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼
       GitHub Actions          Jenkins
              │                   │
              ▼                   ▼
        Build & Lint          Checkout
              │                   │
              ▼                   ▼
         Docker Build        Dependencies
              │                   │
              ▼                   ▼
       Container Tests          Build
              │                   │
              │                   ▼
              │                Flake8
              │                   │
              │                   ▼
              │                Pytest
              │                   │
              └─────────┬─────────┘
                        │
                        ▼
                Quality Validation
                        │
                        ▼
                      PASS
```

---

# Version Control

Git is used for source-code management and GitHub is used as the remote repository.

The project uses meaningful commits to document application and CI/CD development.

Examples of project commits include:

```text
feat: add ACEest Fitness Flask application
ci: add Jenkins and GitHub Actions pipelines
ci: implement GitHub Actions pipeline
ci: implement Jenkins quality gate
fix: use Python 3.12 for Jenkins
```

The validated implementation is maintained on the:

```text
main
```

branch.

---

# Security and Quality Practices

The project follows several basic software engineering practices:

- Dependencies are version-pinned in `requirements.txt`.
- Environment files and local secrets are excluded through `.gitignore`.
- SQLite database files are excluded from source control.
- Development-only files are excluded from Docker build contexts.
- The Docker container runs using a dedicated non-root user.
- A Docker health check is configured.
- Application syntax is validated before automated tests.
- Flake8 is used as an automated code-quality gate.
- Automated tests are executed through CI pipelines.
- Jenkins publishes the Pytest JUnit test report.
- Temporary databases are used during automated testing.

---

# Database

The application uses **SQLite** for lightweight data persistence.

The default database file is:

```text
aceest_fitness.db
```

The application automatically initializes the required database tables when it starts.

The database contains tables for:

- Clients
- Progress
- Workouts

The automated test suite uses an isolated temporary database to prevent test data from affecting the development database.

---

# Development Workflow

A typical development workflow is:

```text
1. Develop or modify the application
        ↓
2. Run Pytest locally
        ↓
3. Run Flake8 locally
        ↓
4. Validate application syntax
        ↓
5. Commit changes using Git
        ↓
6. Push changes to GitHub
        ↓
7. GitHub Actions validates the change
        ↓
8. Jenkins performs the quality gate
        ↓
9. Successful CI validation
```

Recommended local validation before pushing changes:

```bash
python -m py_compile app.py
flake8 app.py
pytest -v
```

---

# Assignment Coverage

| Assignment Requirement | Implementation | Status |
|---|---|---|
| Application Development | Flask fitness management application | ✅ |
| Modularization | Application and test separation | ✅ |
| Git/GitHub | Git repository with public GitHub repository | ✅ |
| Unit Testing | Pytest automated test suite | ✅ |
| Docker | Dockerfile and container configuration | ✅ |
| Jenkins Build | Jenkins pipeline | ✅ |
| Jenkins Quality Gate | Build, Flake8 and Pytest | ✅ |
| GitHub Actions | Automated CI/CD workflow | ✅ |
| Docker Image Assembly | GitHub Actions Docker build | ✅ |
| Container Testing | Pytest executed inside Docker | ✅ |
| Documentation | Structured project README | ✅ |

---

# Project Information

**Project:** ACEest Fitness & Gym – DevOps CI/CD

**Course:** Introduction to DEVOPS (Merged - CSIZG514/SEZG514)

**Semester:** S1-26

**Primary Technologies:**

```text
Python
Flask
SQLite
Pytest
Flake8
Docker
Jenkins
GitHub Actions
Git
GitHub
```

**GitHub Repository:**

https://github.com/2026ht66052/ACEest-Fitness-DevOps

---

## Conclusion

The ACEest Fitness & Gym project demonstrates the integration of application development with core DevOps practices.

The implementation provides:

- A Flask-based fitness management application
- Automated unit and API testing
- Code-quality validation
- Docker containerization
- Jenkins-based CI quality gates
- GitHub Actions-based CI/CD
- Automated container testing
- Git-based version control
- Structured engineering documentation

The project establishes a repeatable workflow in which application changes can be developed, tested, validated, containerized, and integrated through automated DevOps pipelines.
```
