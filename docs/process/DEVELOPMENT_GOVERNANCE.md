# Development Governance

## Mandatory Before Any Scope/Architecture Adjustment

1. Create a PCR document from `docs/process/PCR_TEMPLATE.md`.
2. Update implementation plan and task breakdown.
3. Perform architecture review update in `docs/architecture/ARCH_REVIEW_LOG.md`.
4. Merge code only after governance checks pass.

## CI Blocking Checks

- `line-limit-check`
- `module-boundary-check`
- `architecture-review-check`

## Definition of Done

- Module structure compliance
- Public interface docs updated
- Core logic tests >= 80% coverage (target)
- Error handling and rollback path verified
