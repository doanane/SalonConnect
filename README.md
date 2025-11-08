# Salon Connect API

 This repository contains the backend API for a salon booking platform I built to connect customers with salons, manage bookings, and handle payments. Below I explain the project, how it works, and how you can run or contribute to it. 
---

## Quick overview

Salon Connect is a complete backend system that provides:

- User management with role-based access (Customer, Vendor, Admin).
- Salon discovery (search, filters, featured & nearby listings).
- Multi-service booking system with real-time availability checks.
- Payment processing integrated with Paystack (initiate, verify, webhook handling).
- Vendor dashboard features (revenue insights and booking analytics).
- File uploads (images via Cloudinary) and email (SMTP) for password resets.
- Auto-generated API docs via OpenAPI / Swagger.

Live deployments I maintain:
- Primary: https://salonconnect-qzne.onrender.com
- Swagger UI: https://salonconnect-qzne.onrender.com/docs
- Health check: https://salonconnect-qzne.onrender.com/health

---

## What you get in this repo (conceptually)

Top-level project layout and responsibilities (so you know where to look):

- app/main.py — application entrypoint, router mounting, startup/shutdown hooks
- app/database.py — DB engine and session helpers
- app/models/ — ORM model definitions (User, Salon, Service, Booking, Payment)
- app/schemas/ — Pydantic schemas for request/response validation
- app/routes/ — HTTP endpoints grouped by domain (auth, users, salons, bookings, payments, favorites)
- app/services/ — Business logic: auth, booking management, payments, email helpers
- app/core/ — app configuration, security helpers, Cloudinary utilities
- app/utils/ — shared validators and helpers
- requirements.txt — Python dependency list
- .env — environment variables file example (not committed with secrets)

---

## Key features (short)

- JWT-based authentication with access and refresh tokens
- Role-based access control (Customer, Vendor, Admin)
- File uploads to Cloudinary for avatars and salon images
- Paystack integration with webhook verification
- Booking lifecycle management: Pending → Confirmed → Completed → Cancelled
- Interactive API docs (Swagger / ReDoc)

---

## Environment variables (what to provide)

Create a `.env` in the repo root (or configure in your host platform). Important variables I use:

