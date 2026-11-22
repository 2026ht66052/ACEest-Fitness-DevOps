# ACEest Fitness & Gym — CI/CD Implementation Report

**Role:** DevOps Engineer
**Repository:** `https://github.com/<your-username>/aceest-fitness-devops`
**Container registry:** `https://hub.docker.com/r/<your-username>/aceest-fitness`
**Date:** 2026-11-22

---

## 1. CI/CD architecture overview

### 1.1 From desktop application to deployable service

The starting point was ten incremental versions of a Tkinter desktop
application (`legacy/Aceestver-*.py`), ranging from static program charts
(v1.0) to a SQLite-backed system with authentication, workout logging, body
metrics and report export (v3.2.4). A Tkinter application cannot be
containerised and health-checked meaningfully — it requires a display server
and has no network interface — so the first engineering task was a
**refactor to a twelve-factor web service** while preserving every business
rule and the existing database schema.

The result is four clearly separated modules:

| Module | Responsibility | Why it matters for CI |
|---|---|---|
| `app/core.py` | Pure business rules: calorie factors, BMI banding, validation, program generation | No Flask or DB imports, so it is unit-testable in milliseconds and carries most of the coverage |
| `app/db.py` | SQLite schema and access helpers | Same five tables as the desktop versions, so existing data files still open |
| `app/api.py` | JSON API under `/api/v1` | Lets the pipeline assert behaviour over HTTP against a running container |
| `app/web.py` | Server-rendered UI | Replaces the Tkinter window; verified by the smoke test |

Three operational endpoints were added specifically to make the delivery
pipeline observable: `/health` (liveness), `/ready` (readiness, which actually
queries the database) and `/version`, which returns the running version, the
deployment *track* and the pod name. Every response also carries
`X-App-Version` and `X-App-Track` headers. This single design decision is what
makes all five deployment strategies verifiable from outside the cluster — a
reviewer can `curl /version` and see exactly which variant answered.

### 1.2 Pipeline topology

```
  Developer ── git push ──▶ GitHub ──(webhook / SCM poll H/5 * * * *)──▶ Jenkins
                                                                            │
   ┌────────────────────────────────────────────────────────────────────────┘
   ▼
  CONTINUOUS INTEGRATION
   1 Checkout            git metadata, build naming
   2 Dependencies        isolated venv from requirements-dev.txt
   3 Static checks       flake8 ∥ bandit                        (parallel stage)
   4 Unit tests          pytest — 95 tests, --cov-fail-under=85
   5 SonarQube           sonar-scanner, coverage.xml ingested
   6 Quality gate        waitForQualityGate abortPipeline: true
   ▼
  CONTINUOUS DELIVERY
   7 Build image         multi-stage Docker, non-root uid 10001
   8 Container test      /health /ready /version + pytest executed INSIDE the image
   9 Push                Docker Hub :<ver>-<build>, :<ver>, :latest
   ▼
  CONTINUOUS DEPLOYMENT
  10 Deploy              scripts/deploy.sh --strategy {rolling|blue-green|canary|shadow|ab-testing}
  11 Verify              scripts/smoke-test.sh asserts the expected version is live
   ▼
  post { failure { scripts/rollback.sh } }        ◀── automatic revert
```

The pipeline is parameterised (`DEPLOY_STRATEGY`, `APP_VERSION`, `PROMOTE`),
so the same `Jenkinsfile` demonstrates every delivery strategy without
duplication. Quality gates are *blocking*, not advisory: a coverage drop below
85% or a red SonarQube gate aborts the build before any image is pushed, which
means a broken artefact can never reach the registry.

### 1.3 Containerisation

The image is a two-stage build: stage one compiles dependency wheels, stage two
installs them into a slim runtime with no compiler present. It runs as an
unprivileged user (uid 10001) with a read-only root filesystem, all Linux
capabilities dropped, and `allowPrivilegeEscalation: false` in the pod spec.
Gunicorn serves the app with `gthread` workers and `max_requests` recycling,
which is what makes rolling updates genuinely graceful: in-flight requests
complete before a worker exits.

### 1.4 Orchestration and progressive delivery

Five strategies are implemented against a k3d cluster (k3s in Docker) running
in a GitHub Codespace; the same manifests apply unchanged to Minikube or a
managed cluster:

