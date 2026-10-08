ACEest Fitness & Gym – DevOps CI/CD
A Flask-based fitness and gym management application developed as part of the Introduction to DevOps assignment. The project demonstrates a complete development and CI/CD workflow using Git, GitHub, Pytest, Docker, Jenkins, and GitHub Actions.
The application provides REST APIs for managing fitness clients, workout programs, progress tracking, and workout records. Automated quality gates validate the application before changes are considered ready.
📌 Project Overview
ACEest Fitness & Gym is a lightweight fitness management application that allows gym/fitness administrators to:
- Manage fitness clients
- Assign fitness programs
- Calculate recommended daily calories
- Track client progress and adherence
- Record workouts
- Retrieve client and workout information
- Validate application health through a dedicated health endpoint
The project follows a DevOps-oriented workflow where source code changes are validated through automated testing, linting, build checks, containerization, and CI/CD pipelines.
🎯 Project Objectives
The project demonstrates the following DevOps practices:
1. Application Development & Modularization
   - Develop a Flask-based web application.
   - Separate application logic from automated tests.
   - Use SQLite for lightweight data persistence.
2. Version Control
   - Maintain the project using Git.
   - Host the source code in a public GitHub repository.
   - Use meaningful commits and the main branch.
3. Automated Testing
   - Implement unit and API tests using Pytest.
   - Validate successful and invalid API operations.
   - Generate JUnit-compatible test reports.
4. Containerization
   - Package the application using Docker.
   - Use a lightweight Python base image.
   - Run the application using a non-root container user.
5. Continuous Integration
   - Use Jenkins for build, lint, and test quality gates.
   - Use GitHub Actions for automated CI/CD validation.
🛠️ Technology Stack
Technology	Purpose
Python 3.12	Application and CI runtime
Flask 3.1.3	Web application framework
SQLite	Application database
Pytest 9.1.1	Automated testing
pytest-flask	Flask testing support
Flake8 7.4.1	Code quality and linting
Docker	Application containerization
Git	Version control
GitHub	Source code repository
Jenkins	CI quality gate
GitHub Actions	Automated CI/CD pipeline


📁 Project Structure
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

Key Files
File	Description
app.py	Main Flask application and API implementation
tests/test_app.py	Automated Pytest test suite
requirements.txt	Python dependencies
pytest.ini	Pytest configuration
Dockerfile	Container build definition
.dockerignore	Files excluded from Docker build context
.gitignore	Files excluded from Git
Jenkinsfile	Jenkins CI pipeline definition
.github/workflows/main.yml	GitHub Actions CI/CD workflow
README.md	Project documentation


🚀 Application Features
Client Management
The application supports:
- Creating clients
- Retrieving all clients
- Retrieving an individual client
- Validating client information
- Preventing duplicate client records
Each client can contain information such as:
- Name
- Age
- Height
- Weight
- Fitness program
- Recommended calories
- Target weight
- Adherence
- Membership information
🏋️ Fitness Programs
The application currently provides three predefined programs:
Program	Description
Fat Loss	Program focused on reducing body weight
Muscle Gain	Program focused on muscle development
Beginner	General program for new fitness participants


Each program has an associated calorie calculation factor.
📈 Progress Tracking
Client progress can be recorded by:
- Week
- Adherence percentage
- Client ID
Adherence values are validated to ensure they remain within:
0 – 100%

🏃 Workout Tracking
The application allows workouts to be recorded against individual clients.
Workout information includes:
- Date
- Workout type
- Duration
- Notes
🔌 REST API
The Flask application exposes the following endpoints.
Application Status
GET /
Returns basic application information.
Example:
curl http://127.0.0.1:5000/

Health Check
GET /health
Used to verify that the application is running correctly.
Example:
curl http://127.0.0.1:5000/health

This endpoint is also used by the Docker container health check.
Fitness Programs
GET /programs
Returns the available fitness programs.
Example:
curl http://127.0.0.1:5000/programs

Client Management
GET /clients
Returns all clients.
curl http://127.0.0.1:5000/clients

