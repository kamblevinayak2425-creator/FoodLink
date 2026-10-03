# FoodLink – Smart Surplus Food Redistribution Platform

A responsive Flask demonstration app connecting food donors with NGOs and community members for direct self-pickup. Listings receive a simple expiry-priority score based on preparation time, storage conditions, and availability. The food image recognition box is intentionally an integration placeholder; image upload and preview work, but no vision model is called.

## Folder structure

```text
FoodLink-Platform/
├── app.py                  Flask routes, SQLAlchemy models, auth, demo seeding
├── requirements.txt
├── .env.example            Local configuration template
├── schema.sql              MySQL Workbench schema
├── foodlink.db             Created automatically for local SQLite runs
├── templates/              Jinja HTML templates and shared components
└── static/
    ├── css/style.css       Responsive FoodLink design
    ├── js/app.js           Form, preview, timeline, and chart behavior
    └── uploads/            Validated food images (created automatically)
```

## Run in VS Code (SQLite quick start)

1. Open the `FoodLink-Platform` folder in VS Code.
2. In the integrated terminal, create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env`. Replace `SECRET_KEY` with a long random value. SQLite is the default and creates `foodlink.db` automatically.
5. Run the server:
   ```powershell
   flask --app app run --debug
   ```
6. Visit http://127.0.0.1:5000.

The first run seeds example users and food listings. Demo password for all listed users is `FoodLink123!`:

- Donor: `donor@foodlink.demo`
- Verified NGO: `ngo@foodlink.demo`
- Consumer: `consumer@foodlink.demo`
- Admin: `admin@foodlink.demo`

The admin role is deliberately not available on public registration. New NGOs need admin verification before creating emergency requests.

## MySQL Workbench setup

1. Start your local MySQL server and open MySQL Workbench.
2. Open `schema.sql` in a SQL tab and execute it. This creates the `foodlink` database and its related tables.
3. Create a dedicated database user in Workbench (recommended), then grant it privileges on `foodlink.*`.
4. Set the connection in `.env`, for example:
   ```dotenv
   DATABASE_URL=mysql+pymysql://foodlink_user:your-password@localhost:3306/foodlink
   ```
   URL-encode special characters in the password. Never commit `.env` or use a production database password in source control.
5. Install the Python requirements and start Flask as above. SQLAlchemy creates/validates the ORM tables at startup. `schema.sql` additionally includes the pickup and analytics event tables for Workbench review.

## Main routes

`/` home · `/register` · `/login` · `/dashboard` · `/add-food` · `/food` · `/food/<id>` · `/request-food/<id>` · `/requests` · `/approve-request/<id>` · `/reject-request/<id>` · `/pickup/<id>` · `/emergency-request` · `/notifications` · `/analytics` · `/profile` · `/admin`

JSON endpoint: `GET /api/food` returns currently available listings with computed expiry priority.

## Test with Postman

Start Flask first, then create a Postman environment variable `baseUrl` with value `http://127.0.0.1:5000`.

- `GET {{baseUrl}}/api/food` checks the public listings API.
- `POST {{baseUrl}}/register` with Body → x-www-form-urlencoded: `name`, `email`, `mobile`, `password` (8+ chars), `address`, `role` (`donor`, `ngo`, or `consumer`).
- For POSTs from Postman, first GET a page such as `{{baseUrl}}/login`, retain its session cookie, and send the `csrf_token` value from the `csrf-token` meta tag with the form body.
- `POST {{baseUrl}}/login` with `email` and `password`. Enable Postman's cookie jar to retain the session cookie for subsequent requests.
- As a donor, `POST {{baseUrl}}/add-food` is a browser form route and requires a session; use the web interface for multipart image tests.
- As an NGO/consumer, `POST {{baseUrl}}/request-food/1` with `quantity` and ISO local `pickup_at` (for example `2026-10-03T18:30:00`).
- As the listing donor, `POST {{baseUrl}}/approve-request/1` with optional `approved_quantity` and `pickup_at`, or `POST {{baseUrl}}/reject-request/1`.
- `GET {{baseUrl}}/pickup/1` displays pickup details in a browser. Pickup updates are form POSTs; use the UI to move between Ready for Pickup, Collected, and Completed.
- Sign in with the admin demo account to test `/admin` and verify a newly registered NGO.

The app uses normal HTML form responses and session cookies, not a fully REST/JSON API for every workflow. Postman can inspect route status, forms, redirects, and the public JSON listing endpoint; browser cookies retain Flask sessions.

## Security and scope

Passwords use Werkzeug's adaptive password hashing, ORM queries are parameterized, roles are checked on protected routes, uploads enforce an extension allow-list and 5 MB request limit, and user-provided text is autoescaped by Jinja. Set a unique secret key, disable debug mode, serve behind HTTPS, and add CSRF protection, rate limiting, email verification, and managed upload storage before public deployment. Expiry scoring is transparent rule-based demo logic, not an AI prediction model. This service coordinates self-pickup only; it does not provide delivery.
