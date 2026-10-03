# Doka Mobile — Legacy Prototype Status

This is a retained Expo / React Native prototype. It is **not currently a production-ready mobile client** for either the Personal Local Edition or the stateless Cloud API. The current mobile screens still target the legacy enterprise API contract; the active Personal Local and Cloud API entry points expose different route/authentication contracts.

## Current scope

Implemented in this repository:
- Login session token storage with Expo SecureStore.
- Document list/detail screens for the legacy API contract.
- File and image picker integration.
- Normalization of Expo picker results into a React Native multipart file descriptor.
- A Node built-in regression test suite for picker result normalization.

Not implemented or not verified:
- Resumable/background upload across app suspension or network loss.
- Image thumbnail caching / cache invalidation.
- Offline document synchronization and conflict resolution.
- Current Personal Local / Cloud API adapter and end-to-end authentication compatibility.
- iOS/Android device permission prompts and release signing.
- App Store / Play Store readiness.

## Toolchain

The package currently declares Expo SDK 50 / React Native 0.73. Do not upgrade these independently: align Expo, React Native, native modules and EAS build profiles as one tested SDK upgrade. There is no committed mobile lockfile, so dependency reproducibility and vulnerability status remain unverified.

Install and run after selecting a compatible Node.js version for the declared Expo SDK:

```sh
cd mobile
npm install
npm start
```

Run the pure utility regression tests:

```sh
npm test
```

## API configuration and compatibility

Set the public build-time variable `EXPO_PUBLIC_API_BASE_URL` to the trusted API base ending in `/api`. Examples:
- iOS simulator: `http://localhost:8000/api`
- Android emulator: `http://10.0.2.2:8000/api`
- Physical device: use the development computer's private LAN address and ensure both devices are on the same trusted network.

Do not expose a local DMS port to the public internet. Do not put secrets in `EXPO_PUBLIC_*` variables.

The current screens expect these legacy endpoints:
- `POST /auth/login`
- `POST /auth/logout`
- `GET /documents`
- `POST /documents/upload`
- `GET /documents/{id}`
- `DELETE /documents/{id}`
- `POST /search/advanced`
- `GET /admin/analytics/dashboard`

The active Personal Local app exposes workspace/import routes rather than this legacy document API. The separate Cloud API uses Supabase Auth and its own document contract. A deliberate API adapter and two-user/security tests are required before connecting this prototype to either edition.

## Upload limitations

Uploads currently use a single multipart HTTP request. A failed request must be retried from the beginning; no chunk checkpoint, background transfer task, server-side multipart session, or resume token exists yet. Do not describe this as resumable upload.

The picker normalization utility accepts both Expo's asset-array and legacy single-asset result shapes, handles cancellation, validates the URI, and supplies a MIME fallback. The upload API converts that descriptor into the React Native FormData file shape.

## Release and security gates

Before a mobile release:
- Align the API adapter with the selected Doka edition.
- Upgrade Expo SDK and native dependencies together, generate and review a lockfile, and run dependency audit.
- Add real-device upload interruption/resume tests before implementing a background uploader.
- Add image cache policy and test eviction/privacy behavior before caching private document previews.
- Declare and test iOS photo-library/camera and Android media permissions in Expo app configuration.
- Complete iOS/Android build, signing, privacy and store-readiness checks.

No mobile build, device test, store submission or production API activation is claimed by this repository documentation.
