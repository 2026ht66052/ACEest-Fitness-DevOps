# ACEest Fitness & Gym — DevOps CI/CD Implementation

End-to-end CI/CD pipeline for the ACEest Fitness & Gym application: a Flask web
service, Pytest test suite, Jenkins pipeline, SonarQube quality gate, Docker
image published to Docker Hub, and Kubernetes deployment with **five**
progressive delivery strategies plus automated rollback.

> **Before you run anything:** replace `YOUR_DOCKERHUB_USERNAME` with your own
> Docker Hub username in `Jenkinsfile` and in every file under `k8s/`
> (`grep -rl YOUR_DOCKERHUB_USERNAME .` finds them all).

---

## 1. Repository layout

```
aceest-fitness-devops/
├── app/                        # Flask application (modular)
│   ├── __init__.py             #   application factory, /health /ready /version
│   ├── core.py                 #   pure business rules (unit-tested in isolation)
│   ├── db.py                   #   SQLite persistence + schema
│   ├── api.py                  #   JSON API (/api/v1/...)
│   ├── web.py                  #   server-rendered UI
│   ├── templates/              #   Jinja2 templates
│   └── static/style.css
├── wsgi.py                     # Gunicorn entrypoint
├── gunicorn.conf.py
├── tests/                      # Pytest suite (95 tests, 97% coverage)
│   ├── conftest.py
│   ├── test_core.py            #   unit tests for the business rules
│   ├── test_api.py             #   HTTP contract tests
│   ├── test_web.py             #   UI tests
│   └── test_db.py              #   persistence tests
├── Dockerfile                  # multi-stage, non-root, healthcheck
├── .dockerignore
├── docker-compose.yml          # run the app locally
├── docker-compose.ci.yml       # local Jenkins + SonarQube + Postgres
├── Jenkinsfile                 # the CI/CD pipeline
├── sonar-project.properties    # SonarQube analysis configuration
├── pytest.ini / .flake8
├── k8s/
│   ├── base/                   # namespace, config, secret, services, ingress
│   ├── rolling/                # STRATEGY 1 — rolling update + HPA + PDB
│   ├── blue-green/             # STRATEGY 2 — blue & green + switchable service
│   ├── canary/                 # STRATEGY 3 — canary deploy + weighted ingress
│   ├── shadow/                 # STRATEGY 4 — traffic mirroring (nginx + Istio)
│   ├── ab-testing/             # STRATEGY 5 — header-based A/B routing
│   └── codespaces/             # host-less ingress variants for Codespaces
├── scripts/
│   ├── codespaces-setup.sh     # create the k3d cluster inside a Codespace
│   ├── codespaces-jenkins.sh   # run Jenkins inside a Codespace
│   ├── codespaces-urls.sh      # print the public URLs to submit
│   ├── minikube-setup.sh       # bootstrap a local Minikube cluster
│   ├── deploy.sh               # apply any strategy
│   ├── rollback.sh             # revert any strategy
│   ├── canary-weight.sh        # shift canary traffic share
│   ├── smoke-test.sh           # in-cluster post-deploy verification
│   ├── build-all-versions.sh   # build & push every version tag to Docker Hub
│   └── demo-all-strategies.sh  # one-shot demo of all five + rollback
├── .devcontainer/              # GitHub Codespaces: the whole lab, no local Docker
│   ├── devcontainer.json       #   docker-in-docker, kubectl, helm, java, python
│   └── post-create.sh          #   bootstraps the venv, k3d cluster and ingress
├── .github/workflows/
│   └── build-publish.yml       # fallback: build/push images on GitHub runners
├── docs/
│   ├── NO_DOCKER_GUIDE.md      # START HERE if you have no Docker locally
│   ├── REPORT.md               # the 2–3 page submission report
│   ├── GIT_WORKFLOW.md         # branching, commits, tagging strategy
│   ├── JENKINS_SETUP.md        # step-by-step Jenkins + SonarQube setup
│   └── SUBMISSION.md           # checklist + the URLs to submit
└── legacy/                     # the original Tkinter versions, kept for traceability
```

---

## 2. No Docker on your machine? Start here

If you cannot install Docker (org policy, locked-down laptop), the whole
assignment runs in **GitHub Codespaces** — Docker, Jenkins and Kubernetes
execute in GitHub's cloud and you drive them from a browser. SonarQube runs as
the free hosted SonarQube Cloud instead of a container.

**Read `docs/NO_DOCKER_GUIDE.md`** — it is the complete start-to-submission
walkthrough. In short:

```
repo -> Code -> Codespaces -> Create codespace on main      # 5-10 min build
bash scripts/codespaces-jenkins.sh                          # start Jenkins
bash scripts/codespaces-urls.sh                             # the URLs to submit
```

