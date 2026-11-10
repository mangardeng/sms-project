# School Management System — Backend (Django + DRF + MySQL)

Backend implementation of the Web-Based School Management System described in
the project's Chapter 3/4 design document. Built with **Django REST
Framework** and **MySQL** (PostgreSQL is intentionally not used).

## Tech stack

- Python 3.12+, Django 5.x, Django REST Framework
- MySQL 8.x (via `mysqlclient`)
- JWT authentication (`djangorestframework-simplejwt`)
- django-cors-headers, django-filter, drf-spectacular (Swagger docs)

## Project layout

```
config/                 Django project settings, root urls, wsgi/asgi
apps/
  core/                 Shared base models (AcademicYear, Term, AuditLog), pagination, exceptions, middleware
  accounts/             Custom User model, roles, JWT login (username OR student index number), admin user mgmt
  students/             Student registration/profile, transfers
  teachers/             Teacher registration/profile
  parents/              Parent registration + the critical ParentStudent link table
  classes/              SchoolClass, Stream
  subjects/             Subject, ClassSubject (class/subject/teacher assignment)
  attendance/           Daily attendance, bulk entry, class summaries
  examinations/         Exam types, examinations, results, mark-change audit trail
  fees/                 Fee structures, payments/receipts, balance calculation
  library/              Books, borrowing/returns, fines
  notifications/        In-app notifications + role/broadcast announcements
  dashboard/            Role-based aggregated dashboard statistics
```

## Roles implemented

Administrator, Head Teacher, Registrar, Teacher, Accountant, Librarian,
Parent, Student — matching design doc section 3.3–3.4. Every endpoint
re-validates the caller's role **server-side** on every request; nothing is
trusted from the frontend (design doc 3.6).

The most important security rule — **a parent may only ever see data for
their own linked child(ren)** — is centralized in
`apps/parents/services.py::parent_owns_student()` and is used by every app
that exposes student-linked data (students, attendance, examinations, fees,
library, dashboard). See design doc sections 3.14 and 4.9.

## 1. Prerequisites

- Python 3.12+
- MySQL Server 8.x running locally or reachable over the network
- (Recommended) a virtual environment tool: `venv`, `pipenv`, or `poetry`

## 2. Create the MySQL database

```sql
CREATE DATABASE school_management_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'school_admin'@'%' IDENTIFIED BY 'change-this-password';
GRANT ALL PRIVILEGES ON school_management_db.* TO 'school_admin'@'%';
FLUSH PRIVILEGES;
```

## 3. Set up the Python environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

