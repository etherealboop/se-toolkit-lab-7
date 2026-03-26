FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy bot project files
COPY pyproject.toml uv.lock ./

# Install dependencies with uv
RUN uv sync --frozen

# Copy bot source code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the bot
CMD ["uv", "run", "bot.py"]
