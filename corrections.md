# AI Pipeline Corrections Log

Document three changes you made to the AI-generated CI/CD workflow and why.

## Correction 1
- **Original AI output:** Actions referenced by floating tag, e.g. `uses: actions/checkout@v4`, `docker/build-push-action@v6`.
- **My fix:** Pinned every action to a full commit SHA with the version in a trailing comment, e.g. `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2`.
- **Why:** Supply-chain security. A mutable tag can be repointed to malicious code; a SHA is immutable. Comment keeps it human-readable + Dependabot can still bump it.

## Correction 2
- **Original AI output:** No `permissions:` block (defaults to broad `GITHUB_TOKEN`), or a single broad top-level grant.
- **My fix:** Top-level `permissions: contents: read` (least privilege). Only the `build` job widens to `packages: write` for GHCR push. `test`/`deploy` stay read-only.
- **Why:** Minimal permissions limit blast radius if a step or dependency is compromised. Each job gets only what it needs.

## Correction 3
- **Original AI output:** `deploy` job runs on any trigger with no guard — would attempt production deploy on pull requests too, and had no environment protection.
- **My fix:** Added `if: github.event_name == 'push' && github.ref == 'refs/heads/main'` and `environment: name: production`. Docker login/push also gated to `push` events only.
- **Why:** PRs (incl. forks) must never deploy to prod or push images. The `environment: production` binding activates GitHub environment protection rules (required reviewers, wait timer, branch limits) as a gate before deploy.

## Summary
- **Total corrections made: 9** (7 numbered workflow corrections + 2 supply-chain hardening fixes)
- **Most common issue category:** Security — supply-chain integrity dominates (SHA pins, base-image digest, dep hash-pinning, provenance)
- **Security issues found & fixed: 9**
  1. Unpinned action tags → SHA-pinned (C1)
  2. Over-broad `GITHUB_TOKEN` permissions → per-job least privilege (C2)
  3. Ungated production deploy → main-only `if` + `environment: production` (C3)
  4. `ubuntu-latest` moving runner → pinned `ubuntu-24.04` (C4)
  5. No dependency vuln scan → `pip-audit` added (C5)
  6. Scan not gating build → split `security` job + `build: needs: [test, security]` (C6)
  7. No build provenance → `attest-build-provenance` + OIDC signing (C7)
  8. Mutable base image tag → digest-pinned `python:3.12-slim@sha256:423ed6ab…` (hardening)
  9. Deps not hash-pinned → `requirements.lock` + `--require-hashes` (hardening)
- **Attack vectors reviewed (supply-chain timeline): 3/3 protected** — mutable tags, exposed secrets, open permissions
- **Security checklist: 7/7 pass.** NCSC Code of Practice: 3/4 principles mapped (P1 secure dev, P2 build env, P3 secure deploy).
- **Verification:** YAML valid; pytest 6/6; docker build (`--no-cache`) verifies base digest + all dep hashes.
- **Open item:** `github.repository` lowercase for GHCR/attestation if org/repo has uppercase.

---

## Correction 4 (security checklist pass)
- **Original AI output:** All jobs `runs-on: ubuntu-latest`.
- **My fix:** Pinned all three jobs to `runs-on: ubuntu-24.04`.
- **Why:** `ubuntu-latest` is a moving target (bumps to next LTS without warning → non-reproducible builds, surprise breakage). Pinning the image version keeps runs deterministic.

## Correction 5 (dependency vulnerability scan)
- **Added:** `pip-audit` to install list + step `Check for known vulnerabilities: run: pip-audit` in the `test` job, before pytest.
- **Why:** Scans installed deps against the PyPI Advisory / OSV vuln DB. Non-zero exit on any known CVE fails the job → `build` and `deploy` never run (both gated by `needs: test`). Fail-fast placement (before pytest) surfaces vuln quickly.

## Correction 6 (split security into own job + gate build)
- **Change:** Moved `pip-audit` out of `test` into a standalone `security` job. Set `build: needs: [test, security]`.
- **Why:** `needs: security` requires a job literally named `security` to exist, else the workflow is invalid. Split also runs test + security in parallel (faster) and makes the failing gate obvious in the UI. Build only runs after both pass.

## Change history (files written)
- `.github/workflows/ci-cd.yml` — created full pipeline: test → build → deploy jobs; push/PR on main triggers; pinned SHAs; least-privilege perms; production environment gate; concurrency cancel; PR builds without push/deploy. Later pinned runners to `ubuntu-24.04`.
- `corrections.md` — this log.

