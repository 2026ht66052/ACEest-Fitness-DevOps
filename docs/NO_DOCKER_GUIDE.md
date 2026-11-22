# The complete walkthrough — no Docker on your machine

Everything in this assignment runs in **GitHub Codespaces**: a Linux container
in GitHub's cloud that you drive from a browser tab. Docker, Jenkins, Kubernetes
and the application all run there. Nothing is installed on your work laptop, so
no org policy is involved.

**What you need:** a browser, a GitHub account, a Docker Hub account.
**Total time:** about 3 hours, most of it waiting on builds.
**Cost:** zero.

| Component | Where it runs | Why this is allowed |
|---|---|---|
| Docker | inside the Codespace (docker-in-docker) | GitHub's machine, not yours |
| Jenkins | inside the Codespace (Jenkins WAR on Java 17) | ditto |
| Kubernetes | inside the Codespace (k3d — k3s in Docker) | ditto |
| SonarQube | **sonarcloud.io** (SonarQube Cloud, free for public repos) | hosted service, nothing to install |
| Docker Hub | hosted registry | pushed from the Codespace |

> **Budget note.** The GitHub Free plan includes **120 core-hours and 15 GB-month**
> of Codespaces per month. The dev container asks for a 4-core machine, which
> burns 4 core-hours per wall-clock hour → **30 hours/month**. That is plenty,
> but **stop the Codespace when you walk away** (it also auto-stops after 30
> idle minutes). If you want 60 hours instead, change `"cpus": 4` to `2` in
> `.devcontainer/devcontainer.json`.

---

## Stage 0 — Accounts (15 minutes)

1. **GitHub** — <https://github.com/signup>. Use a personal account, not a Sky one.
2. **Docker Hub** — <https://hub.docker.com/signup>. Then
   *Account settings → **Personal access tokens** → **Generate new token***,
   scope **Read & Write**. (The old *Security* page was renamed; if a guide
   mentions Security, this is the page it means.) Copy the token now — it is
   shown once, and you will use the **token**, never your password.
3. **SonarQube Cloud** — <https://sonarcloud.io> → *Log in with GitHub*.

---

## Stage 1 — Push the project to GitHub (20 minutes)

> **Already have an Assignment-1 repository?** Don't create a new one — the
> brief says to continue the same codebase, and the evolution is itself
> evidence. Follow `docs/MERGE_INTO_EXISTING_REPO.md` instead of 1.1/1.2, then
> come back here at Stage 2.2.

### 1.1 Create the repository

GitHub → **New repository**
* Name: `aceest-fitness-devops`
* Visibility: **Public** — required by the assignment, and it is what makes
  SonarQube Cloud free with unlimited lines of code.
* Do **not** add a README or .gitignore (the project has them).

### 1.2 Upload the project

Easiest route with no local git: on the empty repo page click
**uploading an existing file**, drag in the contents of the unzipped project
folder, and commit.

Two things that trip people up:
* Drag the **contents** of `aceest-fitness-devops/`, not the folder itself.
* The browser uploader skips dot-folders. After the upload, check that
  `.devcontainer/`, `.github/`, `.flake8`, `.dockerignore` and `.gitignore`
  are present. If any are missing, use **Add file → Create new file**, type the
  path (e.g. `.devcontainer/devcontainer.json`) and paste the content.

*Alternative:* if `git` is already on your laptop (it usually is, and it is not
Docker), do it properly from a terminal:

```bash
cd aceest-fitness-devops
git init -b main
git add .
git commit -m "feat: initial Flask rewrite of ACEest Fitness desktop app"
git remote add origin https://github.com/<you>/aceest-fitness-devops.git
git push -u origin main
```

### 1.3 Set your Docker Hub username everywhere

You can do this in the Codespace in Stage 2 with one command, which is easier
than editing eight files in the web UI. Skip ahead; it is step 2.3.

---

## Stage 2 — Start the Codespace (20 minutes, mostly unattended)

### 2.1 Launch it

On the repository page: **Code ▾ → Codespaces → Create codespace on main**.

