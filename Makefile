.PHONY: check api-test api-run phase-status phase5-accept phase6-perf phase6-load phase6-ready phase6-pack phase6-evidence phase6-wave-template phase6-wave-live phase6-wave-gate phase6-wave-exec phase6-wave-exec-final phase6-signoff-draft phase6-signoff-final phase6-window-status phase6-window-gate phase6-window-gate-live phase6-local-sim phase6-handoff-pack

check:
	npm run check:all

api-test:
	cd services/api && python3 -m pytest -q

api-run:
	cd services/api && uvicorn main:app --reload

phase-status:
	python3 scripts/report_phase_status.py

phase5-accept:
	bash scripts/run_phase5_acceptance.sh

phase6-perf:
	python3 scripts/run_phase6_perf_smoke.py

phase6-load:
	python3 scripts/run_phase6_external_load.py

phase6-ready:
	bash scripts/run_phase6_release_readiness.sh

phase6-pack:
	bash scripts/run_phase6_release_pack.sh

phase6-evidence:
	bash scripts/generate_phase6_release_evidence.sh

phase6-wave-template:
	@test -n "$(WAVE)" || (echo "Usage: make phase6-wave-template WAVE=10|50|100" && exit 1)
	python3 scripts/record_gray_wave_checkpoint.py --wave $(WAVE) --mode template

phase6-wave-live:
	@test -n "$(WAVE)" || (echo "Usage: make phase6-wave-live WAVE=10|50|100 [API_BASE_URL=...]" && exit 1)
	python3 scripts/record_gray_wave_checkpoint.py --wave $(WAVE) --mode live

phase6-wave-gate:
	@test -n "$(WAVE)" || (echo "Usage: make phase6-wave-gate WAVE=10|50|100 [STRICT=1]" && exit 1)
	python3 scripts/evaluate_gray_wave_gate.py --wave $(WAVE) $(if $(STRICT),--require-continue,)

phase6-wave-exec:
	@test -n "$(WAVE)" || (echo "Usage: make phase6-wave-exec WAVE=10|50|100 [API_BASE_URL=...]" && exit 1)
	bash scripts/run_gray_wave_execution.sh $(WAVE)

phase6-wave-exec-final:
	@test -n "$(WAVE)" || (echo "Usage: make phase6-wave-exec-final WAVE=100 [API_BASE_URL=...]" && exit 1)
	bash scripts/run_gray_wave_execution.sh $(WAVE) --finalize

phase6-signoff-draft:
	python3 scripts/generate_release_signoff_draft.py

phase6-signoff-final:
	python3 scripts/finalize_release_signoff.py

phase6-window-status:
	python3 scripts/check_release_window_readiness.py

phase6-window-gate:
	python3 scripts/check_release_window_readiness.py --strict

phase6-window-gate-live:
	python3 scripts/check_release_window_readiness.py --strict --require-non-local-wave-evidence

phase6-local-sim:
	bash scripts/run_phase6_local_release_simulation.sh

phase6-handoff-pack:
	python3 scripts/build_release_handoff_package.py
