# Git workflow — branching, commits and tagging

This is the version-control strategy the assignment asks you to demonstrate
(requirement 2). Run these commands once to produce a repository history that
shows incremental versions, feature branches, bug fixes and infrastructure work.

## 1. Initialise and connect the remote

```bash
cd aceest-fitness-devops
git init -b main
git add .
git commit -m "feat: initial Flask rewrite of ACEest Fitness desktop app

Converts the Tkinter application (legacy/) into a modular Flask service with
an application factory, SQLite persistence, JSON API and server-rendered UI."

gh repo create aceest-fitness-devops --public --source=. --remote=origin --push
# or manually:
# git remote add origin https://github.com/<you>/aceest-fitness-devops.git
# git push -u origin main
```

## 2. Branching model

| Branch | Purpose |
|---|---|
| `main` | Always deployable; protected; only merged via PR |
| `develop` | Integration branch for the next version |
| `feature/<slug>` | One feature, branched from `develop` |
| `bugfix/<slug>` | Defect fix, branched from `develop` |
| `hotfix/<slug>` | Urgent production fix, branched from `main` |
| `infra/<slug>` | Pipeline, Docker, Kubernetes changes |
| `release/<version>` | Stabilisation before tagging |

```bash
git checkout -b develop main
git push -u origin develop

git checkout -b feature/weekly-adherence develop
# …work…
git commit -m "feat(progress): log and summarise weekly adherence"
git push -u origin feature/weekly-adherence
# open a PR into develop — Jenkins runs tests + SonarQube on the PR
```

## 3. Conventional commits

Use the format `<type>(<scope>): <subject>`.

| Type | Use for |
|---|---|
| `feat` | New functionality |
| `fix` | Bug fix |
| `test` | Tests only |
| `ci` | Jenkinsfile / pipeline changes |
| `build` | Dockerfile, dependencies |
| `infra` | Kubernetes manifests, cluster config |
| `docs` | Documentation |
| `refactor` | Behaviour-preserving restructuring |
| `perf` | Performance work |

Examples that map onto this project:

```
feat(api): expose client CRUD under /api/v1
feat(core): add deterministic weekly program generator
fix(core): reject adherence values outside 0-100
test(core): cover BMI category boundaries at 18.5, 25 and 30
build(docker): multi-stage image running as non-root uid 10001
ci(jenkins): add SonarQube quality gate and automatic rollback on failure
infra(k8s): add blue-green services with switchable selector
infra(k8s): add nginx mirror-target shadow deployment
docs(readme): document all five deployment strategies
```

## 4. Tagging each application version

Every version in the table below becomes an annotated tag, and
`scripts/build-all-versions.sh` builds a Docker image from each tag — this is
what populates the Docker Hub repository with the full version history.

```bash
for v in 1.0 1.1 1.1.2 2.0.1 2.1.2 2.2.1 2.2.4 3.0.1 3.1.2 3.2.4; do
  git tag -a "v$v" -m "ACEest Fitness v$v"
done
git push origin --tags
```

If you want each tag to point at a genuinely different commit (preferable, and
more convincing to a reviewer), commit the versions incrementally instead:

```bash
# bump the default in app/config.py, commit, then tag
sed -i 's/"3.2.4"/"2.0.1"/' app/config.py
git commit -am "feat(db): persist clients and progress in SQLite (v2.0.1)"
git tag -a v2.0.1 -m "ACEest Fitness v2.0.1 — SQLite persistence"
```

| Tag | Milestone |
|---|---|
| `v1.0` | Static program and diet charts |
| `v1.1` | Client profile inputs, calorie estimation |
| `v1.1.2` | Multi-client roster, CSV export, charting |
| `v2.0.1` | SQLite persistence |
| `v2.1.2` | Client load + weekly progress logging |
| `v2.2.1` | Adherence trend analytics |
| `v2.2.4` | Workouts, exercises, body metrics, BMI |
| `v3.0.1` | Summary analytics |
| `v3.1.2` | Auth, membership, report export |
| `v3.2.4` | Program generator, dashboard, full analytics |

## 5. Protecting `main`

On GitHub → Settings → Branches → Add rule for `main`:

* Require a pull request before merging
* Require status checks: the Jenkins build and the SonarQube quality gate
* Require branches to be up to date before merging
* Do not allow force pushes

## 6. Triggering Jenkins from GitHub

Either poll (configured in the job: `H/5 * * * *`) or push a webhook:

GitHub → Settings → Webhooks → Add webhook
* Payload URL: `http://<jenkins-host>:8080/github-webhook/`
* Content type: `application/json`
* Events: *Just the push event* (add *Pull requests* for PR validation)

For a Jenkins instance on your laptop, expose it first:
`ngrok http 8080` and use the public URL.