The first build takes 5–10 minutes. It installs Docker, kubectl, Helm, Java 17,
Python 3.12 and k3d, creates the Python virtual environment, runs the test
suite, and creates the Kubernetes cluster. You will see this when it finishes:

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │  ACEest Fitness DevOps lab is ready.                                 │
```

If the banner does not appear, open a terminal (**Ctrl+`**) and run it yourself:

```bash
bash .devcontainer/post-create.sh
```

### 2.2 Verify the cluster

```bash
kubectl get nodes
kubectl -n ingress-nginx get svc
k3d cluster list
```

You should see one `Ready` node and an `ingress-nginx-controller` service on
node port 30090.

### 2.3 Set your Docker Hub username

```bash
export DOCKERHUB_USER=yourname          # <-- your Docker Hub username
grep -rl 2026ht66052 . | xargs sed -i "s/2026ht66052/$DOCKERHUB_USER/g"
grep -rn "2026ht66052" . || echo "all placeholders replaced"

git add -A
git commit -m "ci: set the Docker Hub repository for image publishing"
git push
```

Also add the export to your shell profile so it survives a restart:

```bash
echo "export DOCKERHUB_USER=$DOCKERHUB_USER" >> ~/.bashrc
```

### 2.4 Log in to Docker Hub

```bash
docker login -u "$DOCKERHUB_USER"       # paste the ACCESS TOKEN as the password
```

---

## Stage 3 — Build and publish the images (25 minutes)

### 3.1 Build one image and prove it works

```bash
make docker-build
docker images | grep aceest-fitness

docker run -d --name smoke -p 5000:5000 -e APP_VERSION=3.2.4 "$DOCKERHUB_USER/aceest-fitness:3.2.4"
sleep 5
curl -s localhost:5000/health  | python3 -m json.tool
curl -s localhost:5000/version | python3 -m json.tool
docker rm -f smoke
```

**Screenshot this.** It is your evidence for the containerisation requirement.

### 3.2 Tag every version and push them all

```bash
for v in 1.0 1.1 1.1.2 2.0.1 2.1.2 2.2.1 2.2.4 3.0.1 3.1.2 3.2.4; do
  git tag -a "v$v" -m "ACEest Fitness v$v"
done
git push origin --tags

./scripts/build-all-versions.sh            # builds and pushes all ten + latest
```

This takes 10–15 minutes. Then open
`https://hub.docker.com/r/<you>/aceest-fitness/tags` and **screenshot the tag
list** — that is the "docker image repo with all versions" deliverable.

> If the Codespace stops mid-build, the GitHub Actions fallback does the same
> job on GitHub's runners: repo → **Actions → tests-and-image → Run workflow**,
> tick **all_versions**. Add the `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`
> secrets first under *Settings → Secrets and variables → Actions*.

---

## Stage 4 — SonarQube Cloud (20 minutes)

### 4.1 Import the project

1. <https://sonarcloud.io> → **+ → Analyze new project**
2. Install the SonarQube Cloud GitHub App on your account, grant it
   `aceest-fitness-devops`, and select the repo.
3. Choose **Previous version** as the new-code definition.
4. **Analysis Method → With CI → Other CI** (we drive it from Jenkins).
   Generate a token and copy it.
5. Note your **organization key** and **project key** from the project's
   *Information* page. The project key is usually `<org>_aceest-fitness-devops`.

### 4.2 Run the first analysis from the Codespace

```bash
export SONAR_TOKEN=paste_your_token
export SONAR_ORG=your_org_key
export SONAR_PROJECT=your_project_key

# install the scanner once
curl -fsSLo /tmp/ss.zip https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-6.2.1.4610-linux-x64.zip
sudo unzip -q /tmp/ss.zip -d /opt && sudo ln -sf /opt/sonar-scanner-*/bin/sonar-scanner /usr/local/bin/sonar-scanner

.venv/bin/python -m pytest          # regenerate coverage.xml
sonar-scanner \
  -Dsonar.host.url=https://sonarcloud.io \
  -Dsonar.token="$SONAR_TOKEN" \
  -Dsonar.organization="$SONAR_ORG" \
  -Dsonar.projectKey="$SONAR_PROJECT" \
  -Dsonar.python.coverage.reportPaths=coverage.xml
```

