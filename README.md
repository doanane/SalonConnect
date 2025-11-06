# Salon Connect API

A complete backend API for a salon booking platform that connects customers with salons. This README is written as plain explanations and reference tables — no source code is shown here. It explains what each part of the codebase does, how the API behaves, and how to operate, extend, and deploy the system.

---

## Quick overview

Salon Connect provides:
- User management (customers, vendors, admins) with JWT authentication and password reset flows.
- Salon discovery and management with search, filters, reviews, and featured listings.
- A booking system supporting multi-service bookings and booking lifecycle states.
- Payment integration with Paystack (initiate, verify, webhooks).
- Vendor dashboard features (revenue insights, bookings analytics).
- File storage for images (Cloudinary) and email support for password resets.

Live deployments (examples)
- Primary: https://salonconnect-qzne.onrender.com
- Docs (Swagger): https://salonconnect-qzne.onrender.com/docs
- Health: https://salonconnect-qzne.onrender.com/health

---

## Key features (short)

- Role-based access control: Customer, Vendor, Admin.
- JWT Authentication: Access & Refresh tokens.
- Salon & service model with images and reviews.
- Booking lifecycle: Pending → Confirmed → Completed → Cancelled.
- Paystack integration with webhook handling and transaction verification.
- Cloudinary for file uploads (images).
- Auto-generated OpenAPI docs (Swagger / ReDoc).

---

## Architecture & technology

This section maps the architecture to the technologies used.

| Layer | Technology | Purpose / comments |
|---|---:|---|
| Web framework | FastAPI | High-performance async API framework, auto-generated OpenAPI docs |
| ASGI server | Uvicorn (recommended) | Production and development server for FastAPI |
| Database | PostgreSQL + SQLAlchemy | Relational persistence and ORM |
| Migrations | (Recommended) Alembic | For controlled schema changes in production |
| Authentication | JSON Web Tokens (JWT) | Short-lived access tokens + refresh token patterns |
| File storage | Cloudinary | Hosted file/image storage |
| Payments | Paystack | Payment gateway and webhooks |
| Email | SMTP (configurable) | Password reset and transactional emails |
| Deployment | Render.com or similar | Example deployment target in README |

---

## Project structure (conceptual)

This table explains what each top-level directory / file in the app layer is responsible for. The goal is to help contributors find logic without exposing implementation details.

| Path | Responsibility |
|---|---|
| app/main.py | Application entrypoint: mounts routers, middleware, and startup/shutdown events |
| app/database.py | Database engine and session/connection helpers |
| app/models/ | ORM models representing database tables (User, Salon, Service, Booking, Payment, etc.) |
| app/schemas/ | Pydantic request/response models used for validation and serialization |
| app/routes/ | HTTP route handlers organized by domain (auth, users, salons, bookings, payments, favorites) |
| app/services/ | Business logic and helpers reused by routes (auth, booking logic, payments, email) |
| app/core/ | Configuration, security utilities (JWT helpers), Cloudinary integration, environment loading |
| app/utils/ | Generic helpers and validators used across the codebase |
| requirements.txt | Python dependencies list |
| .env | Example environment variables for local development |

---

## Module responsibilities — detailed explanation

This table maps major modules to the behaviors you can expect from them.

| Module / File | What it does (behavioral description) |
|---|---|
| auth routes (routes/auth.py) | Handles registration, login, logout, password reset request & execution, token verify endpoints. Uses JWT for authentication and issues access/refresh tokens. |
| users routes (routes/users.py) | Returns current user profile, updates profile, returns role and user-specific dashboards for customers and vendors. Handles profile image uploads. |
| salons routes (routes/salons.py) | CRUD for salons (vendors), search, filters, featured and nearby listings, salon details, service management (list/add). |
| bookings routes (routes/bookings.py) | Create bookings (multi-service), check availability, update bookings, vendor and customer booking views, booking status transitions. |
| payments routes (routes/payments.py) | Initiate payments using Paystack, verify transactions, and accept Paystack webhook callbacks for asynchronous confirmation. |
| favorites routes (routes/favorites.py) | Add/remove/list favorite salons per user. |
| models/ (user.py, salon.py, booking.py, payment.py) | Database table definitions: relationships, indexes used for search/filters, status enums for booking/payment lifecycle. |
| services (payment_service.py) | Encapsulates payment gateway calls, verification logic, idempotency and webhook signature verification. |
| services (email.py) | Manages password reset tokens, constructs and sends email messages via configured SMTP server. |
| core/config.py | Loads configuration from environment and exposes typed config to the rest of the app. |
| core/security.py | Password hashing, token generation and parsing, permission checks for role-based guards. |
| core/cloudinary.py | Upload helpers and transformation presets for images stored on Cloudinary. |

---

