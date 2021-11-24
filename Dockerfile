FROM python:3.7-buster

RUN groupadd -g 999 appuser && \
    useradd -r -u 999 -g appuser -m appuser

WORKDIR /usr/src/app

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod 644 manage.py
RUN mkdir /usr/src/app/tmp
RUN chmod 777 /usr/src/app/tmp
RUN chmod 777 /usr/src/app/wkhtmltopdf
RUN chown -R appuser.appuser /usr/src/app

RUN apt-get update && apt-cache search ghostscript && apt-get install -y ghostscript

COPY hosts /etc/hosts

USER appuser

ENV PYTHONUNBUFFERED 1

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]

CMD ["python3", "manage.py", "run" ]
