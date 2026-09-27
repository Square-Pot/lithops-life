FROM python:3.10-alpine3.16

ENV PYTHONUNBUFFERED 1

COPY requirements.txt /requirements.txt
RUN apk add --upgrade --no-cache build-base linux-headers gettext && \
    pip install --upgrade pip && \
    pip install -r /requirements.txt &&\
    mkdir -p /vol/static 
    

COPY app/ /app
WORKDIR /app

# .mo не хранятся в git — собираем переводы при сборке образа
RUN DJANGO_SECRET_KEY=build DJANGO_ALLOWED_HOSTS=localhost python manage.py compilemessages

RUN adduser --disabled-password --no-create-home django &&\
    chown -R django:django /vol && \
    chmod -R 755 /vol && \
    chown -R django:django /app

USER django

CMD ["uwsgi", "--socket", ":9000", "--workers", "4", "--master", "--enable-threads", "--module", "app.wsgi"]