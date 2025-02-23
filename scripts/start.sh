#!/bin/bash

# Ensure data directory exists and has right permissions
mkdir -p /data
chown -R nobody:nogroup /data

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis is ready!"

# Initialize database and test data
python3 -c "
from flask import Flask
from app.db import init_db, db
from app.utils.init_test_data import init_test_data
from app.db.models import User

app = Flask(__name__)
init_db(app)

with app.app_context():
    print('\nInitializing database...')
    # Create tables
    db.create_all()
    print('Database tables created')
    
    # Initialize test data
    init_test_data()
    
    # Verify data
    admin = User.query.filter_by(email='admin@test.com').first()
    if admin:
        print(f'\nVerification: Found admin user with ID: {admin.id}')
    else:
        print('\nWarning: Admin user not found in database!')
"

# Start Flask application
flask run --host=0.0.0.0 