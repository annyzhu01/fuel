# CLAUDE.md

## Error Handling Rules

### Never silently swallow errors
- Do not catch exceptions and return empty defaults (e.g. `return []`) without logging or propagating. Callers must be able to detect failures.
- If a function must be fault-tolerant (e.g. processing items in a batch), catch per-item, log the error, and track error counts. Return both success and error counts to the caller.

### API endpoints must return proper HTTP errors
- Wrap database operations in try/except and raise `HTTPException` with a meaningful status code and message. Do not let raw Supabase or ORM exceptions leak as opaque 500s.
- Catch `anthropic.APIError` in any endpoint that calls the AI service. Decide whether to fail the request (`HTTPException(503)`) or degrade gracefully (log and continue without the AI-generated field).
- When re-raising inside a retry loop, ensure `HTTPException` is not accidentally caught by a broader except clause — always add `except HTTPException: raise` before broader handlers.

### Validate configuration early
- Required environment variables (`SUPABASE_URL`, `SUPABASE_KEY`, `ANTHROPIC_API_KEY`) must be validated at client-creation time with a clear `RuntimeError` naming the missing variable(s). Do not pass `None` to SDK constructors.

### Use `maybe_single()` instead of `single()` for lookups that may return no rows
- `.single()` throws an opaque Supabase error when zero or multiple rows match. Use `.maybe_single()` and check the result explicitly, raising a descriptive error (e.g. `ValueError`) when the expected row is missing.

### AI response parsing must handle failures
- Always wrap `json.loads()` on AI-generated output in try/except `json.JSONDecodeError`. Raise a descriptive `RuntimeError` so the caller knows the AI returned an invalid response.
- Always wrap `anthropic` API calls in try/except `anthropic.APIError`. Either propagate as `RuntimeError` or degrade gracefully with logging.

### Batch operations must be resilient
- When processing items in a loop (embedding recipes, inserting records, extracting from PDF chunks), wrap each iteration in try/except so one failure does not abort the entire batch.
- Track and return error counts alongside success counts. Log each failure with enough context to identify the affected item.

### Use `logging` instead of `print` for errors and warnings
- All modules should use `logger = logging.getLogger(__name__)`.
- Use `logger.error()` for failures, `logger.warning()` for degraded-but-continuing situations, `logger.info()` for progress.
- Reserve `print()` for CLI user-facing output only (e.g. usage messages in `__main__` blocks).

### Initialize variables before loops that may not execute
- When a retry/fallback loop populates a variable (e.g. `ing_rows`), initialize it to `None` before the loop to avoid `UnboundLocalError` on all-attempts-failed paths.

## Stack

- **Backend**: Python, FastAPI, Supabase, Anthropic Claude API
- **Frontend**: Next.js, TypeScript
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **PDF ingestion**: pdfplumber + Claude extraction
