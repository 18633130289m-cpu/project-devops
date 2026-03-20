FROM python:3.9

WORKDIR /app
COPY . .

RUN pip install flask redis psutil

CMD ["python", "app.py"]
