import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from marathon.models import Participant

UNSURE_MARK = 'tg_id сопоставлен с уверенностью'


class Command(BaseCommand):
    help = ('Участники без tg_id (или с непроверенным): --export выгружает их в JSON, '
            'в файле вручную проставляется tg_id, --apply загружает обратно.')

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--export', metavar='PATH')
        group.add_argument('--apply', metavar='PATH')

    def handle(self, export, apply, **options):
        if export:
            self._export(export)
        else:
            self._apply(apply)

    def _export(self, path):
        qs = Participant.objects.filter(Q(tg_id__isnull=True) | Q(note__contains=UNSURE_MARK)).order_by('display_name')
        rows = [{
            'slug': p.slug,
            'display_name': p.display_name,
            'tg_username': p.tg_username,
            'tg_id': p.tg_id,
            'confirmed': False,
            'note': p.note,
        } for p in qs]
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        self.stdout.write(f'{len(rows)} участников → {path}. Проставь tg_id и "confirmed": true, затем --apply.')

    def _apply(self, path):
        with open(path, encoding='utf-8') as f:
            rows = json.load(f)
        updated = 0
        with transaction.atomic():
            for row in rows:
                if not row.get('confirmed'):
                    continue
                try:
                    p = Participant.objects.get(slug=row['slug'])
                except Participant.DoesNotExist:
                    raise CommandError(f"Нет участника со slug {row['slug']}")
                tg_id = row.get('tg_id')
                if tg_id and Participant.objects.filter(tg_id=tg_id).exclude(pk=p.pk).exists():
                    other = Participant.objects.get(tg_id=tg_id)
                    raise CommandError(f'tg_id {tg_id} уже у {other} — это один человек? Объедини в админке.')
                p.tg_id = tg_id or None
                if row.get('tg_username') is not None:
                    p.tg_username = row['tg_username']
                if UNSURE_MARK in p.note:
                    p.note = ''
                p.save()
                updated += 1
        self.stdout.write(f'обновлено: {updated}')
