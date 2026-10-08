# ACEest Fitness & Gym – DevOps CI/CD

A Flask-based fitness and gym management application developed as part of the **Introduction to DEVOPS (Merged - CSIZG514/SEZG514)** assignment.

The project demonstrates a complete DevOps workflow using **Git, GitHub, Pytest, Docker, Jenkins, and GitHub Actions**. The application provides REST APIs for managing fitness clients, fitness programs, progress tracking, and workout records.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Objectives](#objectives)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local Setup](#local-setup)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Docker](#docker)
- [Jenkins CI Pipeline](#jenkins-ci-pipeline)
- [GitHub Actions CI/CD](#github-actions-cicd)
- [Version Control](#version-control)
- [DevOps Workflow](#devops-workflow)
- [Security and Quality Practices](#security-and-quality-practices)
- [Assignment Coverage](#assignment-coverage)

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


