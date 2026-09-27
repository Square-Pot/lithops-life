import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from marathon.models import Marathon, Nomination

DEFAULT = Path(__file__).resolve().parents[2] / 'data' / 'nominations.json'


class Command(BaseCommand):
    help = 'Создаёт номинации и проставляет переводы из JSON (ключ — марафон + русское название). Повторный запуск безопасен.'

    def add_arguments(self, parser):
        parser.add_argument('path', nargs='?', default=str(DEFAULT))
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, path, dry_run, **options):
        rows = json.loads(Path(path).read_text(encoding='utf-8'))
        with transaction.atomic():
            for row in rows:
                marathon = Marathon.objects.get(name=row['marathon'])
                found = Nomination.objects.filter(marathon=marathon).by_title(row['title_ru'])
                nomination = found[0] if found else None
                created = nomination is None
                if created:
                    nomination = Nomination(marathon=marathon)
                nomination.title = nomination.title_ru = row['title_ru']
                nomination.title_en = row['title_en']
                nomination.category = nomination.category_ru = row['category_ru']
                nomination.category_en = row['category_en']
                nomination.save()
                self.stdout.write(f"{'+' if created else '~'} [{marathon.name}] {row['title_ru']} / {row['title_en']}")
            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('dry run: изменения откатены'))
