.DEFAULT_GOAL := help
SHELL := /bin/bash

DOCKERHUB_USER ?= 2026ht66052
APP_VERSION    ?= 3.2.4
IMAGE          := $(DOCKERHUB_USER)/aceest-fitness
NAMESPACE      ?= aceest
STRATEGY       ?= rolling

.PHONY: help venv install test lint security coverage sonar run \
        docker-build docker-run docker-push push-all \
        cluster deploy promote rollback smoke demo clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[1;33m%-16s\033[0m %s\n", $$1, $$2}'

install:  ## Create a venv and install dev dependencies
	python3 -m venv .venv
	.venv/bin/pip install --quiet --upgrade pip
	.venv/bin/pip install --quiet -r requirements-dev.txt

test:  ## Run the Pytest suite with coverage
	.venv/bin/python -m pytest

lint:  ## Run flake8
	.venv/bin/flake8 app tests wsgi.py gunicorn.conf.py

security:  ## Run bandit
	.venv/bin/bandit -r app -f json -o bandit-report.json || true
	.venv/bin/bandit -r app

sonar:  ## Run the SonarQube scanner (needs SONAR_TOKEN)
	sonar-scanner -Dsonar.host.url=$${SONAR_HOST_URL:-http://localhost:9000} \
	              -Dsonar.token=$${SONAR_TOKEN}

run:  ## Run the app locally on :5000
	DATABASE_PATH=./data/aceest_fitness.db .venv/bin/flask --app wsgi run --debug --port 5000

docker-build:  ## Build the container image
	docker build --network=host --build-arg APP_VERSION=$(APP_VERSION) \
	             --build-arg GIT_COMMIT=$$(git rev-parse --short HEAD 2>/dev/null || echo dev) \
	             --build-arg BUILD_DATE=$$(date -u +%FT%TZ) \
	             -t $(IMAGE):$(APP_VERSION) -t $(IMAGE):latest .

docker-run: docker-build  ## Build and run the container on :5000
	docker run --rm -p 5000:5000 -e APP_VERSION=$(APP_VERSION) $(IMAGE):$(APP_VERSION)

docker-push:  ## Push the current version to Docker Hub
	docker push $(IMAGE):$(APP_VERSION)
	docker push $(IMAGE):latest

push-all:  ## Build and push every version tag
	DOCKERHUB_USER=$(DOCKERHUB_USER) ./scripts/build-all-versions.sh

cluster:  ## Start Minikube with the required addons
	./scripts/minikube-setup.sh

deploy:  ## Deploy with STRATEGY=rolling|blue-green|canary|shadow|ab-testing
	./scripts/deploy.sh --strategy $(STRATEGY) --image $(IMAGE):$(APP_VERSION) \
	                    --version $(APP_VERSION) --namespace $(NAMESPACE)

promote:  ## Promote the pending blue-green / canary release
	./scripts/deploy.sh --strategy $(STRATEGY) --image $(IMAGE):$(APP_VERSION) \
	                    --version $(APP_VERSION) --namespace $(NAMESPACE) --promote

rollback:  ## Roll back the given STRATEGY
	./scripts/rollback.sh --strategy $(STRATEGY) --namespace $(NAMESPACE)

smoke:  ## Run the in-cluster smoke test
	./scripts/smoke-test.sh --namespace $(NAMESPACE) --expect-version $(APP_VERSION)

demo:  ## Demonstrate all five strategies plus rollback
	DOCKERHUB_USER=$(DOCKERHUB_USER) ./scripts/demo-all-strategies.sh

ci:  ## Everything the pipeline runs, locally
	$(MAKE) lint test docker-build

clean:  ## Remove build and test artefacts
	rm -rf .pytest_cache htmlcov coverage.xml test-results.xml \
	       bandit-report.json flake8-report.txt .scannerwork data
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

# ---------------------------------------------------------------------------
# Codespaces targets (no local Docker required) — see docs/NO_DOCKER_GUIDE.md
# ---------------------------------------------------------------------------
.PHONY: cs-setup cs-jenkins cs-urls cs-reset

cs-setup:  ## Codespaces: create/start the k3d cluster and ingress
	bash scripts/codespaces-setup.sh

cs-jenkins:  ## Codespaces: start Jenkins and print the unlock password
	bash scripts/codespaces-jenkins.sh

cs-urls:  ## Codespaces: print the public endpoint URLs to submit
	bash scripts/codespaces-urls.sh

cs-reset:  ## Codespaces: destroy and rebuild the cluster from scratch
	RECREATE=1 bash scripts/codespaces-setup.sh