> `mysqlclient` needs MySQL's development headers to build. On Ubuntu/Debian:
> `sudo apt-get install default-libmysqlclient-dev build-essential pkg-config`.
> On macOS: `brew install mysql-client pkg-config` (and set `PKG_CONFIG_PATH`
> per Homebrew's instructions). On Windows, prefer a prebuilt wheel.

## 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set at minimum: `DJANGO_SECRET_KEY`, `DB_NAME`, `DB_USER`,
`DB_PASSWORD`, `DB_HOST`, `DB_PORT`.

## 5. Run migrations

```bash
python manage.py makemigrations core accounts students teachers parents classes subjects attendance examinations fees library notifications dashboard
python manage.py migrate
```

## 6. Create an administrator account

```bash
python manage.py createsuperuser
```

The custom `UserManager` automatically sets `role=admin` for superusers, so
this account can log in through the normal `/api/auth/login/` endpoint (not
just `/admin/`) and reach every admin-only API.

## 7. (Optional) Seed a starting Academic Year / Term

Several models (classes/subjects, exams, fees) reference an `AcademicYear`
and `Term`. A convenience command creates a default one:

```bash
python manage.py seed_initial_data
```

## 7b. (Optional but recommended) Seed a full demo dataset

To actually have something to log in to and click around immediately,
run the richer demo-data command. It goes through the real model layer
(same code paths as the API) to create:

- an academic year + Term 1
- 2 classes (Grade 7, Grade 8) with streams
- 5 subjects and class/subject/teacher assignments
- 3 teachers, 8 students (with auto-generated index numbers), 5 parents
  correctly linked to their children via `ParentStudent`
- one Admin, Head Teacher, Registrar, Accountant and Librarian account
- a week of attendance records
- a published midterm exam with results for every student
- fee structures and a couple of partial payments
- 5 library books and two borrowing records (one overdue)
- a welcome announcement broadcast to everyone + a sample fee reminder

```bash
python manage.py seed_demo_data
```

It is safe to re-run — existing records are detected by their natural
unique fields (username, staff ID, etc.) and skipped. Every demo account
uses the password `Password@123`; the command prints the full list of
usernames at the end (students log in with their printed index number,
e.g. `STD00001`, not a username).

## 8. Run the development server

```bash
python manage.py runserver
```

API root: `http://127.0.0.1:8000/api/`
Interactive API docs (Swagger UI): `http://127.0.0.1:8000/api/docs/`
Django admin: `http://127.0.0.1:8000/admin/`

## Authentication flow (matches design doc 3.5–3.7)

```
POST /api/auth/login/
{
  "username": "teacher.john",      // OR a student's index number, e.g. "STD00125"
  "password": "..."
}

-> { "access": "...", "refresh": "...", "user": {...}, "dashboard": "/dashboard/teacher" }
```

Send the access token on every subsequent request:

```
Authorization: Bearer <access_token>
```

- `POST /api/auth/token/refresh/` — refresh an expired access token
- `POST /api/auth/logout/` — blacklists the refresh token
- `GET/PATCH /api/auth/me/` — current user's own profile
- `POST /api/auth/change-password/` — self-service password change
- `/api/auth/users/` — admin-only account management (create/activate/deactivate/reset-password/unlock)

## Key API groups

| Prefix                     | Purpose                                             |
|-----------------------------|------------------------------------------------------|
| `/api/academic-years/`        | Academic years (Admin-managed, readable by all)     |
| `/api/terms/`                  | Terms within an academic year (Admin-managed, readable by all) |
| `/api/students/`            | Student CRUD, `/transfer/`, `/transfer-history/`, `/me/` |
| `/api/teachers/`             | Teacher CRUD, `/me/`                                |
| `/api/parents/`              | Parent CRUD, `/api/parents/links/` (parent<->student) |
| `/api/classes/`               | SchoolClass, `/api/classes/streams/`                |
| `/api/subjects/`              | Subject, `/api/subjects/assignments/` (ClassSubject) |
| `/api/attendance/`            | Attendance CRUD, `/bulk-record/`, `/class-summary/`  |
| `/api/examinations/`          | Examination CRUD, `/publish/`, `/results/`, `/results/bulk-entry/` |
| `/api/fees/`                  | `/structures/`, `/payments/`, `/balance/?student=<id>` |
| `/api/library/`               | Book CRUD, `/borrowing/`, `/borrowing/{id}/mark_returned/`, `/borrowing/overdue/` |
| `/api/notifications/`         | Own notifications, `/mark_read/`, `/mark-all-read/`, `/broadcast/` |
| `/api/dashboard/`             | Role-based aggregated statistics (single endpoint, payload shaped by role) |

## Security notes implemented per the design doc

- **3.14 Parent-Student Data Security** — every parent-facing queryset is
  filtered by the `ParentStudent` link table; object-level permissions
  re-check it again so a guessed/incremented URL id cannot leak another
  student's data.
- **3.4.4 Teacher scope** — teachers are restricted to classes they are
  assigned to via `ClassSubject` (`apps/teachers/services.py`).
- **3.10.8 Exam mark audit trail** — every mark change writes an
  `ExamMarkAuditLog` row.
- **3.15 Security requirements** — password hashing (Django default,
  PBKDF2), JWT auth with rotation + blacklist, failed-login lockout after 5
  attempts, `AuditLog` for create/update/delete/login/access-denied events,
  CORS restricted to configured origins, DRF throttling on login.

## Next steps for a full production deployment

- Add Celery + Redis for async email/SMS delivery of `Notification` rows.
- Add automated tests (pytest-django) mirroring the design doc's Chapter 4
  test plan (4.13–4.19): authentication, authorization, parent isolation,
  functional, security tests.
- Put this behind Nginx + Gunicorn, serve the React frontend separately, and
  terminate TLS at Nginx (design doc 4.20 deployment diagram).
- Wire up `django-storages` for S3-compatible media storage in production
  instead of local `MEDIA_ROOT`.

## Examination grading and automatic term results

* **Grade scale** – Examinations → *Grade scale* (administrator). Default: A 80+, B 70+, C 60+, D 50+, E 40+, F below. Changing it re-grades every mark.
* **Exam types** – each type has a *Counts as* setting (Midterm / End of term / Other) and a *Weight*. Example: Midterm 40, End of term 60.
* **Marks entry** – after an exam is created, *Enter marks* shows each student's percentage and grade live, rejects marks above the maximum, and shows class average/highest/lowest.
* **Automatic computation** – as soon as midterm or end-of-term marks are saved, the system builds each student's subject result (weighted midterm + end of term; provisional until end-of-term marks exist), subject grade and subject position, then the overall total, average, grade and class position. See *Examinations → Term results*.
* Students and parents see term results only after the examinations are published.
* After upgrading an existing database run: `python manage.py migrate` then `python manage.py recompute_results`.
* Tests: `python manage.py test apps.examinations.tests`
* **Sample data:** `python manage.py generate_sample_results [--class "Grade 7"] [--publish] [--seed 1]` creates Midterm (out of 40) and End-of-term (out of 60) exams with random marks for every active student, then calculates all subject totals, grades and class positions. Re-running it overwrites those marks.
* **If a final percentage is missing:** the exam type must count as *Midterm* or *End of term* (Examination types → "Counts as"). Types named like "Mid Term" or "End of Term" are detected automatically; the Term results tab warns about anything left out.
* **How marks combine (current rule):** Midterm marks + End-of-term marks are simply added, like the school report card. Midterm is marked out of 40 and End of term out of 60 (the exam type's "Usually marked out of"; each exam also has its own "Out of" field), so 36 + 56 = 92 out of 100 = 92%, then graded from the grade scale. Weights are no longer used. If a subject's midterm + end-of-term "out of" do not add up to 100 the Term results tab warns you.
* **Examination card:** Term results → click a student (or the student/parent Examinations page) shows the end-of-term report card and prints it on A4. Its layout is in `frontend/src/utils/reportCard.js`.

## Subject results, corrections, and finance (latest update)

**Examinations**
* *Examinations → Subject results*: the subject teacher (or an administrator) picks class + subject + term and types each student's **midterm** and **end-of-term** marks (each exam's "out of" is set at the top of its column). Total, percentage, grade, remark and positions are calculated automatically; the teacher may also type a remark of their own, which replaces the automatic one on the report card.
* **Mistakes can be fixed in the app** – by the subject teacher and administrators only – even after results are published. For published results a reason is required; the old and new marks are kept in the audit trail. Teachers who do not teach that subject cannot change its marks. Teachers are linked to subjects through *Class subjects* (the teacher assigned to a subject in a class).

**Fees and finance** (Fees page)
* **Carry forward** – at the start of a term pick the term that ended and the new term; unpaid balances are added to the new term's account (re-running refreshes the amounts; rows can be adjusted or removed).
* **Payment corrections (accountant only)** – *Correct* (amount, method, date, student, fee, sponsor; a reason is required), *Void* (for payments entered by mistake – kept for the record but not counted) and *History*. Payments are never deleted.
* **Sponsorship** – record sponsors and which students they support (full fees, a percentage, or a fixed amount per term, for all or specific terms/years). Mark a payment as paid by a sponsor. The student account shows the sponsor's share and the family's share, and a sponsor report shows expected / paid / outstanding per sponsor.
* **Expenses, other income, staff salaries** – record them; *Generate payroll* creates the month's pay lines for all staff (copying last month's amounts) and each can be marked paid.
* **Income & expenditure** – generate the statement for any period (fees + other income against expenses + salaries paid), month by month, plus a list of students with unpaid fees. All can be printed.
* Access: Administrator and Accountant have full access to finance; Head Teacher can view; parents/students only see their own account (fees, carried-forward balance and sponsor share).
* Run `python manage.py migrate` after upgrading. Tests: `python manage.py test apps.examinations.tests apps.fees.tests`.