**Screenshot** the project overview (quality gate **Passed**, coverage ~97%) and
the Quality Gate tab. The dashboard URL is public — put it in your report.

> **Worth a line in your report:** SonarQube Cloud is the hosted edition of the
> same product, so the analysis, rules and quality gate are identical to a
> self-hosted SonarQube server. If your instructor insists on the self-hosted
> container specifically, say so and I will give you the self-hosted route —
> it fits in the Codespace too, it is just slower to start.

---

## Stage 5 — Jenkins (40 minutes)

### 5.1 Start it

```bash
bash scripts/codespaces-jenkins.sh
```

It prints the initial admin password. Open the **PORTS** tab at the bottom of
VS Code, find port **8080**, and click the globe icon (*Open in Browser*).

### 5.2 First-run wizard

1. Paste the admin password.
2. **Install suggested plugins** (3–4 minutes).
3. Create your admin user. **Write the credentials down** — you will need them
   after a Codespace restart.
4. Accept the Jenkins URL as offered.

### 5.3 Install the extra plugins

**Manage Jenkins → Plugins → Available plugins**, install and restart:

```
SonarQube Scanner      Docker Pipeline        Kubernetes CLI
HTML Publisher         Pipeline Utility Steps AnsiColor
```

### 5.4 Add the credentials

**Manage Jenkins → Credentials → System → Global credentials → Add Credentials**

| Kind | ID (exactly this) | Value |
|---|---|---|
| Username with password | `dockerhub-creds` | Docker Hub username + **access token** |
| Secret text | `sonar-token` | your SonarQube Cloud token |
| Secret file | `kubeconfig` | see below |

The kubeconfig — run this in the terminal, then download and re-upload the file:

```bash
k3d kubeconfig get aceest > /tmp/kubeconfig-aceest
# right-click /tmp in the Explorer is not possible, so copy it into the workspace:
cp /tmp/kubeconfig-aceest ./kubeconfig-aceest
```

Now right-click `kubeconfig-aceest` in the VS Code Explorer → **Download**, then
upload that file as the `kubeconfig` secret file in Jenkins. Afterwards:

```bash
rm ./kubeconfig-aceest        # never commit a kubeconfig
```

> **This is the step that usually wastes an afternoon with Minikube**, because
> Minikube's kubeconfig points at `127.0.0.1` and references certificates by
> host path. k3d's kubeconfig is self-contained and Jenkins runs on the same
> host as the cluster, so it works as-is. One of the reasons this guide uses
> k3d.

### 5.5 Configure the SonarQube server

**Manage Jenkins → System → SonarQube servers → Add SonarQube**
* Name: `SonarQube` — must match exactly; the pipeline calls `withSonarQubeEnv('SonarQube')`
* Server URL: `https://sonarcloud.io`
* Server authentication token: `sonar-token`
* Tick **Enable injection of SonarQube server configuration as build variables**

**Manage Jenkins → Tools → SonarQube Scanner installations → Add**
* Name: `SonarScanner` — must match the pipeline's `tool 'SonarScanner'`
* **Install automatically**, latest version

Then set your org key in the pipeline:

```bash
sed -i "s/SONAR_ORG        = ''/SONAR_ORG        = '$SONAR_ORG'/" Jenkinsfile
git add Jenkinsfile && git commit -m "ci: point the pipeline at SonarQube Cloud" && git push
```

### 5.6 Create the job

**New Item → Pipeline**, name `aceest-fitness-cicd`.

* **Build Triggers** → tick **Poll SCM**, schedule `H/5 * * * *`
  *(this is the "Jenkins hook that continuously polls the Git repository"
  the assignment asks for — a webhook cannot reach a Codespace reliably, and
  polling is explicitly what the brief requests)*
* **Pipeline**
  * Definition: **Pipeline script from SCM**
  * SCM: **Git**, URL `https://github.com/<you>/aceest-fitness-devops.git`
  * Branch: `*/main`
  * Script Path: `Jenkinsfile`
