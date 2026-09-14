# Monitoring Baseline

MVP tracks the following operational signals:

- API error rate
- AI parse timeout rate (`AI_504_TIMEOUT`)
- Offline replay failure rate
- Push delivery rate
- App crash rate

Suggested stack in staging/prod:

- Sentry (app + API)
- Grafana + Prometheus
- Alerting on P0/P1 thresholds
