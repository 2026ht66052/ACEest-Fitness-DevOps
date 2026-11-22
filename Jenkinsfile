// ---------------------------------------------------------------------------
// ACEest Fitness & Gym — CI/CD pipeline
//
// Stages: checkout -> dependencies -> lint -> unit tests (Pytest + coverage)
//         -> SonarQube analysis -> quality gate -> Docker build -> container
//         smoke test -> push to Docker Hub -> deploy to Kubernetes with the
//         selected strategy -> post-deploy verification -> rollback on failure.
//
// Required Jenkins credentials (Manage Jenkins -> Credentials):
//   dockerhub-creds  : Username/password  (Docker Hub user + access token)
//   sonar-token      : Secret text        (SonarQube user token)
//   kubeconfig       : Secret file        (kubeconfig for the target cluster)
//
// Required Jenkins tools / plugins:
//   SonarQube Scanner plugin + a scanner installation named "SonarScanner"
//   A SonarQube server configuration named "SonarQube"
//   Docker Pipeline, Kubernetes CLI, Git, Pipeline Utility Steps
// ---------------------------------------------------------------------------

pipeline {
  agent any

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '20'))
    timeout(time: 45, unit: 'MINUTES')
    disableConcurrentBuilds()
  }

  parameters {
    choice(
      name: 'DEPLOY_STRATEGY',
      choices: ['rolling', 'blue-green', 'canary', 'shadow', 'ab-testing', 'none'],
      description: 'Progressive delivery strategy to use for this deployment'
    )
    string(name: 'APP_VERSION', defaultValue: '3.2.4', description: 'Semantic version / image tag')
    booleanParam(name: 'PROMOTE', defaultValue: false,
                 description: 'Blue-green / canary: cut 100% of traffic to the new version')
    booleanParam(name: 'SKIP_SONAR', defaultValue: false,
                 description: 'Skip SonarQube analysis (use only when the server is offline)')
  }

  environment {
    DOCKERHUB_USER   = 'YOUR_DOCKERHUB_USERNAME'          // <-- change me
    IMAGE_NAME       = "${DOCKERHUB_USER}/aceest-fitness"
    IMAGE_TAG        = "${params.APP_VERSION}-${env.BUILD_NUMBER}"
    K8S_NAMESPACE    = 'aceest'
    SONAR_PROJECT_KEY = 'aceest-fitness'
    // Required by SonarQube Cloud (sonarcloud.io); leave empty for a
    // self-hosted SonarQube server, where it is not used.
    SONAR_ORG        = ''
    VENV             = '.venv'

    // Parameters exported into the shell environment so the `sh` steps below
    // can reference them without Groovy string interpolation (safer: no
    // secrets or user input is baked into the generated script).
    APP_VERSION_ARG     = "${params.APP_VERSION}"
    DEPLOY_STRATEGY_ARG = "${params.DEPLOY_STRATEGY}"
    PROMOTE_FLAG        = "${params.PROMOTE ? '--promote' : ''}"
  }

  stages {

    stage('Checkout') {
      steps {
        checkout scm
        script {
          env.GIT_COMMIT_SHORT = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
          env.BUILD_DATE = sh(script: 'date -u +%Y-%m-%dT%H:%M:%SZ', returnStdout: true).trim()
          currentBuild.displayName = "#${env.BUILD_NUMBER} v${params.APP_VERSION} (${env.GIT_COMMIT_SHORT})"
          currentBuild.description = "strategy=${params.DEPLOY_STRATEGY}"
        }
        sh 'git log --oneline -5'
      }
    }

    stage('Dependencies') {
      steps {
        sh '''
          set -eu
          python3 -m venv ${VENV}
          ${VENV}/bin/pip install --quiet --upgrade pip
          ${VENV}/bin/pip install --quiet -r requirements-dev.txt
          ${VENV}/bin/pip --version
        '''
      }
    }

    stage('Static checks') {
      parallel {
        stage('Flake8') {
          steps {
            sh '${VENV}/bin/flake8 app tests wsgi.py --output-file=flake8-report.txt --tee || true'
          }
        }
        stage('Bandit (security)') {
          steps {
            sh '${VENV}/bin/bandit -r app -f json -o bandit-report.json || true'
          }
        }
      }
    }

    stage('Unit tests (Pytest)') {
      steps {
        sh '''
          set -eu
          ${VENV}/bin/python -m pytest \
            --cov=app \
            --cov-report=xml:coverage.xml \
            --cov-report=html:htmlcov \
            --cov-fail-under=85 \
            --junitxml=test-results.xml \
            -v
        '''
      }
      post {
        always {
          junit allowEmptyResults: false, testResults: 'test-results.xml'
          publishHTML(target: [
            reportDir: 'htmlcov', reportFiles: 'index.html',
            reportName: 'Coverage report', keepAll: true, alwaysLinkToLastBuild: true
          ])
          archiveArtifacts artifacts: 'coverage.xml,test-results.xml,flake8-report.txt,bandit-report.json',
                           allowEmptyArchive: true, fingerprint: true
        }
      }
    }

    stage('SonarQube analysis') {
      when { expression { return !params.SKIP_SONAR } }
      steps {
        script {
          def scannerHome = tool 'SonarScanner'
          withSonarQubeEnv('SonarQube') {
            sh """
              ${scannerHome}/bin/sonar-scanner \
                -Dsonar.projectKey=${SONAR_PROJECT_KEY} \
                -Dsonar.projectVersion=${params.APP_VERSION} \
                -Dsonar.python.coverage.reportPaths=coverage.xml \
                -Dsonar.python.flake8.reportPaths=flake8-report.txt \
                ${SONAR_ORG ? "-Dsonar.organization=${SONAR_ORG}" : ''}
            """
          }
        }
      }
    }

    stage('Quality gate') {
      when { expression { return !params.SKIP_SONAR } }
      steps {
        timeout(time: 10, unit: 'MINUTES') {
          waitForQualityGate abortPipeline: true
        }
      }
    }

    stage('Build image') {
      steps {
        sh '''
          set -eu
          docker build \
            --build-arg APP_VERSION=${APP_VERSION_ARG} \
            --build-arg GIT_COMMIT=${GIT_COMMIT_SHORT} \
            --build-arg BUILD_DATE=${BUILD_DATE} \
            -t ${IMAGE_NAME}:${IMAGE_TAG} \
            -t ${IMAGE_NAME}:${APP_VERSION_ARG} \
            -t ${IMAGE_NAME}:latest \
            .
          docker images ${IMAGE_NAME} --format "{{.Repository}}:{{.Tag}} {{.Size}}"
        '''
      }
    }

    stage('Container smoke test') {
      steps {
        sh '''
          set -eu
          CID=$(docker run -d -p 18080:5000 -e APP_VERSION=${APP_VERSION_ARG} ${IMAGE_NAME}:${IMAGE_TAG})
          trap "docker rm -f $CID >/dev/null 2>&1 || true" EXIT

          for i in $(seq 1 30); do
            if curl -fsS http://localhost:18080/health >/dev/null 2>&1; then break; fi
            sleep 2
          done

          echo "--- /health ---";  curl -fsS http://localhost:18080/health;  echo
          echo "--- /ready ----";  curl -fsS http://localhost:18080/ready;  echo
          echo "--- /version --";  curl -fsS http://localhost:18080/version; echo

          # Run the Pytest suite *inside* the built image (requirement 7).
          # --user root is needed only here: the runtime image deliberately runs
          # as uid 10001, which cannot install the test-only dependencies.
          docker run --rm --user root --entrypoint sh \
            -v "$PWD/tests:/app/tests:ro" \
            -v "$PWD/pytest.ini:/app/pytest.ini:ro" \
            ${IMAGE_NAME}:${IMAGE_TAG} \
            -c "pip install --quiet --no-cache-dir pytest pytest-cov \
                && cd /app \
                && python -m pytest tests -q --no-header -p no:cacheprovider \
                     --cov=app --cov-report=term --cov-fail-under=85"
        '''
      }
    }

    stage('Push to Docker Hub') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                          usernameVariable: 'DH_USER',
                                          passwordVariable: 'DH_PASS')]) {
          sh '''
            set -eu
            echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin
            docker push ${IMAGE_NAME}:${IMAGE_TAG}
            docker push ${IMAGE_NAME}:${APP_VERSION_ARG}
            docker push ${IMAGE_NAME}:latest
            docker logout
          '''
        }
      }
    }

    stage('Deploy') {
      when { expression { return params.DEPLOY_STRATEGY != 'none' } }
      steps {
        withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
          sh '''
            set -eu
            kubectl version --client
            kubectl get nodes

            # Record the currently live revision so the post-failure handler can revert.
            kubectl -n ${K8S_NAMESPACE} get deploy -o name > .live-deployments.txt 2>/dev/null || true

            ./scripts/deploy.sh \
              --strategy "${DEPLOY_STRATEGY_ARG}" \
              --image "${IMAGE_NAME}:${IMAGE_TAG}" \
              --version "${APP_VERSION_ARG}" \
              --namespace "${K8S_NAMESPACE}" \
              ${PROMOTE_FLAG}
          '''
        }
      }
    }

    stage('Post-deploy verification') {
      when { expression { return params.DEPLOY_STRATEGY != 'none' } }
      steps {
        withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
          sh './scripts/smoke-test.sh --namespace ${K8S_NAMESPACE} --expect-version ${APP_VERSION_ARG}'
        }
      }
    }
  }

  post {
    failure {
      echo 'Pipeline failed — attempting automatic rollback to the last stable revision.'
      script {
        if (params.DEPLOY_STRATEGY != 'none') {
          withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
            sh './scripts/rollback.sh --namespace ${K8S_NAMESPACE} --strategy ${DEPLOY_STRATEGY_ARG} || true'
          }
        }
      }
    }
    always {
      sh 'docker image prune -f || true'
      archiveArtifacts artifacts: 'k8s/**/*.yaml,Jenkinsfile,Dockerfile',
                       allowEmptyArchive: true, fingerprint: true
      cleanWs(deleteDirs: true, notFailBuild: true,
              patterns: [[pattern: '.venv/**', type: 'INCLUDE']])
    }
  }
}
