# EIFM WCC & PPM — Corrected Source

## Included fixes
- Codemagic and GitHub Actions build release APK (`app-release.apk`) instead of debug APK.
- Flutter API URL can be changed at build time with `--dart-define=API_BASE_URL=https://your-backend`.
- Saved login token is checked against `/me` when app opens. Offline/network errors do not automatically erase the token.
- Network timeouts for downloads, uploads and PPM submission, and asynchronous file writing.
- UUID-based report folder names prevent same-second collisions.
- Uploaded photos are streamed to disk with 12 MB limits; Excel checklist uploads are validated with a 25 MB limit and atomic replacement.
- SQLite WAL mode and 30-second busy timeout; startup snapshot backup to `data/backups/eifm_latest.db`.
- Android INTERNET permission and UCrop activity configuration for Flutter image cropper.
- Original DOCX, PDF, Excel and logo are copied UNCHANGED. No claim of pixel-perfect generated report output without manual PDF/Excel comparison.

## Important — not yet done
- This package does **not** migrate your production data to PostgreSQL or cloud object storage. Current Render persistent disk must be confirmed, and existing data backed up **off the server** before redeploy.
- This package does **not** include your live database, previous user records or stored photos; those are on the running server, not GitHub.
- Release builds using Flutter's default generated signing configuration may be signed with a debug key. For real public distribution and seamless future upgrades, configure a permanent private Android release keystore in Codemagic/CI secrets; NEVER upload it to GitHub.
- No Flutter SDK is installed in this authoring environment, so APK compilation and device testing have not been run.
- 200 simultaneous users, exact original PDF text positioning, and complete data-loss prevention require separate integration/load tests and production infrastructure.

## Deployment
1. Download and back up Render `/data/eifm_app.db`, `/data/outputs`, `/data/building_checklists` outside Render. Do not delete the old service.
2. Upload this source to a test GitHub branch, keeping the original branch intact.
3. Run the `EIFM Release APK` GitHub Action or Codemagic `eifm-android` workflow.
4. Download `app-release.apk` from build artifacts and install on a test Android phone. If an old APK was signed by a different key, uninstall the old APK **only after preserving data and verifying server records**.
5. Test signup/login/reopen, photo picker and cropper, WCC/PPM generation, Excel equipment selection, and download files.
6. Only then deploy backend changes to production.

## Backend configuration
Set `EIFM_DATA_DIR` to the actual mounted persistent directory if different from `/data`. Keep the server on one instance while using SQLite. Multi-instance production requires a PostgreSQL + cloud-storage migration.
