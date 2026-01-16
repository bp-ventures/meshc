
  1. All API endpoints are CSRF-exempt with no authentication

  # views.py:35-37, 104, 139
  @csrf_exempt
  @require_POST
  def api_link_token(request):

  Problem: Any website can make cross-origin requests to generate link tokens, save integration tokens, or (with IP spoofing) send webhooks. There's zero authentication.

  Impact: Attacker embeds <form action="https://yoursite/meshc/api/save-token/"> on malicious page → steals/overwrites user tokens.

  ---
  2. X-Forwarded-For is trivially spoofable

  # views.py:23-27
  def get_client_ip(request) -> str:
      xff = request.META.get("HTTP_X_FORWARDED_FOR")
      if xff:
          return xff.split(",")[0].strip()  # Attacker controls this

  Problem: Webhook IP allowlist is meaningless. Attacker sends X-Forwarded-For: 127.0.0.1 and bypasses filter entirely.

  Fix needed: Use request.META['REMOTE_ADDR'] only, or configure trusted proxy IPs explicitly.

  ---
  3. Integration tokens stored in plaintext

  # models.py:48
  token_id = models.CharField(max_length=255, db_index=True)

  Problem: token_id is a sensitive credential granting access to user exchange accounts. Stored unencrypted in SQLite. README says "consider encrypting" but doesn't.

  Impact: Database leak = full compromise of all stored integration tokens.

  ---
  4. CLI now requires Django bootstrap

  # storage.py:38-58
  def _django_setup() -> None:
      """Bootstrap Django for CLI use (standalone mode)."""
      ...
      settings.configure(...)
      django.setup()

  Problem: The "lightweight CLI" now imports Django, configures settings, runs migrations. ~500ms startup penalty. Breaks for users who pip install meshc without Django project present.

  Hardcoded path breaks pip installs:
  _DJANGO_PROJECT_PATH = Path(__file__).parent.parent.parent / 'meshc_django'

  ---
  5. No input validation on wallet addresses

  # views.py:55-56
  address = data.get('address')
  if not address:  # Only checks existence, not format

  Problem: No regex validation. Accepts address: "'; DROP TABLE users;--". Relies entirely on Mesh API to reject bad input.

  Missing:
  - Stellar: Must match ^G[A-Z2-7]{55}$
  - Ethereum: Must match ^0x[a-fA-F0-9]{40}$ + checksum

  ---
  6. Race condition in webhook handler

  # views.py:182-196
  webhook, created = MeshWebhook.objects.get_or_create(...)
  if not created:
      webhook.history.append(payload)  # Not atomic
      webhook.save()

  Problem: Two simultaneous webhooks for same transaction_id:
  1. Both call get_or_create, both get created=False
  2. Both read same history array
  3. Both append, both save
  4. One write overwrites the other → data loss

  Fix: Use select_for_update() or F() expressions for atomic append.

  ---
  7. Secret key has insecure fallback

  # settings.py:10
  SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-only-change-in-prod')

  Problem: Fails silently to insecure default. Should crash in production if not set.
  ---
  9. No rate limiting

  - /meshc/api/link-token/ can be hammered to exhaust Mesh API quota
  - /meshc/api/webhook/ can be spammed (DoS on database)
  - No django-ratelimit or similar

  ---
  10. Test coverage gaps
  ┌──────────────────────────────┬────────────────────────────────────────────┐
  │        What's tested         │             What's NOT tested              │
  ├──────────────────────────────┼────────────────────────────────────────────┤
  │ API returns 400 on bad input │ Frontend JS (icon switching, address swap) │
  ├──────────────────────────────┼────────────────────────────────────────────┤
  │ Mocked Mesh API success      │ Actual Mesh sandbox integration            │
  ├──────────────────────────────┼────────────────────────────────────────────┤
  │ Webhook creates record       │ Race conditions


  #1 and #5 are done
   we need to fix the token storage and authentication in the next release
