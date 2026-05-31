# Task N: Rate Limiter

## Module

`rate_limiter.py` — sliding-window rate limiter with per-key tracking.

## Intended Behavior

- `is_allowed(key)` returns True if the request is within rate limits, False if exceeded. Tracks per-key request counts in sliding time windows.
- `get_count(key)` returns the number of requests in the current window for a given key.
- `reset(key=None)` resets the rate limiter for a specific key or all keys.
- `get_remaining(key)` returns the number of remaining requests allowed in the current window.

## Bugs (3)

### Bug 1: Window boundary uses `>` instead of `>=`

The window boundary check uses `current_time - oldest_timestamp > window_size` when it should use `>=`. This means requests exactly at the window boundary are not expired when they should be.

**Location**: `is_allowed()`, window expiry check.
**Fix**: Change `>` to `>=`.

### Bug 2: Counter does not reset when window slides

When the window slides (old requests expire), the counter is decremented but the expired timestamps are not removed from the internal list. This causes the count to be wrong after window transitions.

**Location**: `is_allowed()`, after window expiry detection.
**Fix**: Remove expired timestamps from the internal list, not just decrement the counter.

### Bug 3: Per-key limits share a global counter

The rate limiter uses a single global counter instead of per-key counters. Requests to different keys all count against the same limit.

**Location**: `is_allowed()`, counter lookup.
**Fix**: Use per-key counters (dict of lists or dict of counts).

## Expected Error Profile

- **Bug 1** causes boundary-condition assertion failures. Agent may need to understand the exact window semantics.
- **Bug 2** causes count assertion failures after window transitions. Agent may try to fix the count method instead of the expiry cleanup.
- **Bug 3** causes per-key isolation assertion failures. Agent may not realize keys should be independent.
- **Expected errors**: 3-5. Bugs interact: fixing the window without fixing per-key isolation produces confusing results.

## Test File

`test_rate_limiter.py` — 8-10 tests covering:
- Basic rate limiting (allowed/denied)
- Window boundary behavior
- Per-key isolation
- Counter accuracy after window slides
- Reset functionality
- Remaining requests count

## Difficulty Assessment

**High**. Three interacting bugs in a stateful component. Bug 2 is subtle (stale timestamps). Bug 3 requires understanding per-key isolation. Bugs 2 and 3 interact: fixing counts without fixing per-key isolation produces wrong results.

## Files

- `tmp/pilot_tasks/task_n/rate_limiter.py` (buggy)
- `tmp/pilot_tasks/task_n/test_rate_limiter.py` (comprehensive)
