pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    ./venv/bin/pip install --upgrade pip
                    ./venv/bin/pip install -r requirements.txt
                '''
            }
        }

        stage('Build') {
            steps {
                sh '''
                    ./venv/bin/python -m py_compile app.py
                '''
            }
        }

        stage('Quality Gate - Lint') {
            steps {
                sh '''
                    ./venv/bin/flake8 app.py
                '''
            }
        }

        stage('Quality Gate - Tests') {
            steps {
                sh '''
                    ./venv/bin/pytest -v --junitxml=test-results.xml
                '''
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'test-results.xml'
        }

        success {
            echo 'ACEest Fitness Jenkins quality gate passed.'
        }

        failure {
            echo 'ACEest Fitness Jenkins quality gate failed.'
        }
    }
}
