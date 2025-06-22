FROM python:3.13-alpine

# Установка зависимостей
RUN pip install --no-cache-dir dnspython paramiko

# Копируем скрипт
COPY keenroutes.py /app/keenroutes.py
WORKDIR /app

# Точка входа
ENTRYPOINT ["python", "-u", "keenroutes.py"]
