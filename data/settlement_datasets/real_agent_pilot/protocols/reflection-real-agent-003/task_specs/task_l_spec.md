# Task L: Priority Queue

## Module

`priority_queue.py` — max-priority queue with duplicate handling and peek.

## Intended Behavior

- `enqueue(item, priority)` adds an item with given priority. Duplicate items are allowed (appended, not overwritten).
- `dequeue()` removes and returns the highest-priority item. Ties broken by insertion order (FIFO within priority).
- `peek()` returns a copy of the highest-priority item without removing it. Modifications to the returned dict must not affect the queue.
- `size()` returns the number of items in the queue.

## Bugs (3)

### Bug 1: Dequeue returns lowest priority instead of highest

The `dequeue()` method selects the item with the lowest priority value instead of the highest. Since this is a max-priority queue, it should return the highest priority.

**Location**: `dequeue()`, priority selection logic.
**Fix**: Select maximum priority instead of minimum.

### Bug 2: Duplicate items overwrite instead of appending

The `enqueue()` method uses the item as a dictionary key or set member, causing duplicate items to overwrite each other instead of being stored separately.

**Location**: `enqueue()`, item storage logic.
**Fix**: Use a list-based storage that allows duplicates.

### Bug 3: `peek()` returns a direct reference, not a copy

The `peek()` method returns the internal item dict directly. Modifications to the returned dict mutate the queue's internal state. Tests expect peek to return an independent copy.

**Location**: `peek()`, return statement.
**Fix**: Return `copy.deepcopy(item)` or construct a new dict.

## Expected Error Profile

- **Bug 1** causes dequeue order assertion failures. Agent may try to reverse the test expectations instead of the queue logic.
- **Bug 2** causes size and duplicate-handling assertion failures. Agent may not realize duplicates should be allowed.
- **Bug 3** causes mutation-safety assertion failures. Subtle — agent may not realize peek() should return a copy.
- **Expected errors**: 3-5. Bugs interact: fixing dequeue without fixing duplicates produces confusing results.

## Test File

`test_priority_queue.py` — 8-10 tests covering:
- Basic enqueue/dequeue
- Priority ordering (highest first)
- Duplicate items
- Peek (non-destructive, returns copy)
- Size tracking
- Empty queue handling

## Difficulty Assessment

**High**. Three interacting bugs in a data structure. Bug 2 requires understanding that duplicates are allowed. Bug 3 is subtle (reference vs copy). Bugs 1 and 2 interact: fixing priority without fixing duplicates produces wrong dequeue results.

## Files

- `tmp/pilot_tasks/task_l/priority_queue.py` (buggy)
- `tmp/pilot_tasks/task_l/test_priority_queue.py` (comprehensive)
