FROM python:3.12-slim

WORKDIR /app

# Cập nhật pip và xóa cache
RUN pip install --no-cache-dir --upgrade pip && \
    pip cache purge

# Copy requirements và cài đặt dependencies
COPY requirements.txt .
RUN pip uninstall -y pydantic pydantic-core && \
    pip install --no-cache-dir pydantic>=2.6.1 pydantic-core>=2.14.5 && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Tạo user với home directory
RUN useradd -m appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 5000
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]
