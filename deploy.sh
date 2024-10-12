#!/bin/bash

cd /home/dntx/projects/lithops-life
git pull origin main
./rebuild.sh
docker exec lithops-life-app-1 sh -c "python manage.py collectstatic --noinput"
