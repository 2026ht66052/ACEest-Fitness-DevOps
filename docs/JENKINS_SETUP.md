# Jenkins + SonarQube setup

Reproducible setup for the build server and the quality gate. Takes about
20 minutes end to end.

## 1. Start the toolchain

```bash
docker compose -f docker-compose.ci.yml up -d
docker compose -f docker-compose.ci.yml ps
```

| Service | URL | Notes |
|---|---|---|
| Jenkins | http://localhost:8080 | unlock password below |
| SonarQube | http://localhost:9000 | `admin` / `admin`, change on first login |

```bash
docker exec aceest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

> SonarQube needs a raised `vm.max_map_count` on Linux hosts:
> `sudo sysctl -w vm.max_map_count=524288`

## 2. Install Jenkins plugins

Manage Jenkins → Plugins → Available. Install, then restart:

* Pipeline, Pipeline: Stage View
* Git, GitHub, GitHub Branch Source
* Docker Pipeline
* SonarQube Scanner
* Kubernetes CLI
* JUnit, HTML Publisher, Coverage
* Credentials Binding, Pipeline Utility Steps
* Timestamper, Workspace Cleanup, AnsiColor

## 3. Install the CLI tools inside the Jenkins container

The pipeline shells out to `python3`, `docker`, `kubectl` and `curl`:

```bash
docker exec -u root aceest-jenkins bash -c '
  apt-get update -qq
  apt-get install -y -qq python3 python3-venv python3-pip curl ca-certificates gnupg
  # docker CLI (the daemon is the hosts, via the mounted socket)
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq && apt-get install -y -qq docker-ce-cli
  # kubectl
  curl -fsSLo /usr/local/bin/kubectl \
    "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
  chmod +x /usr/local/bin/kubectl
  docker --version && kubectl version --client && python3 -V
'
```

## 4. SonarQube: project and token

1. Log in to http://localhost:9000, change the admin password.
2. **Projects → Create project → Manually**
   * Project key: `aceest-fitness`
   * Display name: `ACEest Fitness and Gym`
3. **Analysis method → Locally → Generate a token.** Copy it.
4. **Quality Gates**: the built-in *Sonar way* gate is acceptable. A stricter
   gate matching this project: coverage on new code ≥ 80%, duplicated lines
   ≤ 3%, maintainability/reliability/security rating A, zero new blocker or
   critical issues.

## 5. Jenkins: credentials

Manage Jenkins → Credentials → System → Global credentials → Add:

| Kind | ID | Value |
|---|---|---|
| Username with password | `dockerhub-creds` | Docker Hub username + **access token** (Docker Hub → Account settings → **Personal access tokens** → Generate new token) |
| Secret text | `sonar-token` | the SonarQube token from step 4 |
| Secret file | `kubeconfig` | your kubeconfig (see below) |

Exporting a Minikube kubeconfig that works from inside the Jenkins container:

```bash
kubectl config view --minify --flatten > /tmp/kubeconfig-aceest
# Minikube certs are referenced by path; --flatten embeds them, but the API
# server address must be reachable from the container:
sed -i "s#https://127.0.0.1:[0-9]*#https://$(minikube ip):8443#" /tmp/kubeconfig-aceest
# upload /tmp/kubeconfig-aceest as the `kubeconfig` secret file, then delete it
```

## 6. Jenkins: SonarQube server and scanner

**Manage Jenkins → System → SonarQube servers → Add:**
* Name: `SonarQube`  *(must match `withSonarQubeEnv('SonarQube')`)*
* Server URL: `http://aceest-sonarqube:9000` (container-to-container) or `http://host.docker.internal:9000`
* Server authentication token: `sonar-token`
* Tick **Enable injection of SonarQube server configuration**

**Manage Jenkins → Tools → SonarQube Scanner installations → Add:**
* Name: `SonarScanner`  *(must match `tool 'SonarScanner'`)*
* Install automatically → latest version

## 7. Create the pipeline job

New Item → **Pipeline** → name `aceest-fitness-cicd`.

* **Build Triggers**
  * ☑ *GitHub hook trigger for GITScm polling* (webhook), and/or
  * ☑ *Poll SCM* with schedule `H/5 * * * *` — this is the "Jenkins hook that
    continuously polls the Git repository" the assignment requires.
* **Pipeline**
  * Definition: *Pipeline script from SCM*
  * SCM: Git → your repository URL → branch `*/main`
  * Script Path: `Jenkinsfile`
* Save, then **Build with Parameters**:
  * `DEPLOY_STRATEGY`: pick one of rolling / blue-green / canary / shadow / ab-testing
  * `APP_VERSION`: e.g. `3.2.4`
  * `PROMOTE`: tick to cut traffic over on blue-green/canary

## 8. Edit the Docker Hub username

In `Jenkinsfile`:

```groovy
DOCKERHUB_USER = 'YOUR_DOCKERHUB_USERNAME'   // <-- your username
```

And in the manifests:

```bash
grep -rl YOUR_DOCKERHUB_USERNAME . | xargs sed -i 's/YOUR_DOCKERHUB_USERNAME/yourname/g'
```

## 9. What a green build looks like

```
Checkout                     ✔  12s
Dependencies                 ✔  31s
Static checks (flake8|bandit)✔   8s
Unit tests (Pytest)          ✔  14s   95 tests, 97% coverage
SonarQube analysis           ✔  46s
Quality gate                 ✔   6s   Passed
Build image                  ✔  38s
Container smoke test         ✔  22s   /health /ready /version + pytest in image
Push to Docker Hub           ✔  54s   :3.2.4-42, :3.2.4, :latest
Deploy (rolling)             ✔  41s
Post-deploy verification     ✔  18s   version 3.2.4 confirmed live
```

Artefacts archived per build: `coverage.xml`, `test-results.xml`,
`flake8-report.txt`, `bandit-report.json`, the HTML coverage report, and the
Kubernetes manifests used for the deployment.

## 10. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `docker: command not found` | Step 3 not run, or the socket is not mounted |
| `permission denied /var/run/docker.sock` | Jenkins container must run as root (it does in the compose file) |
| `waitForQualityGate` hangs | SonarQube cannot reach Jenkins — set the webhook under SonarQube → Administration → Configuration → Webhooks to `http://aceest-jenkins:8080/sonarqube-webhook/` |
| `The server could not find the requested resource` on deploy | wrong namespace, or `kubectl apply -f k8s/base/namespace.yaml` was skipped |
| `ImagePullBackOff` | the image tag is not on Docker Hub yet, or `YOUR_DOCKERHUB_USERNAME` was not replaced |
| Pod `CrashLoopBackOff` with a permissions error | `/data` must be writable; the manifests mount an `emptyDir` for exactly this |