The dev container (`.devcontainer/`) installs Docker-in-Docker, kubectl, Helm,
Java 17, Python 3.12 and k3d, then creates the cluster and runs the tests
automatically. `k8s/codespaces/` holds host-less ingress variants, because
GitHub's port-forwarding proxy rewrites the Host header.

`.github/workflows/build-publish.yml` is a safety net, not a replacement for
Jenkins: it builds and pushes the Docker images on GitHub's runners so the
registry deliverable never depends on your laptop.

---

## 3. Quick start (local, with Docker)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# run the tests
pytest                       # 95 tests, coverage report in htmlcov/

# run the app
flask --app wsgi run --debug --port 5000
# or:  DATABASE_PATH=./data/aceest.db gunicorn -c gunicorn.conf.py wsgi:app
```

Open <http://localhost:5000>.

### Docker

```bash
docker build --build-arg APP_VERSION=3.2.4 -t aceest-fitness:3.2.4 .
docker run --rm -p 5000:5000 -e APP_VERSION=3.2.4 aceest-fitness:3.2.4
curl localhost:5000/health && curl localhost:5000/version
```

---

## 4. Application surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Dashboard (client roster, headline metrics) |
| GET | `/programs` | Program catalogue |
| GET/POST | `/clients/new`, `/clients` | Client intake form |
| GET | `/clients/<name>` | Client profile, BMI, progress, workouts |
| POST | `/clients/<name>/progress` | Log weekly adherence (form) |
| GET | `/health` | **Liveness probe** |
| GET | `/ready` | **Readiness probe** (checks the database) |
| GET | `/version` | Version + track + pod — used to verify traffic splits |
| GET | `/api/v1/programs` | Program catalogue (JSON) |
| POST | `/api/v1/programs/generate` | Generate a weekly plan |
| GET/POST | `/api/v1/clients` | List / create clients |
| GET/DELETE | `/api/v1/clients/<name>` | Fetch / delete a client |
| GET/POST | `/api/v1/clients/<name>/progress` | Weekly adherence |
| GET/POST | `/api/v1/clients/<name>/workouts` | Workout + exercise logging |
| GET/POST | `/api/v1/clients/<name>/metrics` | Body metrics |
| POST | `/api/v1/bmi`, `/api/v1/calories` | Calculators |

Every response carries `X-App-Version` and `X-App-Track` headers, which is how
the deployment-strategy demos prove which pod answered.

---

## 5. Version history

The ten Tkinter versions were consolidated into one Flask codebase; each
version is a git tag and a Docker Hub image tag. See `docs/GIT_WORKFLOW.md`.

| Version | Feature set carried over |
|---|---|
| 1.0 | Static program + diet charts |
| 1.1 | Client inputs, calorie estimation, adherence slider |
| 1.1.2 | Multi-client table, CSV export, progress chart |
| 2.0.1 | SQLite persistence (clients, progress) |
| 2.1.2 | Load client, weekly progress logging |
| 2.2.1 | Adherence trend charting |
| 2.2.4 | Height/goals, workouts, exercises, metrics, BMI |
| 3.0.1 | Client summary analytics, status bar |
| 3.1.2 | Role-based login, membership expiry, PDF report |
| 3.2.4 | Program generator, dashboard, full analytics |

```bash
export DOCKERHUB_USER=yourname
docker login
./scripts/build-all-versions.sh      # pushes 1.0 … 3.2.4 + latest
```

---

## 6. CI/CD pipeline

```
 git push
    │
    ▼
 Jenkins (SCM polling / webhook)
    │
    ├─ Checkout ──────────────── git metadata, build name
    ├─ Dependencies ─────────── venv + requirements-dev.txt
    ├─ Static checks ────────── flake8 ∥ bandit          (parallel)
    ├─ Unit tests ───────────── pytest + coverage, fails under 85%
    ├─ SonarQube analysis ───── sonar-scanner
    ├─ Quality gate ─────────── waitForQualityGate, aborts on failure
    ├─ Build image ──────────── docker build (multi-stage)
    ├─ Container smoke test ─── /health /ready /version + pytest INSIDE the image
    ├─ Push ─────────────────── Docker Hub: :<ver>-<build>, :<ver>, :latest
    ├─ Deploy ───────────────── scripts/deploy.sh --strategy <param>
    └─ Verify ───────────────── scripts/smoke-test.sh
         │
         └─ on failure ──────── scripts/rollback.sh  (automatic)