POST /clients
Creates a new client.
Example:
curl -X POST http://127.0.0.1:5000/clients \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John",
    "age": 25,
    "height": 175,
    "weight": 70,
    "program": "Beginner"
  }'

GET /clients/<client_id>
Returns details for a specific client.
Example:
curl http://127.0.0.1:5000/clients/1

Progress Tracking
GET /clients/<client_id>/progress
Retrieves progress information for a client.
curl http://127.0.0.1:5000/clients/1/progress

POST /clients/<client_id>/progress
Adds weekly progress information.
Example:
curl -X POST http://127.0.0.1:5000/clients/1/progress \
  -H "Content-Type: application/json" \
  -d '{
    "week": 1,
    "adherence": 90
  }'

Workout Tracking
GET /clients/<client_id>/workouts
Retrieves workouts associated with a client.
curl http://127.0.0.1:5000/clients/1/workouts

POST /clients/<client_id>/workouts
Adds a workout record.
Example:
curl -X POST http://127.0.0.1:5000/clients/1/workouts \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-10-08",
    "type": "Strength Training",
    "duration": 60,
    "notes": "Upper body workout"
  }'

💻 Local Development Setup
Prerequisites
The following tools are required:
- Python 3.12+
- Git
- pip
- Optional: Docker
Verify Python:
python3 --version

Verify Git:
git --version

1. Clone the Repository
Clone the project repository and enter the project directory:
git clone <repository-url>
cd ACEest-Fitness-DevOps

2. Create a Virtual Environment
python3.12 -m venv venv

Activate the environment on macOS/Linux:
source venv/bin/activate

On Windows:
venv\Scripts\activate

3. Install Dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

4. Run the Application
python app.py

The application starts on:
http://127.0.0.1:5000

Verify the application:
curl http://127.0.0.1:5000/health

🧪 Running Automated Tests
The project uses Pytest for automated testing.
Run all tests:
pytest -v

The current test suite contains 14 automated tests covering:
- Application home endpoint
- Health endpoint
- Fitness programs
- Client creation
- Required field validation
- Program validation
- Weight validation
- Client retrieval
- Non-existent clients
- Progress creation
- Progress validation
- Progress retrieval
- Workout creation
- Workout retrieval
Expected result:
14 passed

🔍 Code Quality
Flake8 is used as the project's linting and quality gate.
Run:
flake8 app.py

The CI pipelines execute this check automatically.
The application is also compiled before testing:
python -m py_compile app.py

This provides an additional validation step to detect Python syntax errors.
🐳 Docker
The application includes a Dockerfile for containerization.
Build the Docker Image
docker build -t aceest-fitness .

Run the Container
docker run --rm -p 5000:5000 aceest-fitness

The application can then be accessed at:
http://127.0.0.1:5000

Verify the health endpoint:
curl http://127.0.0.1:5000/health

Docker Design
The Docker image uses:
- A lightweight Python base image
- pip --no-cache-dir to reduce unnecessary image data
- A dedicated non-root appuser
- A Docker HEALTHCHECK
- .dockerignore to exclude unnecessary files
The container therefore avoids running the Flask application as the root user.
🔄 CI/CD Pipeline
The project implements CI/CD using both Jenkins and GitHub Actions.
The overall workflow is:
             Developer
                 │
                 ▼
          Git Local Repository
                 │
                 ▼
              GitHub
                 │
        ┌────────┴─────────┐
        │                  │
        ▼                  ▼
 GitHub Actions          Jenkins
        │                  │
        ▼                  ▼
 Build & Lint        Checkout Code
        │                  │
        ▼                  ▼
 Docker Build        Install Dependencies
        │                  │
        ▼                  ▼
 Container Tests     Application Build
        │                  │
        ▼                  ▼
     SUCCESS          Quality Gate
                           │
                           ▼
                        SUCCESS

⚙️ GitHub Actions
The GitHub Actions workflow is located at:
.github/workflows/main.yml

The workflow is triggered on:
push:
pull_request:

GitHub Actions Stages
1. Build and Lint
The pipeline:
- Checks out the repository
- Sets up Python 3.12
- Installs dependencies
- Compiles app.py
- Runs Flake8
2. Docker Image Assembly
The pipeline builds the Docker image:
docker build -t aceest-fitness:${{ github.sha }} .

