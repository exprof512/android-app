# Product analytics (Phase 17)

## Ingest

- `POST /api/v1/events` accepts a single event or batch ≤20.
- `user_id` is taken only from the access JWT (client cannot spoof).
- Event names are whitelisted; property keys/values are size-capped; obvious PII keys rejected.
- Redis (or in-memory fallback) rate-limits per user/IP.
- Failures never raise into product flows on the Android side (`AnalyticsTracker` is best-effort).

## Storage

- Table `product_events`: `event_name`, `platform`, `app_version`, `properties` JSON, `occurred_at`, `user_id`.
- Sink is Postgres via `AnalyticsService`. No Firebase/Amplitude in MVP.

## Android

- `BackendAnalyticsTracker` posts to `/events` on a background scope.
- Used for login/opened, export, delete, and similar product signals.
