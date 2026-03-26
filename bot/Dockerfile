# Dockerfile for the LMS Telegram Bot
# Builds a container that runs the bot with all dependencies

FROM python:3.12-slim

WORKDIR /app

# Install uv package manager
# uv is faster than pip and uses pyproject.toml directly
RUN pip install uv

# Copy bot project dependency files
# These are copied first for better Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies with uv
# --frozen ensures exact versions from uv.lock are used
RUN uv sync --frozen

# Copy bot source code
# This layer changes frequently, so it's copied last
COPY . .

# Set environment variables for Python
# PYTHONUNBUFFERED=1: Don't buffer stdout/stderr (important for Docker logs)
# PYTHONDONTWRITEBYTECODE=1: Don't create .pyc files
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the bot entry point
# The bot will connect to Telegram and start polling for messages
CMD ["uv", "run", "bot.py"]
