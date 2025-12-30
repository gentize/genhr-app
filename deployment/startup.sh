#!/bin/bash
# Install dependencies
pip install -r requirements.txt
pip install gunicorn

# Run database migrations (optional if already handled)
# python deployment/migrate_to_postgres.py

# Start Gunicorn
gunicorn --bind=0.0.0.0 --timeout 600 run:app
