from setuptools import setup, find_packages

setup(
    name="python_ml_billing_service",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "aio-pika==9.3.0",
        "aiogram==3.3.0",
        "SQLAlchemy==2.0.23",
        "alembic==1.13.0",
        "asyncpg==0.29.0",
        "psycopg2-binary==2.9.9",
        "python-dotenv==1.0.0",
        "prometheus-client==0.19.0"
    ],
) 