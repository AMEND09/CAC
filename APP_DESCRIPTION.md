# ServeSync — Application Description

## Overview
ServeSync is a Django-based platform that connects JCPS (Jefferson County Public Schools) students with verified organizations offering volunteer opportunities. The app enables students to discover and sign up for volunteer events, track hours and impact, earn badges, and manage profiles. Organizations can register (pending admin verification), post volunteer opportunities, review and manage signups, and credit volunteers for completed work.

This repository appears to be a student-built project (author: Rahbe Abass) intended for local deployment and demonstration. It uses SQLite by default for development and includes email configuration for sending verification codes and notifications.

## Key Features
- Student and organization registration flows (students require a JCPS email address).
- Email verification for student sign-up via a 6-digit code.
- Organization registration with document upload and admin review workflow (PendingOrganization model).
- Organizations can create and manage volunteer opportunities (VolunteerOpportunities model).
- Students can browse listings, sign up, and track signups and completions.
- Dashboard and stats pages for students and organizations (badges, goals, and aggregated metrics).
- Signup acceptance/decline workflow and crediting hours (Completion model).
- Notifications stored in a `Notification` model (in-app notifications via database records).
- PDF export of signup details (uses ReportLab).
- Basic search, filtering, and pagination for listings and signups.

## Tech Stack
- Python 3.x
- Django (project uses Django 5.x in `requirements.txt`)
- SQLite (default DB in `servesync/settings.py`) for development
- ReportLab for PDF export
- Geopy for address validation (Nominatim geocoding)
- Front-end: Django templates, static CSS, JS; uses GSAP and Typed.js in the frontend

## Important Files (high-level)
- `manage.py` — Django management wrapper.
- `servesync/settings.py` — Django settings (SQLite DB, static/media config, email SMTP configured for Gmail).
- `website/models.py` — Core data models: `Organization`, `PendingOrganization`, `Student`, `VolunteerOpportunities`, `Contact`, `Notification`, `SignupRequest`, `Completion`.
- `website/views.py` — Main request handlers implementing auth flows, student/organization dashboards, listing creation, signup handling, accept/decline flows, email sending, PDF export, and utilities.
- `website/urls.py` — URL routing for the site.
- `website/templates/website/` — Collection of templates including `index.html` (home), `student.html`, `organization.html`, `create.html`, `listing.html`, `login.html`, `register.html`, etc.
- `requirements.txt` — Project Python dependencies.
- `db.sqlite3` — Prebuilt development database (if present).
- `media/` — Directory for uploaded files (organization documents, profile pictures).

## Data Models (summary)
- Organization
  - Fields: `organization_name`, `website_url`, `address`, `contact_email`, `contact_phone`, `facilitated`, `people_helped`, `opportunities_created`, `opportunities_completed`, `accepted`, `declined`, `goals`, `badge`, `next_badge`
  - Relationship: 1-to-many with `VolunteerOpportunities`

- PendingOrganization
  - Used for organization registration pending admin approval. Captures registration document and a `verification_code`.

- Student
  - Fields: `first_name`, `last_name`, `school`, `email`, `phone`, `age`, `bio`, `interests`, `profile_picture`, stats like `hours_volunteered`, `people_helped`, `opportunities_completed`, `goal_hours`, `accept`, `decline`, `applied`, `badge`, `next_badge`.

- VolunteerOpportunities
  - Fields: `title`, `description`, `address`, `time`, `skills_required`, `age_requirement`, `hours_expected`, `category`, `posted_by` (FK -> Organization), `email`.

- SignupRequest
  - Links `User` (Django auth user), `VolunteerOpportunities`, and `Organization`. Stores `status` (Pending/Accepted/Declined/Credited), `hours_volunteered`, `people_helped`, `completed`.

- Completion
  - OneToOne with `SignupRequest` and stores `hours_credited`, `people_credited`, `task_completed`.

- Contact and Notification — simple models for messages and in-app notifications.

