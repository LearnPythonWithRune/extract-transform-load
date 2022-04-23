FROM python:3.10-bullseye

RUN apt-get update && apt-get -y install cron
COPY requirements.txt .
RUN pip install -r requirements.txt

RUN mkdir /src

COPY crontab /etc/cron.d/crontab
RUN chmod 0644 /etc/cron.d/crontab
RUN /usr/bin/crontab /etc/cron.d/crontab
COPY . /src

WORKDIR /src

CMD ["cron", "-f"]