- DEBUG: True/False — enable development features
- SECRET_KEY: used for JWTs and security — keep private
- DATABASE_URL: Postgres connection string (postgresql://user:pass@host:5432/dbname)
- CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
- EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL
- PAYSTACK_SECRET_KEY, PAYSTACK_PUBLIC_KEY, PAYSTACK_BASE_URL (default: https://api.paystack.co)
- ACCESS_TOKEN_EXPIRE_MINUTES

---

## Installation & setup (high-level steps)

I keep exact commands short here — these are the steps I follow locally:

1. Clone the repository:
```bash
git clone git@github.com:doanane/SalonConnect.git
cd SalonConnect
```

2. Create and activate a virtual environment (example):
```bash
python -m venv venv
# macOS / Linux
source venv/bin/activate
# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Add your environment variables to `.env` (see the section above).

5. Start the app in development:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- The interactive API docs are at: salonconnect-qzne.onrender.com/docs
- Health endpoint: salonconnect-qzne.onrender.com/health

Note: In production I recommend using a production ASGI server, managed Postgres, and Alembic migrations.

---

## API overview (conceptual endpoints)

I list the main groups and what they do — use the Swagger UI for exact request/response examples.

Authentication
- POST /api/users/register — register new user
- POST /api/users/login — login and receive tokens
- POST /api/users/forgot-password — request password reset link
- POST /api/users/reset-password — reset using token
- POST /api/users/change-password — change password (authenticated)
- GET /api/users/token/verify — verify token
- POST /api/users/logout — logout (invalidate tokens)

User management
- GET /api/users/me — get current user
- GET /api/users/me/profile — get profile
- PUT /api/users/me/profile — update profile (image uploads supported)
- GET /api/users/me/role — get current role
- GET /api/users/customer/dashboard — customer dashboard
- GET /api/users/vendor/dashboard — vendor dashboard

Salon discovery & management
- GET /api/salons/ — browse salons with filters (city, rating, services)
- GET /api/salons/featured — featured salons
- GET /api/salons/nearby — nearby salons by coordinates
- GET /api/salons/{salon_id} — salon details
- POST /api/salons/ — create a salon (Vendor)
- GET /api/salons/{salon_id}/services — list services
- POST /api/salons/{salon_id}/services — add a service (Owner)
- GET /api/salons/{salon_id}/reviews — list reviews
- POST /api/salons/{salon_id}/reviews — create review (Customer)

Booking management
- POST /api/bookings/ — create booking (multi-service support)
- GET /api/bookings/ — list user bookings
- GET /api/bookings/{booking_id} — booking detail
- PUT /api/bookings/{booking_id} — update booking
- GET /api/bookings/vendor/bookings — vendor bookings list

Payments & webhooks
- POST /api/payments/initiate — start a payment flow (Paystack)
- POST /api/payments/verify — verify a payment
- GET /api/payments/{payment_id} — get payment details
- POST /api/payments/webhook/paystack — Paystack webhook endpoint (verify signature)

Favorites
- GET /api/users/favorites — list favorites
- POST /api/users/favorites/{salon_id} — add favorite
- DELETE /api/users/favorites/{salon_id} — remove favorite

Authentication header for protected endpoints:
```
Authorization: Bearer <access_token>
```

---

## Example quick curl flows

Register a user:
```bash
curl -X POST "salonconnect-qzne.onrender.com/api/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "first_name": "John",
    "last_name": "Doe",
    "role": "customer"
  }'
```

Login:
```bash
curl -X POST "salonconnect-qzne.onrender.com/api/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

Browse salons:
```bash
curl -X GET "salonconnect-qzne.onrender.com/api/salons/?city=Lagos&min_rating=4.0"
```

---

## Database models (conceptual)

Primary entities I use:
- User & UserProfile — core identity and profile details
- PasswordReset — tokens for reset flow
- Salon, Service, SalonImage, Review — salon catalog and metadata
- Booking & BookingItem — booking master/detail records
- Payment — transactions with gateway references

---

## Testing & validation

- The fastest way to explore endpoints is via the running Swagger UI.
- For automated testing: add unit tests around service-layer logic and integration tests for booking and payment flows.
- When testing payments, use Paystack test credentials and the Paystack dashboard to inspect requests.

---

## Deployment notes

I typically deploy to Render.com. Basic steps I follow:
1. Push code to GitHub.
2. Connect the repo in Render.
3. Set environment variables in Render dashboard.
4. Use a managed Postgres instance and run migrations (Alembic recommended).
5. Ensure webhook endpoints are HTTPS and accessible (Paystack requires HTTPS).

---

## Troubleshooting (common things I check)

- Database connection: double-check DATABASE_URL and network access.
- Authentication issues: verify SECRET_KEY and token expirations; ensure server clocks are synced.
- Uploads failing: confirm Cloudinary credentials and allowed file sizes.
- Payment errors: verify Paystack keys, webhook endpoints, and signature verification logic.

---

## Security considerations I follow

- Never commit secrets (SECRET_KEY, Paystack keys, DB passwords) to the repo.
- Use HTTPS in production and secure headers.
- Validate and sanitize inputs, especially the data sent to third parties.
- Add rate limiting to sensitive endpoints (login, password reset) if needed.
- Use idempotency and replay protection for webhooks and payment flows.

---

## Contributing

I welcome contributions. If you want to help:
- Work in the services layer for business logic, expose behavior via routes, and add Pydantic schemas for validation.
- Write tests for new features and bug fixes.
- Use Alembic migrations for schema changes (don't rely on auto-creation in production).
- Open a pull request and describe the change — I will review.

---

## Support / Contact

If you need help or have enquiries about Salon Connect, email me at: anane365221@gmail.com

For troubleshooting I recommend:
- Checking the interactive docs at `/docs` on your running instance for exact payloads.
- Reviewing server logs for stack traces and failing requests.
- Using provider dashboards (Paystack, Cloudinary) to trace transactions/uploads.

---

## License

Add a LICENSE file with your preferred license (MIT, Apache-2.0, etc.) so others know how they can use and contribute.

---

If you have any enquiries, contact me via: anane365221@gmail.com