## Views & Workflows (high-level)
- index: Displays the home page (`templates/website/index.html`) with hero, how-it-works, testimonials, FAQ and CTA.
- register -> code: Student registration stores form data in session, sends a 6-digit verification code via email, and `code` view validates it to create a Django `User` and `Student` profile.
- organization_register: Organizations upload documents; a `PendingOrganization` is saved and emails are sent to the applicant and admin address.
- login: Authenticates users and redirects to either `student` or `organization` dashboard depending on email matching `Student` or `Organization` data.
- student: Student dashboard that shows listings, recent activity, and random recommended listings.
- organization: Organization dashboard with counts of active opportunities, total volunteers, aggregated hours, and recent applications.
- create: Organizations can create `VolunteerOpportunities` — includes address validation using Geopy/Nominatim.
- signup/submit_signup: Organizations view and manage signup requests; students submit signups via `submit_signup`.
- accept/decline flow: Organization actions update `SignupRequest` status, create `Completion` objects, and create `Notification` records. Crediting updates student and organization aggregated stats.
- PDF export: Organization can export signup details to PDF using ReportLab.

## Security & Validation Notes
- Passwords are handled by Django auth for users created after verification. However, `PendingOrganization` temporarily stores a raw `password` field — this is insecure and should be refactored so the password is generated/stored hashed or an invite-based flow is used.
- The email backend is configured in `settings.py` to use a Gmail account (`servesyncinc@gmail.com`) with an app password in the repo. This is a security risk: secrets should be moved to environment variables or a secrets manager.
- `DEBUG = True` and `ALLOWED_HOSTS = ['*']` are set — make sure to change these for production.
- File uploads are stored in `media/` and served during development by Django when `DEBUG=True` (see `website/urls.py`). In production, use proper storage (S3, Google Cloud Storage, etc.) and sanitize/validate uploads.

## Setup / Run (development)
1. Create a Python 3.x virtual environment and activate it.

   PowerShell example:

   ```powershell
   python -m venv venv; .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Apply migrations (if you want a fresh DB):

   ```powershell
   python manage.py migrate
   ```

3. Create a superuser (optional):

   ```powershell
   python manage.py createsuperuser
   ```

4. Run the development server:

   ```powershell
   python manage.py runserver
   ```

5. Open http://127.0.0.1:8000/ in your browser.

Notes:
- `servesync/settings.py` configures an SMTP server. For local testing, you can use the Django console email backend by setting `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'` in `settings.py`.
- If you have an existing `db.sqlite3` in the repo, the app may be pre-populated with data; back it up before running migrations.

## Tests & Validation
- There are no automated tests present in the repository (no `tests` directory beyond the app-level `tests.py` which is empty). Adding unit tests for critical workflows (registration, signup, accept/credit flow) is recommended.

## Developer Notes & Suggested Improvements
- Move secret credentials (email password, secret key) into environment variables and update `settings.py` to read from them.
- Remove or hash the raw `password` field from `PendingOrganization` and replace it with a safer onboarding flow.
- Add input validation and stronger error handling for file uploads and external API calls (e.g., Nominatim rate limits/timeouts).
- Add automated tests (unit and integration) for the major user flows.
- Consider switching from SQLite to PostgreSQL for production and ensure migrations are consistent.
- Add rate-limiting and CSRF protections on sensitive endpoints (CSRF is enabled by default in middleware but review forms and AJAX endpoints accordingly).
- Add admin views for verifying `PendingOrganization` entries and approving organizations (current flow emails admin but does not include an explicit approval view in this code snapshot).

## Contribution Guide
- Use standard Git feature branches. Make changes in small commits with clear messages.
- Run linters and tests locally before creating PRs. Add tests for new behavior.
- Follow Django security best practices when changing auth, email, or file upload behavior.

## Maintainers / Author
- Creator indicated in templates: Rahbe Abass (GitHub: https://github.com/RahbeA). The repository README and templates contain personal contact info.

---

If you'd like, I can:
- Create a short SECURITY.md advising on secrets and deployment.
- Add a .env.example and update `settings.py` to load secrets from environment variables.
- Add basic unit tests for one or two core views (registration + signup flow).

Which of these would you like me to do next?