# Task K: Token Authentication

## Module

`token_auth.py` — token-based authentication with expiry and refresh.

## Intended Behavior

- `create_token(user_id, ttl_seconds)` creates a token with expiry timestamp.
- `validate_token(token)` returns True if token exists, is not expired, and signature matches.
- `refresh_token(token, new_ttl)` extends the token's TTL. Returns the updated token dict.
- `revoke_token(token)` removes a token. Returns True if token existed.

## Bugs (3)

### Bug 1: Expiry check uses `>` instead of `>=`

The `validate_token()` method checks `now > expiry` to determine if expired. This means a token at exactly its expiry time is still considered valid. Tests expect tokens to be expired at the exact expiry timestamp.

**Location**: `validate_token()`, expiry comparison.
**Fix**: Change `>` to `>=`.

### Bug 2: Signature comparison is case-sensitive

The `validate_token()` method compares the token's signature field against a computed signature using `!=`. The computed signature is always uppercase, but tokens created with lowercase signatures (from external sources) should also be valid. Tests create tokens with mixed-case signatures and expect validation to succeed.

**Location**: `validate_token()`, signature comparison.
**Fix**: Compare `.upper()` on both sides.

### Bug 3: `refresh_token()` does not update the expiry

The `refresh_token()` method returns the token dict but does not update the expiry timestamp with the new TTL. The token's expiry remains unchanged.

**Location**: `refresh_token()`, after retrieving the token.
**Fix**: Compute new expiry from `time.time() + new_ttl` and update the token.

## Expected Error Profile

- **Bug 1** causes boundary-condition assertion failures. Agent may need to understand the exact comparison semantics.
- **Bug 2** causes signature validation failures. Agent may not realize the comparison should be case-insensitive.
- **Bug 3** causes refresh-related assertion failures. Agent may add new fields without updating expiry.
- **Expected errors**: 3-4. Bugs are mostly independent.

## Test File

`test_token_auth.py` — 8-10 tests covering:
- Token creation
- Token validation (valid, expired, boundary)
- Signature matching (case sensitivity)
- Token refresh (expiry update)
- Token revocation
- Missing token handling

## Difficulty Assessment

**Medium**. Three independent bugs. Bug 1 is a boundary condition. Bug 2 requires understanding case sensitivity. Bug 3 is a missing update. All are discoverable from test output.

## Files

- `tmp/pilot_tasks/task_k/token_auth.py` (buggy)
- `tmp/pilot_tasks/task_k/test_token_auth.py` (comprehensive)