* Save.

### 5.7 Run it

**Build with Parameters** → `DEPLOY_STRATEGY: rolling`, `APP_VERSION: 3.2.4` → **Build**.

Expect roughly:

```
Checkout                      ✔
Dependencies                  ✔
Static checks (flake8|bandit) ✔
Unit tests (Pytest)           ✔   95 tests, 97% coverage
SonarQube analysis            ✔
Quality gate                  ✔   Passed
Build image                   ✔
Container smoke test          ✔
Push to Docker Hub            ✔
Deploy (rolling)              ✔
Post-deploy verification      ✔
```

**Screenshot the stage view.** Then run it four more times, once per strategy,
and once with a deliberately broken test to capture the automatic rollback.

Common first-run failures:

| Error | Fix |
|---|---|
| `docker: not found` | the pipeline is running on a different agent — there is only one here; restart Jenkins |
| `waitForQualityGate` hangs | in SonarQube Cloud, *Administration → Webhooks* cannot reach a Codespace. Set `SKIP_SONAR` for that build, or run the scanner manually as in Stage 4 and screenshot that instead |
| `unauthorized` on push | the `dockerhub-creds` password must be the **access token** |
| `connection refused` on deploy | the cluster stopped: `bash scripts/codespaces-setup.sh` |

---

## Stage 6 — Deploy all five strategies (40 minutes)

Run these in the Codespace terminal; they are the same scripts Jenkins calls,
and running them by hand gives you clean transcripts to submit.

```bash
export DOCKERHUB_USER=yourname
IMG=$DOCKERHUB_USER/aceest-fitness
```

### 1. Rolling update + rollback

```bash
./scripts/deploy.sh --strategy rolling --image $IMG:3.1.2 --version 3.1.2
./scripts/deploy.sh --strategy rolling --image $IMG:3.2.4 --version 3.2.4
kubectl -n aceest rollout history deploy/aceest-fitness
curl -s localhost:30080/version

./scripts/rollback.sh --strategy rolling
curl -s localhost:30080/version        # back to 3.1.2
```

### 2. Blue-green + rollback

```bash
./scripts/deploy.sh --strategy blue-green --image $IMG:3.2.4 --version 3.2.4
curl -s localhost:30081/version        # still the old colour
curl -s localhost:30083/version        # green preview = new version

./scripts/deploy.sh --strategy blue-green --image $IMG:3.2.4 --version 3.2.4 --promote
curl -s localhost:30081/version        # traffic has moved

./scripts/rollback.sh --strategy blue-green
curl -s localhost:30081/version        # instantly back
```

### 3. Canary

```bash
./scripts/deploy.sh --strategy canary --image $IMG:3.2.4 --version 3.2.4
./scripts/canary-weight.sh 30

# prove the split — expect roughly 14 stable / 6 canary
for i in $(seq 1 20); do curl -s localhost:30080/version; echo; done \
  | grep -o '"track": *"[^"]*"' | sort | uniq -c

./scripts/deploy.sh --strategy canary --image $IMG:3.2.4 --version 3.2.4 --promote
```

### 4. Shadow

```bash
./scripts/deploy.sh --strategy shadow --image $IMG:3.2.4 --version 3.2.4

# generate live traffic, then show the shadow saw copies of it
for i in $(seq 1 10); do curl -s localhost:30090/health > /dev/null; done
kubectl -n aceest logs -l track=shadow --tail=20

# and prove no user traffic is served by it
kubectl -n aceest get endpoints aceest-fitness -o yaml | grep -c shadow || echo "0 shadow endpoints in the live service"
```

### 5. A/B testing

```bash
./scripts/deploy.sh --strategy ab-testing --image $IMG:3.2.4 --version 3.2.4

curl -s localhost:30090/version                      # variant A (control)
curl -s -H 'X-Variant: B' localhost:30090/version    # variant B (experiment)
curl -s localhost:30085/version                      # variant A direct
curl -s localhost:30086/version                      # variant B direct
```

### Final state

```bash
kubectl -n aceest get deploy,svc,ingress,pods -o wide
bash scripts/codespaces-urls.sh
```

