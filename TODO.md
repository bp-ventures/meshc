## Normalize Token Expiration Handling

- Audit `store_token` (and tests) to confirm the most common entry point is a string timestamp from CLI/README, so we can focus fixes there.
- Decide on a single representation for `expires_at` (e.g., naive UTC) and convert every input—strings or tz-aware datetimes—to that format before saving.
- Update `IntegrationToken.is_expired` to compare like-with-like: either call `datetime.utcnow()` on the stored naive UTC values or make both sides tz-aware.
- Fix `IntegrationToken.to_dict()` so it emits valid ISO strings (no duplicated `Z`) by using `datetime.replace(tzinfo=timezone.utc).isoformat().replace('+00:00','Z')` or similar.
- Extend storage tests to cover string inputs, tz-aware datetimes, `is_expired`, and `to_dict()` to ensure the regressions can’t recur.
