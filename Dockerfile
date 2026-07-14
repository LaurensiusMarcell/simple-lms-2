# Menggunakan image Python versi ringan
FROM python:3.11-slim

# Mencegah Python menulis file .pyc ke disk
ENV PYTHONDONTWRITEBYTECODE=1
# Memastikan output Python dikirim langsung ke terminal
ENV PYTHONUNBUFFERED=1

# Menentukan direktori kerja di dalam kontainer
WORKDIR /app

# Menyalin file requirements dan menginstalnya
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Menyalin seluruh project ke dalam kontainer
COPY . /app/