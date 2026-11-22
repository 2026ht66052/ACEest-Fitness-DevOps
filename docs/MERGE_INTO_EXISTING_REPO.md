# Merging this project into your Assignment-1 repository

You already have **`2026ht66052/ACEest-Fitness-DevOps`** with 8 commits. Keep it.
Do **not** create a new repository.

Two reasons:

1. The brief says *"use the same code base that you had used in assignment 1."*
   Continuing the same repo is literally that.
2. Requirement 2 asks you to *"track all incremental versions, new features, bug
   fixes and infrastructure changes through structured commits."* A repository
   that starts with a single-file Flask app and evolves into a full pipeline
   **is** that evidence. A fresh repo throws it away and starts at commit #1.

Your existing repo already has `app.py`, `Dockerfile`, `Jenkinsfile`, `tests/`
and `.github/workflows/`. This project supersedes all of them — but we retire
the old files visibly rather than silently deleting them, because the diff is
part of what is being graded.

---

## Step 1 — Open a Codespace on the existing repo

Go to `https://github.com/2026ht66052/ACEest-Fitness-DevOps` →
**Code ▾ → Codespaces → Create codespace on main**.

It will use a default container for now (your repo has no `.devcontainer/` yet).
That is fine — we only need a terminal and the file explorer at this point.

## Step 2 — Copy the new project in

On your laptop, unzip `aceest-fitness-devops.zip`. Then, in the Codespace's
**Explorer** panel (left sidebar), **drag and drop** everything from *inside*
the unzipped folder onto the file tree.

Drag the **contents**, not the folder — you want `app/`, `k8s/`, `docs/`,
`Jenkinsfile`, `Dockerfile` … landing at the repository root, not inside a
nested `aceest-fitness-devops/` directory.

Confirm the dot-folders made it (drag-and-drop into VS Code keeps them; the
GitHub web uploader does not):

```bash
ls -a
ls .devcontainer .github/workflows
```

You should see `.devcontainer/`, `.github/`, `.dockerignore`, `.flake8`,
`.gitignore`.

## Step 3 — Retire the Assignment-1 files

```bash
mkdir -p legacy
git mv app.py legacy/app_assignment1.py 2>/dev/null || mv app.py legacy/app_assignment1.py
```

Your old `tests/`, `Dockerfile`, `Jenkinsfile`, `pytest.ini` and
`requirements.txt` were overwritten by the drag-and-drop, which is intended —
the new ones are supersets. Check what changed before committing:

```bash
git status
git diff --stat
```

## Step 4 — Commit it as a readable story

Not one giant commit. Stage it in logical pieces so the history reads as
engineering rather than a dump:

```bash
git add legacy/
git commit -m "refactor: retire the Assignment-1 single-file app into legacy/

The Tkinter and single-file Flask versions are kept verbatim for traceability;
they are excluded from SonarQube analysis and from the container image."

git add app/ wsgi.py gunicorn.conf.py requirements.txt requirements-dev.txt
git commit -m "feat: modular Flask service with health, readiness and version endpoints

Extracts the business rules into a pure app/core.py so they can be unit tested
without Flask or a database, and adds /health, /ready and /version so the
deployment strategies are verifiable from outside the cluster."

git add tests/ pytest.ini .flake8
git commit -m "test: 95 Pytest cases covering core logic, API, UI and persistence (97% coverage)"

git add Dockerfile .dockerignore docker-compose.yml docker-compose.ci.yml
git commit -m "build(docker): multi-stage image running as non-root uid 10001"

git add Jenkinsfile sonar-project.properties .github/
git commit -m "ci(jenkins): add SonarQube quality gate, in-container tests and automatic rollback"

git add k8s/
git commit -m "infra(k8s): add rolling, blue-green, canary, shadow and A/B manifests"

git add scripts/ Makefile .devcontainer/
git commit -m "infra: add deployment, rollback and Codespaces bootstrap scripts"

git add docs/ README.md
git commit -m "docs: add CI/CD report, Git workflow, Jenkins setup and submission checklist"

git push
```

## Step 5 — Tag the versions

```bash
for v in 1.0 1.1 1.1.2 2.0.1 2.1.2 2.2.1 2.2.4 3.0.1 3.1.2 3.2.4; do
  git tag -a "v$v" -m "ACEest Fitness v$v"
done
git push origin --tags
```

Your repo page will then show **0 Tags → 10 Tags**, which is the tagging
strategy deliverable.

## Step 6 — Rebuild the Codespace so the dev container takes effect

Now that `.devcontainer/` is committed, the Codespace needs to pick it up:

**Ctrl+Shift+P → Codespaces: Rebuild Container** (choose *Full Rebuild*).

It restarts with Docker-in-Docker, kubectl, Helm, Java 17, Python 3.12 and k3d,
runs the tests and creates the cluster. 5–10 minutes.

If the rebuild misbehaves, delete the Codespace and create a fresh one — the
code is pushed, so nothing is lost.

## Step 7 — Set your Docker Hub username

Your Docker Hub account is **`2026ht66052`**, so:

```bash
export DOCKERHUB_USER=2026ht66052
echo "export DOCKERHUB_USER=2026ht66052" >> ~/.bashrc
grep -rl YOUR_DOCKERHUB_USERNAME . | xargs sed -i "s/YOUR_DOCKERHUB_USERNAME/$DOCKERHUB_USER/g"
grep -rn "YOUR_DOCKERHUB_USERNAME" . || echo "all placeholders replaced"

git add -A
git commit -m "ci: point image builds at the 2026ht66052 Docker Hub repository"
git push
```

Then continue from **Stage 3** of `docs/NO_DOCKER_GUIDE.md`.

---

## A note on your other repos

`Web-Dev` and `PMO-Office` are your DevOps Lab 1 work and `git-lab` is the git
session. Leave them alone — they are separate submissions. Only
`ACEest-Fitness-DevOps` is this assignment.
