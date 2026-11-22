# Submission checklist

Work top to bottom. Everything marked **YOU** needs your own account values.

> **No Docker on your machine?** Follow `docs/NO_DOCKER_GUIDE.md` instead — it
> covers the same checklist but runs Docker, Jenkins and Kubernetes inside a
> GitHub Codespace and uses the free hosted SonarQube Cloud. Come back here for
> the final evidence list.

## 0. Personalise the repository

```bash
export DOCKERHUB_USER=yourname                 # YOU
grep -rl YOUR_DOCKERHUB_USERNAME . | xargs sed -i "s/YOUR_DOCKERHUB_USERNAME/$DOCKERHUB_USER/g"
grep -rn "<your-username>" docs/               # fix the URLs in docs/REPORT.md
```

## 1. Application and tests

- [ ] `pytest` passes locally — 95 tests, ~97% coverage
- [ ] `flake8 app tests wsgi.py` is clean
- [ ] `flask --app wsgi run` serves <http://localhost:5000>

## 2. GitHub (requirement 2)

- [ ] Repository created and **public**
- [ ] `main` + `develop` pushed, at least a few `feature/*` branches merged via PR
- [ ] Conventional commit messages (see `docs/GIT_WORKFLOW.md`)
- [ ] Annotated tags `v1.0` … `v3.2.4` pushed
- [ ] Branch protection on `main` with the Jenkins check required
- [ ] **Submit:** the repository URL

## 3. Docker Hub (requirement 5)

```bash
docker login
./scripts/build-all-versions.sh
```

- [ ] Repository `<you>/aceest-fitness` is public
- [ ] Tags `1.0 1.1 1.1.2 2.0.1 2.1.2 2.2.1 2.2.4 3.0.1 3.1.2 3.2.4 latest` all present
- [ ] **Submit:** the Docker Hub repository URL + a screenshot of the tag list

## 4. Jenkins (requirement 4 & 7)

Follow `docs/JENKINS_SETUP.md`.

- [ ] Pipeline job `aceest-fitness-cicd` created from SCM
- [ ] SCM polling `H/5 * * * *` **and/or** a GitHub webhook configured
- [ ] At least **3 green builds** on recent commits, visible in build history
- [ ] One build per strategy: rolling, blue-green, canary, shadow, ab-testing
- [ ] One **deliberately failing** build showing the automatic rollback
      (easiest: push a commit that breaks a test, or set `APP_VERSION` to a tag
      that does not exist so the deploy fails)
- [ ] **Submit:** screenshots of the stage view, build history, and the
      archived coverage report

## 5. SonarQube (requirement 7)

- [ ] Project `aceest-fitness` analysed
- [ ] Quality gate shows **Passed**
- [ ] Coverage ≈ 97%, zero blocker/critical issues
- [ ] **Submit:** screenshot of the project overview + the quality gate page.
      Export the report via **Project Information → … → Export** if a file is
      required, and save it as `docs/sonarqube-report.pdf`

## 6. Kubernetes endpoints (requirement 6 — the graded deliverable)

```bash
./scripts/minikube-setup.sh
./scripts/demo-all-strategies.sh
minikube ip
```

Record each URL and its `/version` response:

| Strategy | URL | Expected `track` |
|---|---|---|
| Rolling update | `http://<IP>:30080/` and `/version` | `stable` |
| Blue-green (active) | `http://<IP>:30081/version` | `blue` or `green` |
| Blue preview | `http://<IP>:30082/version` | `blue` |
| Green preview | `http://<IP>:30083/version` | `green` |
| Canary (direct) | `http://<IP>:30084/version` | `canary` |
| A/B variant A | `http://<IP>:30085/version` | `variant-a` |
| A/B variant B | `http://<IP>:30086/version` | `variant-b` |
| Ingress | `curl -H 'Host: aceest.local' http://<IP>/version` | `stable` |
| A/B by header | `curl -H 'Host: aceest.local' -H 'X-Variant: B' http://<IP>/version` | `variant-b` |
| Shadow | `kubectl -n aceest logs -l track=shadow --tail=20` | mirrored requests, no user traffic |

Proof of the canary split:

```bash
for i in $(seq 1 20); do
  kubectl -n aceest run c$i --rm -q --restart=Never --image=curlimages/curl:8.11.0 -- \
    -fsS http://aceest-fitness.aceest.svc.cluster.local/version
done | grep -o '"track": *"[^"]*"' | sort | uniq -c
```

Proof of rollback:

```bash
kubectl -n aceest rollout history deploy/aceest-fitness
./scripts/rollback.sh --strategy rolling
./scripts/smoke-test.sh --namespace aceest
```

- [ ] **Submit:** the endpoint URLs above, plus terminal output/screenshots for
      the canary split, the blue-green switch and the rollback

> If Minikube is not reachable by your assessor, say so explicitly and submit
> the URLs together with the terminal transcripts. For a publicly reachable
> endpoint, deploy the same manifests to a managed cluster (EKS/AKS/GKE) and
> change the services from `NodePort` to `LoadBalancer`.

## 7. Report

- [ ] `docs/REPORT.md` reviewed; placeholders replaced with your URLs
- [ ] Converted to PDF if a PDF is required:
      `pandoc docs/REPORT.md -o docs/REPORT.pdf`
- [ ] **Submit:** the report (2–3 pages)

## 8. Final package

The project folder must contain:

- [x] Flask application files (`app/`, `wsgi.py`) and the legacy versions (`legacy/`)
- [x] `Jenkinsfile`
- [x] `Dockerfile` and Kubernetes manifests (`k8s/`)
- [x] Pytest test cases (`tests/`) and the SonarQube report
- [x] Report (`docs/REPORT.md`)