3. Automated Testing
The Docker image is built for testing and Pytest is executed inside the container:
docker run --rm aceest-fitness:${{ github.sha }} pytest -v

The stages use dependencies between jobs so that later stages execute only after the required earlier stage succeeds.
🔧 Jenkins CI Pipeline
The Jenkins pipeline is defined in:
Jenkinsfile

Jenkins is configured to retrieve the project directly from the GitHub repository and use the Jenkinsfile stored in source control.
Jenkins Stages
Checkout
   ↓
Install Dependencies
   ↓
Build
   ↓
Quality Gate - Lint
   ↓
Quality Gate - Tests

Checkout
Jenkins pulls the latest code from the main branch.
Install Dependencies
The pipeline creates a Python 3.12 virtual environment and installs the dependencies from:
requirements.txt

Build
The application is syntax-checked using:
python -m py_compile app.py

Quality Gate – Lint
Flake8 validates the application code.
Quality Gate – Tests
Pytest executes the complete automated test suite and generates a JUnit XML test report.
✅ Jenkins Validation Result
The Jenkins pipeline has been successfully executed against the GitHub repository.
The successful pipeline validated:
Python 3.12.13
Flask 3.1.3
Pytest 9.1.1
Flake8 7.4.1

The automated test stage completed with:
14 passed

and the Jenkins pipeline completed successfully.
🌿 Version Control
Git is used for source-code management.
The repository follows a meaningful commit-based workflow. Examples of project commits include:
feat: add ACEest Fitness Flask application
ci: add Jenkins and GitHub Actions pipelines
ci: implement GitHub Actions pipeline
ci: implement Jenkins quality gate
fix: use Python 3.12 for Jenkins

The main branch contains the validated project implementation.
🔐 Security and Quality Considerations
The project follows several basic engineering practices:
- Dependencies are explicitly version-pinned.
- Secrets and environment files are excluded through .gitignore.
- Database files are excluded from version control.
- Docker excludes unnecessary development files through .dockerignore.
- The Docker container runs the application as a non-root user.
- Automated tests run before the CI pipeline is considered successful.
- Flake8 is used as an automated code-quality gate.
- Application syntax is validated before the test stage.
🗄️ Database
The application uses SQLite for lightweight data persistence.
The database is created automatically when the Flask application starts.
The default database file is:
aceest_fitness.db

The database contains tables for:
- Clients
- Progress
- Workouts
For automated testing, a temporary test database is created so that tests do not modify the development database.
🧑‍💻 Development Workflow
A typical development workflow is:
1. Create or modify application code
        ↓
2. Run local tests
        ↓
3. Run Flake8
        ↓
4. Commit changes using Git
        ↓
5. Push changes to GitHub
        ↓
6. GitHub Actions validates the change
        ↓
7. Jenkins performs the quality gate
        ↓
8. Successful build confirms the change

Recommended local validation before pushing:
python -m py_compile app.py
flake8 app.py
pytest -v

📋 DevOps Implementation Summary
DevOps Area	Implementation
Application	Flask REST API
Database	SQLite
Version Control	Git
Remote Repository	GitHub
Automated Testing	Pytest
Code Quality	Flake8
Build Validation	Python compilation
Containerization	Docker
CI Pipeline	GitHub Actions
CI Quality Gate	Jenkins
Test Reporting	JUnit XML
Container Testing	Pytest executed inside Docker
Branch	main


🎓 Assignment Coverage
This project implements the major requirements of the Introduction to DevOps assignment:
- ✅ Application development using Flask
- ✅ Modular application and test structure
- ✅ Git repository management
- ✅ Public GitHub repository
- ✅ Automated Pytest test suite
- ✅ Docker containerization
- ✅ Jenkins build and quality gate
- ✅ GitHub Actions workflow
- ✅ Docker image assembly through CI
- ✅ Automated testing inside the Docker container
- ✅ Professional project documentation
👤 Project
ACEest Fitness & Gym
Developed as part of:
Introduction to DEVOPS (Merged - CSIZG514/SEZG514)
Semester: S1-26