---

## Stage 7 — Make the endpoints public and submit (20 minutes)

### 7.1 Publish the ports

In the **PORTS** tab, for each of `30080 30081 30082 30083 30084 30085 30086 30090`:

> right-click → **Port Visibility → Public**

<!-- markdownlint-disable-next-line -->
After that, anyone with the URL can open it without signing in — which is what
your assessor needs. The URLs look like:

```
https://<your-codespace-name>-30080.app.github.dev/
https://<your-codespace-name>-30081.app.github.dev/version
```

Print them all, with a live status check:

```bash
bash scripts/codespaces-urls.sh
```

### 7.2 The honest caveat — put this in your submission

A Codespaces URL is live **only while the Codespace is running**. So:

* Keep the Codespace alive (don't delete it) until you are graded.
* Submit the URLs **and** the terminal transcripts and screenshots. The
  transcripts are complete evidence on their own.
* Add one line to your submission:
  > *The cluster is k3d (k3s in Docker) running in a GitHub Codespace, exposed
  > through GitHub's public port forwarding. Endpoints are live while the
  > Codespace is running; transcripts and screenshots of every strategy are
  > included.*

If you need a permanently reachable URL, the same manifests deploy unchanged to
a managed cluster — change the services from `NodePort` to `LoadBalancer`. Azure
for Students gives $100 of credit with an academic email and no credit card,
which covers an AKS cluster for the grading window.

### 7.3 Evidence checklist

| # | Evidence | Where from |
|---|---|---|
| 1 | Public GitHub repo URL | Stage 1 |
| 2 | Branches, conventional commits, `v1.0`–`v3.2.4` tags | `docs/GIT_WORKFLOW.md` |
| 3 | Docker Hub tag list screenshot | Stage 3.2 |
| 4 | SonarQube Cloud dashboard URL + quality-gate screenshot | Stage 4.2 |
| 5 | Jenkins stage view, ≥3 green builds, 1 rollback build | Stage 5.7 |
| 6 | Coverage report (97%) from the Jenkins artefacts | Stage 5.7 |
| 7 | Endpoint URLs for all five strategies | Stage 7.1 |
| 8 | Canary split counts, blue-green switch, rollback transcripts | Stage 6 |
| 9 | Report | `docs/REPORT.md` |

---

## Day-to-day: restarting work

The Codespace stops when idle. On return:

```bash
# GitHub -> Code -> Codespaces -> click your codespace
bash scripts/codespaces-setup.sh        # restarts the k3d cluster
bash scripts/codespaces-jenkins.sh      # restarts Jenkins
bash scripts/codespaces-urls.sh         # re-check the endpoints
```

Port visibility resets to private on restart, so re-publish the ports when you
need the public URLs again.

Check your quota any time at <https://github.com/settings/billing>.

---

## If Codespaces itself is blocked

Options in order of preference:

1. **Podman instead of Docker, on your laptop.** The assignment explicitly
   allows "Docker **or Podman**". Podman is Apache-2.0, daemonless, rootless and
   carries no Docker Desktop licence, which is what most org policies actually
   prohibit. Worth one email to IT. The `Dockerfile` needs no changes:
   `podman build`, `podman push`, and `alias docker=podman` makes the scripts
   work unaltered.
2. **Google Cloud Shell** — <https://shell.cloud.google.com>, free with any
   Google account, no card, Docker preinstalled, 5 GB persistent home. Sessions
   time out after 20 idle minutes and the VM is ephemeral outside `$HOME`, so
   it suits a demo rather than a long Jenkins session.
3. **A personal cloud VM** you have root on — Azure for Students ($100, no
   card, academic email), GCP's $300/90-day trial, or Oracle Cloud Always Free.
   Choose an **x86_64** shape: Oracle's free tier is ARM, and an ARM-only image
   on Docker Hub will not run on your assessor's x86 machine.
4. **Killercoda / Play with Kubernetes** — free browser scratchpads for the
   Kubernetes parts, with per-session time limits and no persistence. Fine for
   rehearsing the strategies, not for the full pipeline.