| Strategy | Mechanism | Rollback |
|---|---|---|
| **Rolling update** | `maxUnavailable: 0`, `maxSurge: 1`, readiness-gated; PDB `minAvailable: 2`; HPA 3→8 pods | `kubectl rollout undo` (revision history kept) |
| **Blue-green** | Two full deployments; `aceest-fitness-active` service selector names the live colour | Patch the selector back — atomic, sub-second |
| **Canary** | Stable + canary behind one service; share set by replica ratio, refined by nginx `canary-weight` | Scale canary to 0 / weight 0 |
| **Shadow** | Shadow pods omit the `role: serving` label so no user traffic can reach them; nginx `mirror-target` (or Istio `mirrorPercentage: 100`) copies live traffic | Delete the deployment — nothing user-facing changed |
| **A/B testing** | Deterministic routing on `X-Variant: B` header/cookie via `canary-by-header` | Delete the variant-B ingress |

The distinction between canary and A/B testing is deliberate and was a design
decision rather than a configuration detail. A canary answers *"is this build
safe?"* and therefore splits traffic **randomly** by percentage. An A/B test
answers *"which variant converts better?"* and therefore needs **sticky,
deterministic** assignment so that a user's behaviour can be attributed to one
variant. Implementing both with the same percentage mechanism would have
satisfied the manifest requirement while missing the point.

---

## 2. Challenges faced and mitigation strategies

**1. A GUI application is not deployable.**
Tkinter needs a display; there is no HTTP surface to probe, so liveness and
readiness probes, smoke tests and traffic-splitting are all impossible.
*Mitigation:* refactored to Flask with an application factory, extracting every
business rule into `app/core.py` first so the refactor could be proven
behaviour-preserving by unit tests before any infrastructure work began.

**2. Business logic was entangled with widget callbacks.**
In the original code, the calorie calculation lived inside a button handler and
the BMI banding inside a `messagebox` call — untestable without a running GUI.
*Mitigation:* separated pure functions from I/O. `core.py` now holds 121
statements at 98% coverage, including the BMI boundary cases at exactly 18.5,
25 and 30, which the original code got right only by accident of ordering.

**3. The program generator was non-deterministic.**
v3.1.2 used `random.sample` with no seed, so the same input produced different
plans and no assertion was possible.
*Mitigation:* `generate_program()` accepts an optional `seed`. Production calls
omit it and stay random; tests pass a seed and assert exact output, plus
property-style assertions that sets/reps always fall inside the band for the
requested experience level.

**4. Shadow deployments silently receiving real traffic.**
The first iteration gave shadow pods the same labels as stable pods, so the
service happily load-balanced *production* requests onto an unverified build —
the exact failure mode shadow testing exists to prevent.
*Mitigation:* traffic membership is now an explicit, separate label
(`role: serving`). The shadow template omits it, so inclusion in the live
service is opt-in rather than accidental. The canary and rolling manifests
carry it; the shadow manifest documents its absence in a comment so nobody
re-adds it.

**5. Canary percentages were coarse.**
With three stable replicas, the finest achievable canary share was 25%, which
is far too much exposure for a first look at a new build.
*Mitigation:* layered two mechanisms. `canary-weight.sh` scales to a ten-replica
total so each replica equals 10%, and the nginx `canary-weight` annotation
provides per-request precision down to 1% where the ingress controller is
available. The script applies both, and falls back cleanly when no ingress
controller exists.

**6. Jenkins could not build images.**
The Jenkins container has no Docker daemon, so `docker build` failed.
*Mitigation:* docker-outside-of-docker — the host socket is mounted and only the
Docker *CLI* is installed in the container. This avoids privileged
docker-in-docker while keeping builds fast through the host's layer cache.

**7. Minikube's kubeconfig is unusable from a container.**
It points at `127.0.0.1` and references certificates by host path.
*Mitigation:* `kubectl config view --minify --flatten` embeds the certificates,
and the API server address is rewritten to the Minikube IP before the file is
uploaded as a Jenkins secret file. Documented in `docs/JENKINS_SETUP.md` §5
because it costs an hour to rediscover.

**8. Smoke tests needed an externally reachable address.**
Asserting against a NodePort ties the pipeline to one cluster topology and
breaks on managed Kubernetes.
*Mitigation:* `smoke-test.sh` runs a throwaway `curlimages/curl` pod *inside*
the cluster and talks to the service's DNS name. The same script therefore
works unchanged on Minikube, EKS, AKS and GKE, and it can target any single
track (`--service aceest-fitness-canary`) to verify a variant before it is
promoted.

**9. A failed deployment left a broken version serving traffic.**
*Mitigation:* `post { failure { … } }` invokes `rollback.sh` with the same
strategy parameter, so every strategy has a matching, tested revert path. Each
deploy also writes a `kubernetes.io/change-cause` annotation, so
`kubectl rollout history` explains what each revision was and why.

