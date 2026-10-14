# EIFM WCC & PPM — Corrected source package

## Included changes
- Flutter Release APK commands in Codemagic and both GitHub workflows.
- Fixed hard-reset of API URL on each app startup. Build-time `API_BASE_URL` now supported.
- HTTP timeout for list/download and WCC upload; asynchronous file writes.
- Image picker errors are shown instead of crashing silently.
- Unique filenames prevent same-second report overwrites.
- `/health` endpoint for backend checks.
- `.gitignore` excludes sensitive database, outputs and signing keys.

## IMPORTANT — NOT YET DONE
This package is NOT a completed premium cloud migration. The existing backend still uses SQLite and local files. To stop data loss on Render, confirm the paid persistent disk is actually mounted at `/data`, and export/back up the database, `outputs/`, and `building_checklists/` BEFORE deploying. Google Cloud SQL + Cloud Storage migration needs credentials, deployment, data export and testing; cannot be completed inside a source ZIP alone. Current tokens remain database-backed and non-expiring; secure refresh-token migration is pending.

## Android build
1. Upload contents of this folder to a backup/new GitHub branch (do not overwrite live production blindly).
2. Run GitHub Actions `EIFM Android APK Build`, or Codemagic `eifm-android`.
3. Download `app-release.apk` from build artifacts. Release signing may use debug signing unless a production keystore is configured. For future updates, configure and preserve your OWN production signing key.
4. If migrating backend, pass `--dart-define=API_BASE_URL=https://your-real-api-host` in the build command.
5. Check Android Internet permission and cropper activity configuration in the generated Android project. The repository currently creates Android project at build time.

## Verify before production
- Sign in, close/reopen app, sign in after server restart
- Create WCC with two pictures and three signatures
- Download WCC PDF, DOCX and ZIP; compare with original layout
- Create PPM using FCU, DB, SMDB and multi-equipment; compare Excel sheet formatting
- Test 200+ users using staged load tests
- Back up and restore live data

No guarantee of 100% bug-free APK: Flutter/Android build and running Render service cannot be tested in this environment.