## Environment variables (what each variable means)

Provide these in .env for local development or in your hosting environment (Render, Heroku, etc).

| Variable | Required? | Purpose / Notes |
|---|:---:|---|
| DEBUG | recommended | True/False to enable extra logging and dev features |
| SECRET_KEY | yes | Used for JWT signing and other security primitives — keep secret |
| DATABASE_URL | yes | PostgreSQL connection string (e.g., postgresql://user:pass@host:5432/dbname) |
| CLOUDINARY_CLOUD_NAME | yes for uploads | Cloudinary cloud name |
| CLOUDINARY_API_KEY | yes for uploads | Cloudinary API key |
| CLOUDINARY_API_SECRET | yes for uploads | Cloudinary API secret |
| EMAIL_HOST | yes if email used | SMTP host for sending emails |
| EMAIL_PORT | yes if email used | SMTP port |
| EMAIL_HOST_USER | yes if email used | SMTP username |
| EMAIL_HOST_PASSWORD | yes if email used | SMTP password or app-specific password |
| DEFAULT_FROM_EMAIL | recommended | From address for transactional emails |
| PAYSTACK_SECRET_KEY | yes for payments | Secret key for Paystack API calls |
| PAYSTACK_PUBLIC_KEY | recommended | Public key for client integrations |
| PAYSTACK_BASE_URL | recommended | Base URL for Paystack API (default: https://api.paystack.co) |
| ACCESS_TOKEN_EXPIRE_MINUTES | recommended | Access token lifetime in minutes |

---

## How to set up (high-level, non-code steps)

1. Prepare a runtime environment with Python 3.10+ and create an isolated virtual environment.
2. Install project dependencies from the provided dependency list (requirements.txt).
3. Create and populate the environment variables (.env). Ensure DATABASE_URL points to a running Postgres instance.
4. Start the database and apply migrations (recommended: use Alembic in production).
5. Start the application server (development mode should enable hot reload). Application exposes interactive API docs on /docs and health on /health.
6. Use the interactive docs to try endpoints and understand request/response shapes.

Note: exact CLI commands are intentionally not shown here; use the standard Python tooling for your environment (pip, python, uvicorn, alembic, etc.).

---

## API surface — conceptual endpoint reference

Below are grouped lists of important endpoints and what they do. They are presented as tables for quick reference.

Authentication Endpoints

| Method | Path | Purpose | Auth required |
|---:|---|---|---|
| POST | /api/users/register | Register a new user (customer, vendor, admin) | Public |
| POST | /api/users/login | Log user in and receive tokens | Public |
| POST | /api/users/forgot-password | Request a password reset link | Public |
| POST | /api/users/reset-password | Reset password using token | Public |
| POST | /api/users/change-password | Change password for authenticated user | Bearer Token |
| GET | /api/users/token/verify | Validate an access/refresh token | Bearer Token |
| POST | /api/users/logout | Invalidate user session/tokens | Bearer Token |

User Management Endpoints

| Method | Path | Purpose | Auth required |
|---:|---|---|---|
| GET | /api/users/me | Get current user info | Bearer Token |
| GET | /api/users/me/profile | Get current user's profile | Bearer Token |
| PUT | /api/users/me/profile | Update profile & image upload | Bearer Token |
| GET | /api/users/me/role | Get current user role | Bearer Token |
| GET | /api/users/customer/dashboard | Customer-specific dashboard | Bearer Token (Customer) |
| GET | /api/users/vendor/dashboard | Vendor-specific dashboard | Bearer Token (Vendor) |

Salon Discovery & Management

| Method | Path | Purpose | Auth required |
|---:|---|---|---|
| GET | /api/salons/ | List salons with filters (city, rating, services) | Optional |
| GET | /api/salons/featured | Featured salons | Optional |
| GET | /api/salons/nearby | Nearby salons based on coordinates | Optional |
| GET | /api/salons/{salon_id} | Salon detail | Optional |
| POST | /api/salons/ | Create a salon (vendors) | Bearer Token (Vendor) |
| GET | /api/salons/{salon_id}/services | List services for a salon | Public |
| POST | /api/salons/{salon_id}/services | Add a service (owner) | Bearer Token (Owner) |
| GET | /api/salons/{salon_id}/reviews | List reviews | Public |
| POST | /api/salons/{salon_id}/reviews | Create a review (customers) | Bearer Token (Customer) |

Booking Management

| Method | Path | Purpose | Auth required |
|---:|---|---|---|
| POST | /api/bookings/ | Create a booking (possibly multi-service) | Bearer Token (Customer) |
| GET | /api/bookings/ | List bookings for current user | Bearer Token |
| GET | /api/bookings/{booking_id} | Booking detail | Bearer Token |
| PUT | /api/bookings/{booking_id} | Update booking details or status | Bearer Token |
| GET | /api/bookings/vendor/bookings | List bookings for vendor | Bearer Token (Vendor) |

Payments & Webhooks

| Method | Path | Purpose | Auth required |
|---:|---|---|---|
| POST | /api/payments/initiate | Start a payment flow | Bearer Token |
| POST | /api/payments/verify | Verify a payment transaction | Bearer Token |
| GET | /api/payments/{payment_id} | Get payment details | Bearer Token |
| POST | /api/payments/webhook/paystack | Endpoint for Paystack webhook events | Paystack Signature |

Favorites

| Method | Path | Purpose | Auth required |
|---:|---|---|---|
| GET | /api/users/favorites | List favorite salons for user | Bearer Token |
| POST | /api/users/favorites/{salon_id} | Add a salon to favorites | Bearer Token |
| DELETE | /api/users/favorites/{salon_id} | Remove a salon from favorites | Bearer Token |

Authentication notes:
- Use Authorization: Bearer <access_token> header for protected endpoints.
- Tokens: short-lived Access Token and longer-lived Refresh Token patterns are supported.

---

## Data models — conceptual summary

These database models represent the primary domain entities. Each model maps to a relational table and includes relationships (foreign keys) where needed.

| Model | Purpose |
|---|---|
| User | Core identity record (email, password hash, role, last login metadata) |
| UserProfile | Extended profile info: first_name, last_name, phone, bio, profile_image_url |
| PasswordReset | One-time tokens for password reset workflow |
| Salon | Salon entity: name, address, coordinates, owner reference, metadata |
| Service | Salon services: name, description, duration, price, salon reference |
| SalonImage | Image references for a salon (Cloudinary URLs) |
| Review | Customer reviews: rating, text, user reference, salon reference |
| Booking | Booking master record: user, salon, date/time, status enum |
| BookingItem | Individual service entries within a booking (service, price, duration) |
| Payment | Payment transactions: gateway id, status, amount, booking reference |

---

## Testing & validation

- The application exposes interactive API documentation (Swagger UI) — use that to review and exercise endpoints and sample payload shapes.
- Validate major flows manually first (registration → login → create booking → payment) before automating tests.
- Add unit tests around service layer functions (business logic), and integration tests around critical routes, especially payment webhook handling and booking lifecycle transitions.
- Use staging credentials for third-party services (Cloudinary, Paystack, SMTP) during tests to avoid accidental production transactions.

---

## Deployment guidance (high level)

Recommended host: Render.com (or similar)
- Connect the GitHub repository to Render and set environment variables in the Render dashboard.
- Use a production-grade database (managed Postgres) with migrations applied via Alembic.
- Ensure webhook endpoints are accessible and served via HTTPS (required by Paystack).
- Monitor logs and set up error reporting/alerting for payment and booking-critical flows.

---

## Troubleshooting — common issues

- Database connection failures: verify DATABASE_URL and network connectivity; ensure the DB accepts connections from your host.
- Authentication or token problems: confirm SECRET_KEY, correct token expiry settings and clock sync on servers.
- File uploads failing: check Cloudinary credentials and allowed file sizes/types.
- Payments failing: verify Paystack keys, webhook URL, and signature verification logic; ensure SSL for webhook endpoints.
- Migrations vs auto-create: do not rely on auto-create in production; use migrations (Alembic) to manage schema safely.

---

## Security considerations

- Keep SECRET_KEY and third-party service keys secret (do not check them into source control).
- Use HTTPS in production and enforce secure cookies wherever applicable.
- Validate and sanitize all external inputs; employ rate limiting on auth endpoints.
- Implement idempotency and replay protection for payment-related endpoints and webhook handlers.

---

## Contributing

- Read the project structure and module responsibilities above to find the right place to work.
- Implement features in the services layer, expose them via routes, and ensure Pydantic schemas validate input/response shapes.
- Add tests for any new business logic and update docs (OpenAPI metadata is generated from routes and schemas).
- For database changes, create migration scripts (Alembic) rather than relying on table auto-creation in production.

---

## Support & contact

If you need help:
- Check the interactive API docs at /docs on your running instance for exact request/response shapes.
- Inspect server logs for error stack traces and failing requests (especially for webhooks).
- For payment issues, use Paystack dashboard and logs to trace transactions.

---

## License

Specify your preferred license (e.g., MIT, Apache 2.0) in a LICENSE file to allow others to contribute and reuse the project appropriately.

---

Thank you for using Salon Connect. If you'd like, I can:
- Convert this into a nicely formatted README.md file in your repository.
- Produce a CONTRIBUTING.md with step-by-step development workflow.
- Generate a concise quick-start sheet with exact commands (separate file) for developers who want explicit CLI instructions.
Which would you like next?