```

Set-up instructions: **`docs/JENKINS_SETUP.md`**.

Required Jenkins credentials:

| ID | Type | Contents |
|---|---|---|
| `dockerhub-creds` | Username with password | Docker Hub user + access token |
| `sonar-token` | Secret text | SonarQube user token |
| `kubeconfig` | Secret file | kubeconfig for the target cluster |

Start the local toolchain:

```bash
docker compose -f docker-compose.ci.yml up -d
docker exec aceest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
# Jenkins   http://localhost:8080
# SonarQube http://localhost:9000   (admin/admin)
```

---

## 7. Kubernetes deployment

```bash
./scripts/minikube-setup.sh                 # start cluster + ingress + metrics
export DOCKERHUB_USER=yourname
./scripts/demo-all-strategies.sh            # all five strategies + rollback
```

### Strategy 1 — Rolling update

`maxUnavailable: 0`, `maxSurge: 1`, gated by the readiness probe, so capacity
never dips. Kubernetes keeps the revision history, so rollback is one command.

```bash
./scripts/deploy.sh --strategy rolling --image $DOCKERHUB_USER/aceest-fitness:3.2.4 --version 3.2.4
kubectl -n aceest rollout history deploy/aceest-fitness
./scripts/rollback.sh --strategy rolling                 # or --to-revision N
```

### Strategy 2 — Blue-green

Two complete environments; the `aceest-fitness-active` service selector names
the live colour. Promotion and rollback are both a single atomic patch.

```bash
./scripts/deploy.sh --strategy blue-green --image …:3.2.4 --version 3.2.4            # deploy idle colour
./scripts/deploy.sh --strategy blue-green --image …:3.2.4 --version 3.2.4 --promote  # cut traffic over
./scripts/rollback.sh --strategy blue-green                                          # flip back
```

### Strategy 3 — Canary release

Stable and canary deployments share one service, so the replica ratio sets the
traffic share; an nginx `canary-weight` ingress gives per-request precision.

```bash
./scripts/deploy.sh --strategy canary --image …:3.2.4 --version 3.2.4
./scripts/canary-weight.sh 30          # ~30% of traffic
./scripts/deploy.sh --strategy canary --image …:3.2.4 --version 3.2.4 --promote
./scripts/rollback.sh --strategy canary
```

### Strategy 4 — Shadow deployment

The shadow pods deliberately lack the `role: serving` label, so no user request
can ever reach them; nginx `mirror-target` (or an Istio `VirtualService` with
`mirrorPercentage: 100`) copies production traffic to them for observation.

```bash
./scripts/deploy.sh --strategy shadow --image …:3.2.4 --version 3.2.4
kubectl -n aceest logs -l track=shadow -f
./scripts/rollback.sh --strategy shadow
```

### Strategy 5 — A/B testing

Deterministic, sticky routing on the `X-Variant: B` header (or a cookie), so a
given user always sees the same variant and the business metric is attributable.

```bash
./scripts/deploy.sh --strategy ab-testing --image …:3.2.4 --version 3.2.4
IP=$(minikube ip)
curl -H 'Host: aceest.local' http://$IP/version                       # variant A
curl -H 'Host: aceest.local' -H 'X-Variant: B' http://$IP/version      # variant B
./scripts/rollback.sh --strategy ab-testing
```

### Endpoints to submit

| What | URL |
|---|---|
| Dashboard | `http://<minikube-ip>:30080/` |
| Blue-green active | `http://<minikube-ip>:30081/version` |
| Blue / green preview | `:30082` / `:30083` `/version` |
| Canary direct | `http://<minikube-ip>:30084/version` |
| A/B variant A / B | `:30085` / `:30086` `/version` |
| Ingress | `curl -H 'Host: aceest.local' http://<minikube-ip>/version` |

---

## 8. Code quality

```bash
pytest                                       # tests + coverage.xml
flake8 app tests wsgi.py                     # style (clean)
bandit -r app                                # security scan
sonar-scanner -Dsonar.host.url=http://localhost:9000 -Dsonar.token=<token>
```

The pipeline fails the build when coverage drops below 85% or the SonarQube
quality gate is not green.

---

## 9. Documents for submission

* `docs/NO_DOCKER_GUIDE.md` — full walkthrough for a machine without Docker
* `docs/MERGE_INTO_EXISTING_REPO.md` — folding this into your Assignment-1 repo
* `docs/REPORT.md` — CI/CD architecture, challenges, automation outcomes
* `docs/SUBMISSION.md` — checklist and the exact URLs/screenshots to hand in
* `docs/GIT_WORKFLOW.md` — commit, branch and tag conventions
* `docs/JENKINS_SETUP.md` — reproducible Jenkins + SonarQube configuration
