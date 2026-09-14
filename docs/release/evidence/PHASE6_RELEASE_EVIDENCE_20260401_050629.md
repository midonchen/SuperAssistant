# Phase 6 Release Evidence Report

- Generated at (UTC): `2026-04-01T05:06:29Z`
- Host: `Darwin misudeMacBook-Air.local 24.6.0 Darwin Kernel Version 24.6.0: Mon Jul 14 11:30:34 PDT 2025; root:xnu-11417.140.69~1/RELEASE_ARM64_T8103 arm64`
- Python: `Python 3.12.1`
- Git revision: `N/A (no git repository)`

## Command Results

### Release Pack Gate

- Command: `make phase6-pack`
- Started (UTC): `2026-04-01T05:06:29Z`
- Ended (UTC): `2026-04-01T05:06:34Z`
- Status: `FAIL`

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
......F...................                                               [100%]
=================================== FAILURES ===================================
____________________ test_provider_quota_guard_local_limit _____________________

    def test_provider_quota_guard_local_limit():
        guard = ProviderQuotaGuard(qps_per_minute=1, token_per_minute=10, token_per_day=100, redis_url="redis://localhost:0/0")
        ok1, reason1 = guard.allow("parser", estimated_tokens=5)
        ok2, reason2 = guard.allow("parser", estimated_tokens=5)
>       assert ok1 is True
E       assert False is True

services/api/tests/test_ai_quota.py:11: AssertionError
=============================== warnings summary ===============================
../../../../Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/dateutil/tz/tz.py:37
  /Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/dateutil/tz/tz.py:37: DeprecationWarning: datetime.datetime.utcfromtimestamp() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.fromtimestamp(timestamp, datetime.UTC).
    EPOCH = datetime.datetime.utcfromtimestamp(0)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED services/api/tests/test_ai_quota.py::test_provider_quota_guard_local_limit
1 failed, 25 passed, 1 warning in 1.06s
make[1]: *** [phase6-pack] Error 1
```

## Summary

- Final status: `FAIL`
- Release signoff template: `docs/release/RELEASE_SIGNOFF_TEMPLATE.md`
- UAT checklist: `docs/release/UAT_EXECUTION_CHECKLIST.md`
- Gray runbook: `docs/release/GRAY_RELEASE_RUNBOOK.md`
