# Seatsurfing Backend (FastAPI)

This project is a Python backend implementation of a workspace booking system.

## Features
- REST API with FastAPI
- JWT Authentication
- PostgreSQL integration
- Booking system (desks / rooms)
- Calendar integration

## Tech Stack
- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic

## Setup

python -m venv .venv  
.venv\Scripts\activate  
pip install -r requirements.txt  

## Run

uvicorn app.main:app --reload  

## Notes
Backend refactoring from original Go project to Python.