## Correction 7 (build provenance attestation)
- **Added:** In `build` job — perms `id-token: write` + `attestations: write` (kept contents:read, packages:write); `id: build` on the build-push step; new step `Attest build provenance` using `actions/attest-build-provenance@c074443f1aee8d4aeeae555aebba3282517141b2 # v2.2.3`, gated to `push`, `push-to-registry: true`, `subject-digest: ${{ steps.build.outputs.digest }}`.
- **Why:** Generates a signed SLSA provenance attestation binding the image digest to the build (verifiable with `gh attestation verify`). `id-token: write` needed for OIDC keyless signing; `attestations: write` to store it. Gated to push since PRs build no pushed image.
- **✅ SHA verified:** `git ls-remote` → `refs/tags/v2.2.3` = `c074443f1aee8d4aeeae555aebba3282517141b2` (lightweight tag = direct commit). Pin correct.
- **⚠️ Still verify:** `github.repository` case — GHCR + attestation need lowercase; add lowercasing step if org/repo has caps.

## NCSC Mapping
NCSC Software Security Code of Practice — 3 of the 4 principles mapped to pipeline features.

**Principle 1 — Secure design and development**
- `security` job runs `pip-audit` → catches known-vuln dependencies before build (vuln management).
- `test` job runs pytest (6 tests) → verifies behaviour before ship.
- Least-privilege `permissions` per job → secure-by-default design in the build config itself.

**Principle 2 — Build environment security**
- Every action pinned to a commit SHA → build pipeline can't be hijacked by a repointed tag (supply-chain integrity).
- Runner pinned `ubuntu-24.04` → reproducible, known build environment.
- `GITHUB_TOKEN` scoped to `contents: read` by default, widened only where needed → compromised step has minimal reach. No secrets echoed to logs.
- OIDC keyless signing (`id-token: write`) → no long-lived signing secret stored in the build env.

**Principle 3 — Secure deployment and maintenance**
- `actions/attest-build-provenance` → signed SLSA provenance binds image digest to its build; downstream verifiable with `gh attestation verify`.
- Image tagged by immutable `${{ github.sha }}` (never `:latest`) → deployed artifact is traceable to exact source.
- Prod deploy uses `environment: production` + `if` guard on main → protection rules (reviewers/wait/branch) gate release; PRs & forks can't deploy.
- `needs: [test, security]` → nothing deploys unless tests + vuln scan pass.

## Supply-chain hardening gaps (outside the workflow)
Workflow itself: 3/3 attack vectors protected (mutable tags, exposed secrets, open permissions). Two residual gaps live in the Dockerfile / requirements, not the pipeline:

1. **Base image mutable tag** — `Dockerfile` used `FROM python:3.12-slim` (mutable tag). Registry could serve different bits under that tag = same class as unpinned actions. **✅ FIXED:** both `FROM` lines pinned to `python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf`. Verified with `docker build --no-cache`.
2. **Dependencies not hash-pinned** — `requirements.txt` pinned versions but not hashes. `pip-audit` catches *known* CVEs, not a swapped/typo-squatted package. **✅ FIXED:** generated `requirements.lock` (451 lines, full transitive hashes) via `pip-compile --generate-hashes --allow-unsafe`. Dockerfile build stage + both CI jobs (`test`, `security`) now `pip install --require-hashes -r requirements.lock`. `pytest`/`pip-audit` resolve from the lock (removed redundant separate installs). `requirements.txt` = human source; regenerate the lock after editing it. Build verified every hash (`--no-cache`), YAML valid.

## Validation & local verification
- **YAML syntax** — `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci-cd.yml'))"` → VALID (parses clean).
- **Deps install** — `pip install -r requirements.txt` → ok (flask, pytest, pip-audit).
- **Tests** — `pytest test_app.py -v` → **6/6 passed** in 0.04s (health 200, health json, info 200, info name, index 200, 404 route).
- **Docker build** — `docker build -t pipeline-api:test .` → success, tagged `pipeline-api:test`.
- **Note (local only):** `HEALTHCHECK is not supported for OCI image format and will be ignored` — local runtime is podman (OCI default), so Dockerfile `HEALTHCHECK` ignored locally. Works on GitHub Actions runner (real Docker daemon). Silence locally with `podman build --format docker`. No CI change needed.

## Security checklist result (7/7)
- [x] Actions pinned to commit SHAs
- [x] permissions block, specific scopes (not write-all)
- [x] Runner pinned ubuntu-24.04
- [x] No secrets echoed to logs
- [x] Docker image tagged ${{ github.sha }}
- [x] Production deploy uses environment: production
- [x] needs: dependencies enforce stage ordering
