# SkillBoost — Project Overview
Draft · 5 Nov 2026

## Why this project exists
SkillBoost is a backend API for an online learning platform: staff publish courses, students enroll, and an admin controls who gets access.

It solves two practical problems. Access must be limited to approved people, and a course with limited seats must never be oversold when many students enroll at once.

This doc is written before any code. It fixes the purpose, scope, and future direction so the sprint backlog and design doc can trace back to it. The project is also a portfolio piece for Python backend roles, built the way a small industry team would build it (Agile, layered code, tested at every level).

## Goals
The build has to deliver a working, secure API and, just as much, show how it was engineered.

**Product goals**

- Only admin-approved users can log in and use the platform
- Staff manage their own courses; students enroll and drop
- Enrollment respects seat limits, even under concurrent requests

**Portfolio goals**

- Clean layered structure: routes (controller), services (business rules), models (data)
- Tests at unit, integration, and end-to-end level, running in CI
- A visible Agile trail on GitHub: issues, board, PRs, sprint notes
- Every design choice is something the author can explain in an interview

## Users and roles
There are three roles. Student and staff accounts are self-registered but stay `pending` until an admin approves them.

| Role | How they get an account | What they can do |
|---|---|---|
| Student | Self-registers, then waits for approval | Browse courses, enroll, drop, view own enrollments |
| Staff | Self-registers, then waits for approval | Create, edit, and delete own courses; set seat capacity |
| Admin | Created by CLI command (`flask create-admin`), never by registration | View pending users and approve them |

## Features (MVP)
The MVP is seven user stories plus two rules that apply everywhere: role-based access and validated input with consistent JSON errors.

| ID | Feature | Who | Key rule |
|---|---|---|---|
| US1 | Register | Visitor | Account starts `pending`; duplicate email returns 409; missing field returns 400 |
| US2 | Admin approval | Admin | Pending users cannot log in until approved; non-admin gets 403 |
| US3 | Login | Approved user | Returns a JWT valid for 1 hour; wrong password returns 401 |
| US4 | Manage courses | Staff | Only the course owner can edit or delete; each course has a seat capacity |
| US5 | Browse courses | Any logged-in user | No token returns 401 |
| US6 | Enroll and drop | Student | Duplicate returns 409; full course returns 409; staff gets 403 |
| US7 | My enrollments | Student | Returns only the caller's own enrollments |

**Capacity-safe enrollment (part of US4 and US6).** Each course has a seat limit. The enrollment check locks the course row (`SELECT ... FOR UPDATE`), so two students racing for the last seat cannot both succeed. A concurrency test on MySQL proves it.

**Production basics (small items, built alongside the stories)**

- Pagination, filtering, and sorting on the course list
- Security basics: bcrypt password hashing, login rate limit, secrets only in environment variables, CORS config
- Structured logging with a request ID, and one consistent JSON error format
- Audit log table recording who approved whom, and when
- Indexes on foreign keys, with an `EXPLAIN` note in the README

**Delivery and presentation**

- Docker Compose (app + MySQL), so `docker compose up` runs everything
- README as the landing page: one-line pitch, CI badge, Swagger screenshot, ERD, API table, design trade-offs, and a section on capacity-safe enrollment (problem, approach, proof)
- Coverage badge with an 80% target (assumed), ruff pre-commit, and type hints
- Optional: live deploy with demo logins (check current free hosting options before choosing one)

## Out of scope
These are deliberately left out of the MVP to keep it simple and finishable. Each is listed under Future work in the README.

- Waitlist and auto-promotion when a seat frees up (proposed for Sprint 5, after the MVP)
- Real-time messaging
- Redis caching
- Refresh tokens and forced logout (a token stays valid until it expires)
- Frontend, file uploads, certificates, notifications

## Future scope
The MVP is designed so each of these can be added later without reworking the core. Grouping is a proposal, not a commitment.

**Next (builds directly on the MVP)**

- Waitlist with auto-promotion when a student drops (proposed as Sprint 5)
- Load test with Locust on the enroll endpoint, with results in the README
- Assessments and results

**Later**

- Refresh tokens and token revocation
- Redis cache on the course list
- Notifications for approval and enrollment events
- Admin reporting dashboard

**Stretch**

- Real-time messaging between users
- Class and advisor structure with advisor-only progress views
- Completion certificates
- Frontend client

## Decisions so far
Most decisions are confirmed; the tech stack and the production extras are still assumptions and may change.

| Area | Decision | Status |
|---|---|---|
| Stack | Flask, SQLAlchemy (ORM), MySQL, pytest | Assumed |
| Code structure | MVC-style: routes (controller), services (business rules), models (data). No View layer, since the API returns JSON | Confirmed |
| Auth | PyJWT, access token only, 1-hour expiry, `token_required` and `role_required` decorators | Confirmed |
| Admin creation | CLI command, never via registration | Confirmed |
| Capacity | Seat limit per course in the MVP; waitlist excluded | Confirmed |
| Test database | MySQL for all tests (separate `skillboost_test` locally, service container in CI), because row locking differs on SQLite | Confirmed |
| Process | Agile-lite: GitHub Issues and Projects, one branch and PR per issue, 1-week sprints that end when their stories are Done | Confirmed |
| Production extras | bcrypt hashing, login rate limit, structured logging, audit log, Docker Compose, 80% coverage target, ruff pre-commit | Assumed |

## Success criteria
The project is done when a stranger can clone it, run it, and verify every claim in this doc.

- A fresh clone runs with `docker compose up` or the README steps, and `pytest` is green locally and in CI
- Every acceptance criterion of US1 to US7 is a passing test
- A concurrency test fires parallel enroll requests for the last seat and exactly one succeeds
- The course list supports pagination, filtering, and sorting; errors share one JSON format; passwords are hashed with bcrypt and login is rate-limited
- A seed script loads sample courses and users
- API docs (Swagger/OpenAPI) are reachable
- Coverage is at or above 80% (assumed target), with a coverage badge and ruff pre-commit
- README has a CI badge, Swagger screenshot, ERD, API table, design trade-offs, a capacity-enrollment section (problem, approach, proof), and a Future work section
- The GitHub board, issues, PRs, and sprint retros show the Agile trail
- Optional: live deploy with demo logins
