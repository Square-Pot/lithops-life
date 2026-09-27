import json
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from marathon.models import Marathon, Nomination, Participant, Nominee


class Command(BaseCommand):
    help = 'Импорт номинантов финалов из JSON-выгрузки чата (data/finals_*.json). Повторный запуск безопасен.'

    def add_arguments(self, parser):
        parser.add_argument('path')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, path, dry_run, **options):
        with open(path, encoding='utf-8') as f:
            data = json.load(f)

        names = self._collect_names(data)
        stats = Counter()
        with transaction.atomic():
            for item in data:
                if not item.get('title'):
                    stats['skipped: нет на сайте'] += 1
                    self.stdout.write(f"  пропуск: {item['marathon']} «{item.get('poll_question')}»")
                    continue
                found = Nomination.objects.filter(marathon__name=item['marathon']).by_title(item['title'])
                if len(found) != 1:
                    raise CommandError(f"Номинация не найдена: {item['marathon']} «{item['title']}»")
                nomination = found[0]

                nomination.poll_url = item.get('poll_msg') or ''
                nomination.total_voters = item.get('total_voters')
                if item.get('poll_date') and not nomination.poll_date:
                    nomination.poll_date = item['poll_date']
                nomination.save()

                for n in item['nominees']:
                    participant = self._get_participant(n, names, stats)
                    _, created = Nominee.objects.update_or_create(
                        nomination=nomination, participant=participant, plant=(n.get('plant') or '')[:255],
                        defaults={
                            'is_winner': bool(n.get('winner')),
                            'votes': n.get('votes'),
                            'photo_msgs': '\n'.join(n.get('photo_msgs') or []),
                        },
                    )
                    stats['nominee created' if created else 'nominee updated'] += 1

            if dry_run:
                transaction.set_rollback(True)

        for k, v in sorted(stats.items()):
            self.stdout.write(f'{k}: {v}')
        if dry_run:
            self.stdout.write(self.style.WARNING('dry run: изменения откатены'))

    @staticmethod
    def _collect_names(data):
        # у одного человека в разных постах бывает «Борис Ш.» и «Борис Шемаров» — берём самое полное
        names = {}
        for item in data:
            for n in item['nominees']:
                key = n.get('tg_id') or n.get('username')
                name = (n.get('display_name') or '').strip()
                if len(name) > len(names.get(key, '')):
                    names[key] = name
        return names

    def _get_participant(self, n, names, stats):
        tg_id = n.get('tg_id')
        username = (n.get('username') or '').strip()
        participant = None
        if tg_id:
            participant = Participant.objects.filter(tg_id=tg_id).first()
        if not participant and username:
            participant = Participant.objects.filter(tg_username__iexact=username).first()
        if participant:
            if tg_id and not participant.tg_id:
                participant.tg_id = tg_id
            if username and participant.tg_username != username:
                participant.tg_username = username
            participant.save()
            return participant

        display_name = names.get(tg_id or username) or username or str(tg_id)
        participant = Participant.objects.create(
            display_name=display_name,
            slug=self._unique_slug(username.lstrip('@') or display_name, tg_id),
            tg_id=tg_id,
            tg_username=username,
            note='' if n.get('tg_id_confidence', 'high') == 'high'
                 else f"tg_id сопоставлен с уверенностью {n['tg_id_confidence']}, проверить",
        )
        stats['participant created'] += 1
        return participant

    @staticmethod
    def _unique_slug(base, tg_id):
        slug = slugify(base, allow_unicode=False) or f'u{tg_id}'
        candidate, i = slug, 2
        while Participant.objects.filter(slug=candidate).exists():
            candidate, i = f'{slug}-{i}', i + 1
        return candidate
