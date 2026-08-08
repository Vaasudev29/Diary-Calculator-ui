# result_summary schema

This document describes the standardized `result_summary` schema used across calculators in the Dairy Process Calculator Suite.

Purpose
- Provide a small, consistent, and validated payload that all calculators populate in their outputs and in history entries.
- Enables generic UI features (dashboard, comparison, exports), interoperability, and reliable analytics.

Location
- Calculators place the standardized summary at `CalculatorResult.data['result_summary']` or in `CalculatorResult.metadata['result_summary']` for backward compatibility.

Schema (fields)
- `mass` (number, optional)
  - Description: Primary production mass for the result (e.g., kg of cheese, kg of paneer, kg of butter). Use SI metric units (kg) where possible.
  - Type: Decimal / float
  - Example: 1250.0

- `net_total_cost` (number, optional)
  - Description: Net cost for the batch after credits (e.g., whey credit) and processing adjustments. Currency units are implementation-specific (documented at app level).
  - Type: Decimal / float
  - Example: 15400.50

- `cost_per_kg` (number, optional)
  - Description: Derived metric (net_total_cost / mass) when both mass and net cost are available.
  - Type: Decimal / float
  - Example: 12.32

- `yield_pct` (number, optional)
  - Description: Yield percentage relative to input (where applicable).
  - Type: float (0-100)
  - Example: 18.5

- `extras` (object, optional)
  - Description: Free-form map for additional calculator-specific values that should not be required by generic consumers. Examples include `whey_volume_l`, `cheese_solids_kg`, `salt_added_kg`, etc.
  - Type: object (string keys to numeric/string values)

Validation rules
- The `ResultSummary` dataclass enforces numeric types for `mass`, `net_total_cost`, and `cost_per_kg` and ensures they are non-negative when present.
- `yield_pct` (if present) must be between 0 and 100.
- Calculators should use the shared helper `utils.result_helpers.build_result_summary(...)` to create validated summary dicts.

Versioning & evolution
- The schema is intentionally small. To evolve the schema:
  1. Add new optional fields (avoid breaking changes).
 2. Increase the schema version in history entries if you introduce a breaking change.
 3. Update `ResultSummary` and accompanying docs.

Examples
- Cheese detailed `result_summary` example:

```json
{
  "mass": 125.5,
  "net_total_cost": 1540.5,
  "cost_per_kg": 12.28,
  "yield_pct": 12.55,
  "extras": {
	"whey_volume_l": 920.0,
	"cheese_solids_kg": 56.7
  }
}
```

Best practices for contributors
- Always populate `result_summary` for any new calculator that produces a mass or cost result.
- Prefer `mass` and `net_total_cost` as the canonical keys; the helpers will map known calculator-specific keys into these fields.
- Keep `extras` for additional data; avoid placing critical cross-calculator metrics only in `extras`.
