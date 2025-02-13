FROM python:3.12-slim

WORKDIR /app

# Cập nhật pip trước khi cài đặt packages
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements và cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir pydantic==2.10.6 pydantic-core==2.29.0 && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Tạo user với home directory
RUN useradd -m appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 5000
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]
