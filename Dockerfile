FROM python:3.12-slim

WORKDIR /app

RUN apt-get update
RUN apt-get install -y locales 


COPY requirements.txt .
RUN pip install --no-cache-dir  -r requirements.txt


RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/'        /etc/locale.gen \
    && locale-gen

COPY . .

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

ENV LC_ALL=en_US.UTF-8
ENV LC_CTYPE=en_US.UTF-8

CMD ["python3", "app.py"]