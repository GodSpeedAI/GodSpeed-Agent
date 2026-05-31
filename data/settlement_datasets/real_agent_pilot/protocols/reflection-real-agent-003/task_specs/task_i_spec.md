# Task I: Event Logger

## Module

`event_logger.py` — structured event logging with level filtering and rotation.

## Intended Behavior

- `log(event, level, metadata)` records an event with ISO-format timestamp, level, and optional metadata.
- `get_logs(level=None)` returns all logs, optionally filtered to minimum level (DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50).
- `rotate(max_entries)` keeps only the most recent `max_entries` logs, discarding older ones. Returns count of discarded entries.
- `clear()` removes all logs and resets the internal counter.

## Bugs (3)

### Bug 1: Timestamp is raw float, not ISO format

The `log()` method stores `time.time()` (a float like `1717152000.123`) instead of an ISO-format string. Tests expect timestamps to contain `"-"` and `":"` (ISO format markers).

**Location**: `log()` method, timestamp assignment.
**Fix**: Use `datetime.datetime.now().isoformat()`.

### Bug 2: Level filter uses strict equality instead of minimum threshold

The `get_logs(level=...)` method filters using `== level` instead of `>= level`. This means `get_logs(level="WARNING")` returns only WARNING logs, not WARNING + ERROR + CRITICAL.

**Location**: `get_logs()` method, level filtering logic.
**Fix**: Compare `log_level_value >= filter_level_value`.

### Bug 3: Rotation counter never resets after `clear()`

The `clear()` method empties the log list but does not reset the internal `_counter` used for entry numbering. After clear + new logs, entry numbers continue from where they left off. Tests expect counter to reset to 0.

**Location**: `clear()` method.
**Fix**: Reset `self._counter = 0` in `clear()`.

## Expected Error Profile

- **Bug 1** causes timestamp format assertion failures. Agent may try to fix the format string or the test.
- **Bug 2** causes level filtering assertion failures. Agent may misunderstand the filtering semantics.
- **Bug 3** causes counter assertion failures after clear+log sequences. Agent may not realize clear() is incomplete.
- **Expected errors**: 3-5. Bugs are independent but may be discovered sequentially.

## Test File

`test_event_logger.py` — 8-10 tests covering:
- Basic logging
- Timestamp format
- Level filtering (minimum threshold)
- Rotation
- Counter reset after clear
- Metadata handling

## Difficulty Assessment

**Medium-High**. Three independent bugs in different methods. Bug 2 requires understanding the level hierarchy. Bug 3 is subtle (counter state). Agent must read test output carefully to distinguish bugs.

## Files

- `tmp/pilot_tasks/task_i/event_logger.py` (buggy)
- `tmp/pilot_tasks/task_i/test_event_logger.py` (comprehensive)
