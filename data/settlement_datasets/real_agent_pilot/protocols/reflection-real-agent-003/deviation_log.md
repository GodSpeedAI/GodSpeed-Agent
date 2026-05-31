# Deviation Log

## Purpose

Record any deviations from the pre-registered protocol. Deviations may affect the validity of specific runs or the entire pilot.

## Deviation Format

Each deviation is recorded with:

| Field | Description |
|---|---|
| deviation_id | Unique identifier (DEV-001, DEV-002, etc.) |
| timestamp | When the deviation was discovered |
| phase | Which phase it occurred in (runner, blinding, evaluation, etc.) |
| description | What happened |
| affected_runs | Which runs are affected (run-ids or "all") |
| severity | low / medium / high / critical |
| resolution | What was done about it |
| impact_on_conclusions | Whether and how this affects conclusions |

## Severity Definitions

| Severity | Meaning |
|---|---|
| Low | Minor procedural issue. Does not affect data validity. |
| Medium | Procedural issue that may affect some scores but not overall conclusions. |
| High | Issue that may invalidate one or more runs. |
| Critical | Issue that invalidates the pilot or compromises blinding. |

## Active Deviations

(None yet — pilot has not been executed.)

## Deviation Records

(To be filled during execution.)

---

### Template for New Deviations

```
#### DEV-NNN: [Title]

- **Timestamp**: 
- **Phase**: 
- **Description**: 
- **Affected Runs**: 
- **Severity**: 
- **Resolution**: 
- **Impact on Conclusions**: 
```
