# Task J: LRU Cache

## Module

`lru_cache.py` — least-recently-used cache with TTL expiration.

## Intended Behavior

- `put(key, value, ttl_seconds)` stores a key-value pair with optional TTL.
- `get(key)` returns the value if present and not expired, updates access order. Returns `None` if missing or expired.
- `size()` returns current number of entries (excluding expired).
- `evict(n)` removes the `n` least-recently-used entries. Returns count of evicted entries.

## Bugs (3)

### Bug 1: Eviction removes most-recently-used instead of least-recently-used

The `evict(n)` method removes from the wrong end of the access-order tracking. It removes the most recently accessed entries instead of the least recently accessed.

**Location**: `evict()` method, iteration direction.
**Fix**: Remove from the oldest end of the access order.

### Bug 2: TTL comparison is backwards

The TTL check in `get()` compares `now < expiry` when it should compare `now > expiry` (or equivalently, the expiry check should be `now >= expiry` for expired). This means entries are considered expired when they are still valid, and valid when expired.

**Location**: `get()` method, TTL expiry check.
**Fix**: Reverse the comparison direction.

### Bug 3: `get()` does not update access order

The `get()` method returns the value but does not move the key to the most-recently-used position. This means repeated gets do not protect an entry from eviction.

**Location**: `get()` method, after value retrieval.
**Fix**: Move accessed key to the end of the access order.

## Expected Error Profile

- **Bug 1** causes eviction order assertion failures. Agent may try to fix the eviction count instead of the order.
- **Bug 2** causes TTL-related assertion failures. Agent may misunderstand the comparison direction.
- **Bug 3** causes access-order assertion failures after get+evict sequences. Subtle — agent may not realize get() should update order.
- **Expected errors**: 3-5. Bugs interact: fixing eviction order without fixing access order produces confusing results.

## Test File

`test_lru_cache.py` — 8-10 tests covering:
- Basic put/get
- TTL expiration
- Eviction order (LRU)
- Access order updates on get
- Size tracking
- Expired entry cleanup

## Difficulty Assessment

**High**. Three interacting bugs in a data structure. Bug 3 is particularly subtle — the agent must understand that get() should update access order. Bugs 1 and 3 interact: fixing eviction without fixing access order produces wrong results.

## Files

- `tmp/pilot_tasks/task_j/lru_cache.py` (buggy)
- `tmp/pilot_tasks/task_j/test_lru_cache.py` (comprehensive)
