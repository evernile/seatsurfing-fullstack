FROM python:3.12-slim

WORKDIR /app

COPY server_py/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY server_py /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]