**10. No container runtime was permitted on the development machine.**
Organisational policy prohibited installing Docker locally, which would block
containerisation, the registry, the quality gate and the cluster — four of the
seven requirements.
*Mitigation:* moved the entire toolchain off the workstation rather than
weakening the pipeline. A committed dev container (`.devcontainer/`) provisions
Docker-in-Docker, kubectl, Helm, Java and Python inside a GitHub Codespace;
Kubernetes runs as k3d (k3s in Docker) in the same environment; Jenkins runs
from its WAR on that host, which incidentally removes the kubeconfig-rewriting
problem described in challenge 7, because Jenkins and the cluster share a
network namespace. SonarQube moved to the hosted SonarQube Cloud edition, free
and unlimited for public repositories. The environment is now reproducible from
the repository by anyone in about ten minutes — a stronger position than the
original laptop-local setup, since the lab is version-controlled rather than
hand-built. Codespaces' public port forwarding also supplies externally
reachable HTTPS endpoints, which a laptop-local Minikube could never provide.
A GitHub Actions workflow was added purely as a safety net so that image
publishing survives the Codespace being stopped.

**11. Codespaces' proxy breaks host-based ingress rules.**
GitHub rewrites the `Host` header to `<codespace>-<port>.app.github.dev`, so
rules pinned to `aceest.local` matched nothing and the canary-weight and
A/B-by-header demos silently served only the control.
*Mitigation:* added host-less ingress variants under `k8s/codespaces/`, selected
automatically by `scripts/deploy.sh` when the `CODESPACES` environment variable
is present. The host-based manifests remain for Minikube and managed clusters,
so one repository serves both environments.

**12. SonarQube flagged complexity in the validation path.**
`validate_client` reached a cyclomatic complexity of 13 against a limit of 12,
and the quality gate correctly blocked it.
*Mitigation:* extracted `_coerce_number` and `_validate_name_and_program`
helpers. This was a useful demonstration that the gate changes behaviour rather
than decorating the build — the fix was made because the pipeline refused to
proceed.

---

## 3. Key automation outcomes

| Metric | Before | After |
|---|---|---|
| Deployment method | Copy a `.py` file, run it manually on a desktop | `git push` → tested, scanned, containerised, deployed |
| Automated tests | None | 95 Pytest tests, **97% coverage**, enforced at ≥ 85% |
| Static analysis | None | flake8 (clean), bandit, SonarQube blocking quality gate |
| Build reproducibility | Depends on the developer's local Python | Pinned multi-stage image, identical in CI and in-cluster |
| Time from commit to running in-cluster | Manual, hours, error-prone | ~4 minutes, unattended |
| Downtime during release | Full restart | **Zero** — `maxUnavailable: 0` + readiness gating |
| Rollback | Re-send the old file and hope | One command per strategy; automatic on pipeline failure; blue-green reverts in under a second |
| Release risk control | All-or-nothing | 10%/30%/50% canary, zero-impact shadow validation, sticky A/B experiments |
| Version traceability | Ten loose files with versions in the filename | Annotated git tags ↔ immutable Docker Hub tags ↔ `/version` endpoint |
| Security posture | Script run as the desktop user | Non-root uid 10001, read-only rootfs, all capabilities dropped, secrets injected from a Secret |
| Capacity handling | Single process | HPA 3→8 replicas at 70% CPU, PDB keeps 2 pods available during maintenance |

### Evidence to accompany this report

1. Jenkins build history showing green runs on recent commits, with the stage
   view and archived coverage report.
2. SonarQube project page: quality gate **Passed**, coverage 97%, zero blocker
   or critical issues.
3. Docker Hub repository listing tags `1.0` … `3.2.4` and `latest`.
4. `kubectl -n aceest get deploy,svc,ingress` showing all five strategies.
5. `/version` responses proving each traffic split:
   blue-green active colour, a mixed canary sample, variant A vs variant B by
   header, and the shadow pod's logs showing mirrored requests while serving no
   user traffic.
6. `kubectl rollout history deploy/aceest-fitness` with change-cause
   annotations, plus a rollback demonstration.

### Conclusion

The engineering value here was not in wiring the tools together — it was in
making the application *amenable* to automation. Extracting pure business logic
produced a test suite fast enough to run on every commit; adding a `/version`
endpoint and an explicit `role: serving` label turned traffic management from a
hopeful configuration into something assertable; and making the quality gate
blocking meant it changed the code rather than merely reporting on it. The
pipeline is now the only path to production, and every step of it is
reversible.
