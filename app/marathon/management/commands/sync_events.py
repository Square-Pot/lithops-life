import datetime
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import translation

from marathon.models import Event, Marathon

DEFAULT = Path(__file__).resolve().parents[2] / 'data' / 'events.json'


class Command(BaseCommand):
    help = 'Создаёт/обновляет события марафонов из JSON (ключ — марафон + дата). Повторный запуск безопасен.'

    def add_arguments(self, parser):
        parser.add_argument('path', nargs='?', default=str(DEFAULT))
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, path, dry_run, **options):
        rows = json.loads(Path(path).read_text(encoding='utf-8'))
        # 'title' у modeltranslation пишется в поле активного языка — фиксируем русский
        with translation.override('ru'), transaction.atomic():
            for row in rows:
                marathon = Marathon.objects.get(name=row['marathon'])
                if row.get('old_date'):  # перенос события на другую дату
                    Event.objects.filter(marathon=marathon, date=datetime.date.fromisoformat(row['old_date'])) \
                        .update(date=datetime.date.fromisoformat(row['date']))
                defaults = {
                    'title': row['title_ru'],
                    'title_ru': row['title_ru'],
                    'title_en': row['title_en'],
                    'published': row.get('published', True),
                }
                if row.get('title_de'):  # без title_de немецкий берётся из базы или фолбэком en → ru
                    defaults['title_de'] = row['title_de']
                event, created = Event.objects.update_or_create(
                    marathon=marathon, date=datetime.date.fromisoformat(row['date']), defaults=defaults,
                )
                self.stdout.write(f"{'+' if created else '~'} {event}")
            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('dry run: изменения откатены'))
