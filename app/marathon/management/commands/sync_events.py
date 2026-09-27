import datetime
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from marathon.models import Event, Marathon

DEFAULT = Path(__file__).resolve().parents[2] / 'data' / 'events.json'


class Command(BaseCommand):
    help = 'Создаёт/обновляет события марафонов из JSON (ключ — марафон + дата). Повторный запуск безопасен.'

    def add_arguments(self, parser):
        parser.add_argument('path', nargs='?', default=str(DEFAULT))
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, path, dry_run, **options):
        rows = json.loads(Path(path).read_text(encoding='utf-8'))
        with transaction.atomic():
            for row in rows:
                marathon = Marathon.objects.get(name=row['marathon'])
                event, created = Event.objects.update_or_create(
                    marathon=marathon, date=datetime.date.fromisoformat(row['date']),
                    defaults={
                        'title': row['title_ru'],
                        'title_ru': row['title_ru'],
                        'title_en': row['title_en'],
                        'published': row.get('published', True),
                    },
                )
                self.stdout.write(f"{'+' if created else '~'} {event}")
            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('dry run: изменения откатены'))
