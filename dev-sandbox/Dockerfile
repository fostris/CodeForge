FROM python:3.12-slim

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install testing framework (always needed)
RUN pip install --no-cache-dir \
    pytest>=7.4 \
    pytest-asyncio>=0.21 \
    pytest-cov>=4.0 \
    pytest-mock>=3.12

# Install common project dependencies that generated code typically uses
# These cover auth systems, web APIs, databases, etc.
RUN pip install --no-cache-dir \
    fastapi>=0.104 \
    uvicorn>=0.24 \
    sqlalchemy>=2.0 \
    alembic>=1.12 \
    pydantic>=2.0 \
    pydantic-settings>=2.0 \
    pydantic-settings>=2.0 \
    python-jose[cryptography]>=3.3 \
    PyJWT>=2.8 \
    passlib[bcrypt]>=1.7 \
    bcrypt>=4.0 \
    python-multipart>=0.0.6 \
    httpx>=0.24 \
    email-validator>=2.0 \
    python-dotenv>=1.0

# Install requirements.txt if present (for project-specific deps)
# This runs at build time with whatever is in dev-sandbox/
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Set Python path so imports work
ENV PYTHONPATH=/workspace:$PYTHONPATH

# Default command
CMD ["pytest", "--tb=short", "-v"]
