# School Management System — Frontend (React + Vite)

React frontend for the Web-Based School Management System, talking to the
Django REST Framework + MySQL backend. Built with Vite, React Router, and
plain CSS (no UI framework dependency) using a set of design tokens for a
consistent "ledger / report card" visual style.

## Tech stack

- React 18, React Router 6
- Axios (with automatic JWT refresh)
- Vite (dev server + build)
- No CSS framework — hand-written design tokens in `src/styles/tokens.css`

## Prerequisites

- Node.js 18+ and npm
- The Django backend running and reachable (see the backend's own README)

## Setup

```bash
npm install
cp .env.example .env
```

Edit `.env` if your backend isn't at the default address:

```
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

## Run the dev server

```bash
npm run dev
```

Visit `http://localhost:3000`. Make sure the backend's `CORS_ALLOWED_ORIGINS`
(in its `.env`) includes `http://localhost:3000`.

## Build for production

```bash
npm run build
```

Output goes to `dist/`. Serve it with Nginx (or any static host) and point it
at the backend's API — see the backend README's deployment diagram (4.20 in
the design doc).

## Project structure

```
src/
  api/            Axios client + one thin wrapper module per backend app
  components/     Reusable UI: DataTable, Modal, ResourceForm, ResourceManager,
                   Badge, StatCard, AlertBanner, LoadingSpinner, EmptyState
  context/        AuthContext (session state, login/logout, silent restore)
  layouts/        AppLayout, Sidebar (role-filtered nav), Topbar
  pages/          One folder per module, plus dashboards/ for the 8 role views
  routes/         ProtectedRoute (auth guard), RoleRoute (role guard)
  styles/         tokens.css (design system) + global.css (component styles)
  utils/          roles.js, format.js
```

## How authentication works

The login form's single "identifier" field is sent to the backend as
`username` — the backend's custom auth backend resolves it to either an
actual username (staff/parents) or a student index number (students),
matching design doc 3.5–3.7. On success:

- `access`/`refresh` JWTs are stored in `localStorage`
- the returned `user` object populates `AuthContext`
- the returned `dashboard` path is used for the post-login redirect

Every subsequent request automatically attaches `Authorization: Bearer
<access>` (see `api/client.js`). On a 401, the client transparently tries
`/api/auth/token/refresh/` once and retries the original request; if that
also fails, the session is cleared and the user is bounced to `/login`.

## Role-based UI

`layouts/navConfig.js` filters sidebar links by `user.role`. `RoleRoute`
enforces the same rules at the route level so a user can't reach a page by
typing a URL directly. **This is a UI convenience only** — every actual
authorization decision is re-enforced by the Django backend regardless of
what the frontend shows or hides, per design doc 3.6.

The dashboard (`pages/DashboardPage.jsx`) fetches the single
`/api/dashboard/` endpoint and renders one of eight role-specific view
components (`pages/dashboards/RoleDashboards.jsx`) based on the shape the
backend returns for that role.

## The generic CRUD system

Most list/create/edit/delete pages (Classes, Subjects, Teachers, Parents,
Students, Fee Structures, Payments, Books, User Accounts) are built by
configuring `components/ResourceManager.jsx` with:

- `api` — an object with `list/create/update/remove` (see `api/resource.js`)
- `columns` — table column definitions
- `formFields` (or separate `createFields`/`editFields`) — drives the
  create/edit modal via `ResourceForm` + `FormField`

This keeps each page file small and consistent; pages that need bespoke UI
(Attendance's daily grid, Examinations' bulk marks entry, Fees' balance
lookup) are written by hand instead of forcing them into the generic shape.

## Known follow-ups

- No automated frontend tests yet (Vitest + React Testing Library would be
  a natural fit, mirroring the backend's Chapter 4 test plan).
- Notifications and the unread-count badge poll every 30s; swapping to
  WebSockets/SSE would remove the polling delay.
