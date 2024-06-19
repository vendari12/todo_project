#!/usr/bin/env python

import logging
import os
import subprocess
import unittest
import typer
from flask import Flask
from flask_migrate import Migrate
from app import create_app, db
from app.models import Role, User
from config import Config, config

# Initialize the Typer CLI manager
manager = typer.Typer()

# Set up the Flask app with the specified configuration
flask_config = os.getenv("FLASK_CONFIG", "default")
app: Flask = create_app(flask_config)
migrate = Migrate(app, db)

# Set logging level for CORS
logging.getLogger("flask_cors").setLevel(logging.DEBUG)


@manager.command()
def test() -> None:
    """Run the unit tests."""
    logging.info("Running unit tests...")
    tests = unittest.TestLoader().discover("tests")
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if result.wasSuccessful():
        logging.info("All tests passed.")
    else:
        logging.error("Some tests failed.")

@manager.command()
def recreate_db() -> None:
    """
    Recreates the local database.
    This should not be used in a production environment.
    """
    logging.info("Recreating the database...")
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.commit()
        logging.info("Database recreated successfully.")

@manager.command()
def runserver(host: str = "0.0.0.0", port: int = 5000) -> None:
    """Run the Flask development server."""
    logging.info(f"Starting server on {host}:{port}...")
    app.run(host, port)

@manager.command()
def create_tables() -> None:
    """
    Creates database tables without dropping existing ones.
    """
    logging.info("Creating database tables...")
    with app.app_context():
        db.create_all()
        db.session.commit()
        logging.info("Database tables created successfully.")

@manager.command()
def setup_dev() -> None:
    """Setup the application for local development."""
    logging.info("Setting up development environment...")
    setup_general()

@manager.command()
def setup_prod() -> None:
    """Setup the application for production environment."""
    logging.info("Setting up production environment...")
    setup_general()

def setup_general() -> None:
    """General setup for both development and production environments."""
    logging.info("Running general setup...")
    with app.app_context():
        Role.insert_roles()
        admin_role = Role.query.filter_by(name="Administrator").first()
        if admin_role and not User.query.filter_by(email=Config.ADMIN_EMAIL).first():
            user = User(
                first_name="Admin",
                last_name="Account",
                password=Config.ADMIN_PASSWORD,
                confirmed=True,
                username="Admin",
                email=Config.ADMIN_EMAIL,
            )
            db.session.add(user)
            db.session.commit()
            logging.info(f"Added administrator {user.full_name()}.")
        else:
            logging.info("Administrator role already exists or no admin role found.")

@manager.command()
def format_code() -> None:
    """Run the code formatters (isort and yapf) over the project files."""
    logging.info("Formatting code with isort and yapf...")
    commands = [
        "isort . --recursive",
        "yapf -r -i ."
    ]
    for command in commands:
        logging.info(f"Running: {command}")
        try:
            subprocess.run(command, shell=True, check=True)
            logging.info(f"Successfully ran: {command}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running command '{command}': {e}")

if __name__ == "__main__":
    manager()
