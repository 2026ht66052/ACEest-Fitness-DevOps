"""Gunicorn configuration for the containerised application."""

import multiprocessing
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", min(4, multiprocessing.cpu_count() * 2 + 1)))
threads = int(os.environ.get("WEB_THREADS", "2"))
worker_class = "gthread"
timeout = 30
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(M)sms'
# Allows zero-downtime rolling updates: finish in-flight requests before exit.
max_requests = 1000
max_requests_jitter = 100
