FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script
COPY container_restarter.py .

# Make the script executable
RUN chmod +x container_restarter.py

# Run the script
CMD ["python", "-u", "container_restarter.py"]
