#!/bin/bash
# любой упавший шаг (pull, сборка, chown, collectstatic) валит деплой в GitHub Actions, а не проходит молча
set -e

cd /home/dntx/projects/lithops-life
git pull origin main
./rebuild.sh
# схема выкатывается вместе с кодом: бэкап базы с датой, затем миграции (без них новый код отдаёт 500)
cp -p app/db.sqlite3 ~/db.sqlite3.bak-$(date +%F-%H%M%S)
docker exec lithops-life-app-1 python manage.py migrate --noinput
# статика на хосте могла остаться от прежнего uid контейнера — отдаём её django (см. rebuild.sh)
docker exec -u root lithops-life-app-1 chown -R django:django /vol/static
docker exec lithops-life-app-1 sh -c "python manage.py collectstatic --noinput"
