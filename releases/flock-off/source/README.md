# FLOCK OFF — collaboration and public-records research candidate

Version `0.3.0+collaboration.1`. Coauthored by **Frazer Σ Love ACO-Σ** and **Sara ΣΩ ACO-Ω**. Combined distribution: AGPL-3.0-only; original Apache notices remain intact. See [license map](docs/LICENSE_MAP.md).

**Experimental prerelease candidate.** Software tests use synthetic records. Independent source review is partial and post-fix revalidation remains incomplete after a tool-access restriction. Live Tor privacy, actual sensor hardware and field performance remain unverified. This application does not promise anonymity or independent security clearance. Publication status is recorded separately on GitHub.

## Start on Windows

Use Python 3.12 with Tk installed. The hashed lock targets CPython 3.12 Windows x64; other platforms need separate dependency qualification.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps .
.\.venv\Scripts\flockoff-red-tape-desk.exe
```

Launch the sensor console with `flockoff-sensors`. Command-line help: `flockoff --help`, `flockoff red-tape --help`, `flockoff-red-tape --help`, and `flockoff-relay --help`.

## Choose your work

- **Private notes / Shared room / Council packet** opens neutral encrypted notes, invite-only shared cards, or a reviewed council document. Separate stores and external keys preserve their boundaries. Keep backups and keys separately.
- **Shared room** requires an invitation fingerprint review and explicit room/category consent before app-active automatic sync. The room owner must remain online to grant new sends. The UI queues locally when unavailable. Current heads show conflicts; a merge names the selected parent revisions. Original files and private databases are not automatically shared. Text you enter may identify you.
- **Council packet** creates a neutral title and random reference before preview. Unbranded output is the default. Presenter identity disclosure is optional and explicit; collaborators are not automatically identified. Each new byte variant needs its own approval; an approved reprint keeps identical bytes. Renaming does not make documents unlinkable.
- **Public records research** starts disabled. Choose public scope, approved static HTTPS URLs and access-rule consent. The app checks at bounded rates while open, through Tor SOCKS5h with no direct fallback. It stores source revisions, excerpts, dates, unresolved questions and exact status distinctions. Public research never queries private vaults or rooms. Source-bound BLOOMCORE conductance memory provides advisory related-item distances, not truth or confidence scores.
- The existing **Records desk** builds speaking briefs, evidence appendices, question assessments, answer tracking and an offline Town Hall timer from deliberately supplied records. It never files requests or sends council submissions automatically.
- **Sensor console** handles decoded input, synthetic replay and host serial sessions with receipts. No native radio receiver or physical hardware performance is claimed.
- **Release the Hounds** plays a short synthetic bark only after a click, with text fallback. **Bureaucracy Simulator** is optional fictional satire with bounded randomized stages, an obvious exit and an absurd final rejection. Neither alters real validation or records.

## Collaboration setup and privacy

No hosted relay or Tor service is supplied. [Setup](docs/COLLABORATION_SETUP.md) describes the self-hostable local relay and owner endpoint. Collaboration remote destinations must be valid Tor v3 onions; public research uses a separate approved-HTTPS profile through Tor. No credentials, service, firewall or onion configuration is created automatically.

Removal blocks new owner grants. A previously issued exact in-flight batch has a bounded residual window; recipients may retain older plaintext. Relay timing/volume and endpoint compromise remain risks. Read [protocol and limits](docs/COLLABORATION_PROTOCOL.md), [workspace flows](docs/WORKSPACE_PATHS.md), [research](docs/RESEARCH_AGENT.md), and [public memory lineage](docs/PUBLIC_MEMORY.md).

## Verify and build

```powershell
.\.venv\Scripts\python.exe tools/verify_release.py
.\.venv\Scripts\python.exe tools/check_desktop.py
.\.venv\Scripts\python.exe tools/check_sensors.py
```

Additional native harnesses cover Hounds, simulator, workspace paths and research UI. See [build notes](BUILD.md). Historical baseline receipts and [sensor-console README](docs/HISTORICAL_SENSORCONSOLE_README.md) describe earlier candidates and do not qualify this successor. Final release manifest, wheel, ZIP and exact-commit receipts are produced only after expanded checks and independent review.
