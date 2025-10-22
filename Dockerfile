# Start with the base Python image
FROM python:3.11-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy the project files into the container
COPY . .

# Install the necessary dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# The command to run your application
ENTRYPOINT ["python", "-m", "mcp_server_rememberizer.server"]
