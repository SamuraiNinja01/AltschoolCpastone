# AltschoolCapstoneProject

# FastAPI Movie Listing API

This is a Movie Listing API built with FastAPI. The API allows users to list movies, view movies, rate them, and add comments. It uses JWT for authentication and is deployed to a cloud platform.

## Features

- **User Authentication**
  - User registration
  - User login with JWT
- **Movie Management**
  - Add a movie (authenticated users only)
  - View all movies (public)
  - View a specific movie (public)
  - Edit or delete movies (only by the user who added them)
- **Movie Ratings**
  - Rate a movie (authenticated users)
  - View ratings of a movie (public)
- **Comments**
  - Add a comment to a movie (authenticated users)
  - View comments for a movie (public)
  - Add nested comments (authenticated users)

## Technologies Used

- **FastAPI**: Python web framework for building APIs
- **SQLAlchemy**: ORM for managing the database
- **SQLite**: Default database (can be replaced with another SQL or NoSQL database)
- **JWT (JSON Web Tokens)**: For authentication
- **Uvicorn**: ASGI server to run FastAPI apps
- **Alembic**: For handling database migrations
