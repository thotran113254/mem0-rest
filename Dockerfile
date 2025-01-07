FROM python:3.12-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY . .

RUN adduser --disabled-password --no-create-home appuser
USER appuser

EXPOSE 5000
CMD ["flask", "run", "--host=0.0.0.0"]
