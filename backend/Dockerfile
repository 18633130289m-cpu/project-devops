FROM python:3.9

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir flask redis pymysql
CMD ["python", "app.py"]
