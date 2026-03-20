FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    swig \
    libexpat1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install DIAMOND — required by CarveMe for protein annotation
# CarveMe's --refseq mode downloads a genome and runs DIAMOND against it;
# without DIAMOND the run exits cleanly but produces no SBML output.
RUN wget -q https://github.com/bbuchfink/diamond/releases/download/v2.1.9/diamond-linux64.tar.gz \
    && tar xzf diamond-linux64.tar.gz \
    && mv diamond /usr/local/bin/diamond \
    && rm diamond-linux64.tar.gz

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

COPY server.py .

EXPOSE 8000

CMD ["python", "server.py"]
