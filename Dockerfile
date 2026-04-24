FROM python:3.12-slim

# Install system dependencies for GUI and remote sync
RUN apt-get update && apt-get install -y \
    python3-tk \
    libtk8.6 \
    git \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variable for Citra path (can be overridden)
ENV CITRA_PATH=/root/.local/share/citra-emu

CMD ["python", "main.py"]
