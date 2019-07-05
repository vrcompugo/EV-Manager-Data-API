FROM python:3.7-stretch

RUN groupadd -g 999 appuser && \
    useradd -r -u 999 -g appuser appuser

WORKDIR /usr/src/app

COPY . .

RUN chmod 644 manage.py

RUN pip install --no-cache-dir -r requirements.txt

USER appuser

ENV PYTHONUNBUFFERED 1


CMD ["python3", "manage.py", "run" ]