#!/bin/bash

cd /home/dntx/projects/lithops-life
git pull origin main
./rebuild.sh
# статика на хосте могла остаться от прежнего uid контейнера — отдаём её django (см. rebuild.sh)
docker exec -u root lithops-life-app-1 chown -R django:django /vol/static
docker exec lithops-life-app-1 sh -c "python manage.py collectstatic --noinput"
