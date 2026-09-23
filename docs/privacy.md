# Privacy & consent (Phase 17)

## Soft email verification

- Register/login always issue JWT pairs.
- `users.email_verified_at` is nullable; Android surfaces verification state.
- Tokens are SHA-256 hashed; plaintext never stored or logged.
- `MockEmailProvider` is the default; real SMTP is out of scope.
- In `APP_ENV=test`, `GET /auth/_test/last-email` peeks at the last outbound debug token.

## Consent versions

- On register, backend stores `terms_version` / `privacy_version` from Settings (`TERMS_VERSION`, `PRIVACY_VERSION`) plus `accepted_terms_at`.
- `GET /users/me` returns consent + public `TERMS_URL` / `PRIVACY_URL`.
- Production Settings validation fails if legal URLs are missing or placeholder.

## Account delete / export

- `GET /users/me/export` — JSON sync of user-owned rows; no password hashes, refresh tokens, or provider secrets.
- `DELETE /users/me` with body `{"confirmation":"DELETE"}` hard-deletes the user; shared `ingredients` / `recipes` / `recipe_images` are untouched (no `user_id`).
- After delete, subsequent calls return `401`; Android clears local session only after `204`.

## Sessions

- Sessions are `refresh_tokens` rows with optional `device_label` / `platform` / `app_version` and `last_used_at`.
- List / revoke / revoke-all endpoints under `/users/me/sessions`.
