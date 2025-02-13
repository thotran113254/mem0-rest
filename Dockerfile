FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .

# Thêm bước clean cache và force reinstall
RUN pip cache purge && \
    pip install --no-cache-dir --force-reinstall -r requirements.txt

COPY . .

# Tạo user với home directory
RUN useradd -m appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 5000
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]
