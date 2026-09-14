# SuperAssistant Mobile (Flutter)

This is a Flutter skeleton targeting iOS for MVP.

## Prepare

1. Install Flutter SDK.
2. `cd apps/mobile`
3. `flutter pub get`
4. `flutter run -d ios`

## Implemented Screens

- Auth
- Onboarding (3 steps with skip confirmation)
- Home (inventory wall + AI briefing + action dock)
- List (purchase suggestions + filters)
- Log (search/filter + detail sheet)
- Settings (cycle/max stock/notify settings)
- Voice Modal (record/parse/confirm states)
- OCR Modal (shoot/upload/parse/partial states)
- Manual Fill
- Item Detail

## API Integration

- Mobile uses `API_BASE_URL` via dart define.
- Default: `http://localhost:8000/api/v1`

Example:

```bash
flutter run -d ios --dart-define=API_BASE_URL=http://localhost:8000/api/v1
```

Recommended endpoint by environment:

1. iOS Simulator + local API:
   - `http://localhost:8000/api/v1`
2. Real iPhone + local API (same Wi-Fi):
   - `http://<your-lan-ip>:8000/api/v1`
3. Staging:
   - `https://<staging-domain>/api/v1`

Release-style build command:

```bash
flutter build ios --release --dart-define=API_BASE_URL=https://<staging-domain>/api/v1
```
