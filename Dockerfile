FROM python:3.13-alpine

ENV TZ="Europe/Brussels"
ENV PYTHONUNBUFFERED=1

WORKDIR /artifacts

COPY requirements.txt /artifacts/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /artifacts/

ENTRYPOINT ["python3", "-u", "main.py", "--headless"]