# Phase 6 Release Evidence Report

- Generated at (UTC): `2026-04-01T01:50:37Z`
- Host: `Darwin misudeMacBook-Air.local 24.6.0 Darwin Kernel Version 24.6.0: Mon Jul 14 11:30:34 PDT 2025; root:xnu-11417.140.69~1/RELEASE_ARM64_T8103 arm64`
- Python: `Python 3.12.1`
- Git revision: `N/A (no git repository)`

## Command Results

### Release Pack Gate

- Command: `make phase6-pack`
- Started (UTC): `2026-04-01T01:50:37Z`
- Ended (UTC): `2026-04-01T01:50:49Z`
- Status: `PASS`

```text
bash scripts/run_phase6_release_pack.sh
[phase6-pack] 1/3 verify release artifacts...
[phase6-pack] 2/3 execute release-readiness gate...
[phase6-ready] 1/4 governance checks...

> superassistant-monorepo@0.1.0 check:all
> npm run check:line-limit && npm run check:module-boundary && npm run check:architecture


> superassistant-monorepo@0.1.0 check:line-limit
> bash scripts/check_line_limit.sh


> superassistant-monorepo@0.1.0 check:module-boundary
> python3 scripts/check_module_boundaries.py

module-boundary-check: passed

> superassistant-monorepo@0.1.0 check:architecture
> bash scripts/check_architecture_review.sh

architecture-review-check: passed
[phase6-ready] 2/4 api regression...
.......................                                                  [100%]
=============================== warnings summary ===============================
../../../../Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/dateutil/tz/tz.py:37
  /Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/dateutil/tz/tz.py:37: DeprecationWarning: datetime.datetime.utcfromtimestamp() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.fromtimestamp(timestamp, datetime.UTC).
    EPOCH = datetime.datetime.utcfromtimestamp(0)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
23 passed, 1 warning in 0.69s
[phase6-ready] 3/4 phase5 acceptance...
[phase5] running governance checks...

> superassistant-monorepo@0.1.0 check:all
> npm run check:line-limit && npm run check:module-boundary && npm run check:architecture


> superassistant-monorepo@0.1.0 check:line-limit
> bash scripts/check_line_limit.sh


> superassistant-monorepo@0.1.0 check:module-boundary
> python3 scripts/check_module_boundaries.py

module-boundary-check: passed

> superassistant-monorepo@0.1.0 check:architecture
> bash scripts/check_architecture_review.sh

architecture-review-check: passed
[phase5] running key auth/offline/admin acceptance tests...
.....                                                                    [100%]
=============================== warnings summary ===============================
../../../../Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/dateutil/tz/tz.py:37
  /Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/dateutil/tz/tz.py:37: DeprecationWarning: datetime.datetime.utcfromtimestamp() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.fromtimestamp(timestamp, datetime.UTC).
    EPOCH = datetime.datetime.utcfromtimestamp(0)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
5 passed, 10 deselected, 1 warning in 0.27s
[phase5] acceptance passed.
[phase6-ready] 4/4 phase6 perf smoke...
[phase6-perf] voice parse p95: 2.42 ms (target <= 1200 ms)
[phase6-perf] ocr parse p95: 2.27 ms (target <= 2800 ms)
[phase6-perf] offline replay 100 jobs: 116.15 ms (target <= 30000 ms)
[phase6-perf] PASS
[phase6-ready] PASS
[phase6-pack] 3/3 execute external-load gate...
[phase6-load] home_inventory_list: total=400, errors=0, p95=85.93ms, avg=31.27ms, max=228.47ms, throughput=569.67rps, target_p95<=1500ms
[phase6-load] voice_parse: total=120, errors=0, p95=18.65ms, avg=13.18ms, max=19.50ms, throughput=655.64rps, target_p95<=1200ms
[phase6-load] ocr_parse: total=120, errors=0, p95=19.81ms, avg=12.92ms, max=21.28ms, throughput=683.05rps, target_p95<=2800ms
[phase6-load] offline_enqueue_100: 3.35ms (target <= 30000ms)
[phase6-load] PASS
[phase6-pack] PASS
[phase6-pack] Next: complete docs/release/RELEASE_SIGNOFF_TEMPLATE.md and attach UAT/gray evidence.
```

## Summary

- Final status: `PASS`
- Release signoff template: `docs/release/RELEASE_SIGNOFF_TEMPLATE.md`
- UAT checklist: `docs/release/UAT_EXECUTION_CHECKLIST.md`
- Gray runbook: `docs/release/GRAY_RELEASE_RUNBOOK.md`
