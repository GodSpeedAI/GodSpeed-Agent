# Task M: Config Validator

## Module

`config_validator.py` — nested configuration validation with type coercion.

## Intended Behavior

- `validate(config, schema)` validates a config dict against a schema. Returns list of error strings.
- Schema defines required fields, types, and nested structures.
- `coerce_value(value, target_type)` converts a value to the target type ("int", "float", "bool", "str").
- `get_nested(config, dotted_key)` retrieves a value from a nested dict using dot notation (e.g., `"database.host"`).

## Bugs (3)

### Bug 1: `get_nested()` crashes on missing intermediate keys

The `get_nested()` method does not handle the case where an intermediate key in the dotted path is missing. It raises `KeyError` instead of returning a default value. Tests expect it to return `None` for missing paths.

**Location**: `get_nested()`, key traversal loop.
**Fix**: Use `.get()` with a default or catch `KeyError`.

### Bug 2: `coerce_value()` for "int" rejects negative numbers

The `coerce_value()` method for integer coercion uses a check that rejects strings starting with `"-"`. Tests expect `"-5"` to coerce to `-5`.

**Location**: `coerce_value()`, integer coercion branch.
**Fix**: Allow leading minus sign in the numeric check.

### Bug 3: Required field check uses values instead of keys

The `validate()` method checks whether required fields exist by checking `config.values()` instead of `config.keys()`. This means it looks for the required field name among the config's values rather than its keys.

**Location**: `validate()`, required field check.
**Fix**: Check `config.keys()` instead of `config.values()`.

## Expected Error Profile

- **Bug 1** causes `KeyError` crashes in tests that use missing paths. Agent may try to fix the test instead of the method.
- **Bug 2** causes coercion assertion failures for negative numbers. Agent may not realize the coercion logic has a sign check.
- **Bug 3** causes validation assertion failures. Subtle — agent may not realize the check is on values instead of keys.
- **Expected errors**: 3-4. Bugs are mostly independent.

## Test File

`test_config_validator.py` — 8-10 tests covering:
- Basic validation
- Nested key access (present and missing)
- Type coercion (positive, negative, edge cases)
- Required field checking
- Schema validation

## Difficulty Assessment

**Medium-High**. Bug 1 produces a crash (easy to find). Bug 2 requires understanding the coercion logic. Bug 3 is subtle (values vs keys). All discoverable from test output.

## Files

- `tmp/pilot_tasks/task_m/config_validator.py` (buggy)
- `tmp/pilot_tasks/task_m/test_config_validator.py` (comprehensive)
