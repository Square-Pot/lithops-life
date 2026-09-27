import json
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from marathon.models import Contestant, Image, Marathon, Nomination, Nominee, Participant

BUCKET_URL = 'https://storage.yandexcloud.net/lithops.life/'


class Command(BaseCommand):
    help = ('Заводит финальные фото из manifest.json (file, marathon, nomination_title, tg_id, '
            'contestant_short_name?) как Image, уже залитые в S3 под --prefix. Повторный запуск безопасен.')

    def add_arguments(self, parser):
        parser.add_argument('manifest')
        parser.add_argument('--prefix', required=True, help='папка в бакете, например finals/2024/')
        parser.add_argument('--finals', help='finals_*.json: найти номинацию по посту, если в manifest нет nomination_title')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, manifest, prefix, dry_run, finals=None, **options):
        prefix = prefix.strip('/') + '/'
        with open(manifest, encoding='utf-8') as f:
            rows = json.load(f)
        poll_by_msg = {}
        if finals:
            with open(finals, encoding='utf-8') as f:
                for item in json.load(f):
                    for nominee in item['nominees']:
                        for msg in nominee['photo_msgs']:
                            poll_by_msg[msg] = item.get('title') or item.get('poll_question')

        stats = Counter()
        with transaction.atomic():
            for row in rows:
                marathon = self._get(Marathon, name=row['marathon'])
                nomination = None
                title = row.get('nomination_title') or poll_by_msg.get(row.get('msg'))
                if title:
                    found = Nomination.objects.filter(marathon=marathon).by_title(title)
                    if len(found) != 1:
                        raise CommandError(f"Nomination не найдена: {marathon.name} «{title}»")
                    nomination = found[0]
                participant = self._get(Participant, tg_id=row['tg_id']) if row.get('tg_id') else None
                contestant = self._get(Contestant, marathon=marathon, short_name=row['contestant_short_name']) \
                    if row.get('contestant_short_name') else None
                is_winner = bool(nomination and participant and Nominee.objects.filter(
                    nomination=nomination, participant=participant, is_winner=True).exists())

                _, created = Image.objects.update_or_create(
                    url=BUCKET_URL + prefix + row['file'],
                    defaults={
                        'marathon': marathon,
                        'nomination': nomination,
                        'participant': participant,
                        'contestant': contestant,
                        'is_winner': is_winner,
                        'description': row.get('msg', ''),
                    },
                )
                stats['created' if created else 'updated'] += 1
                stats['winner photos'] += is_winner

            if dry_run:
                transaction.set_rollback(True)

        for k, v in sorted(stats.items()):
            self.stdout.write(f'{k}: {v}')
        if dry_run:
            self.stdout.write(self.style.WARNING('dry run: изменения откатены'))

    @staticmethod
    def _get(model, **lookup):
        try:
            return model.objects.get(**lookup)
        except model.DoesNotExist:
            raise CommandError(f'{model.__name__} не найден: {lookup}')
