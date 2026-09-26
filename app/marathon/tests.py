import datetime
import json
import tempfile

from django.core.management import call_command
from django.test import TestCase

from marathon.models import Marathon, Contestant, Nomination, Image, Participant, Nominee


class FinalsTest(TestCase):
    def setUp(self):
        self.marathon = Marathon.objects.create(name='2023', description='', seeding_date=datetime.date(2023, 10, 1))
        self.contestant = Contestant.objects.create(genus='Lithops', short_name='C188', marathon=self.marathon)
        self.nomination = Nomination.objects.create(title='Лучший C188', category='Конкурсные', marathon=self.marathon)

    def _import(self, data):
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        call_command('import_finals', f.name, stdout=open('/dev/null', 'w'))

    def test_import_is_idempotent_and_keeps_two_plants_of_one_person(self):
        nominee = {'tg_id': 1, 'username': '@boris', 'display_name': 'Борис', 'votes': 5, 'winner': True, 'photo_msgs': []}
        data = [{'marathon': '2023', 'title': 'Лучший C188', 'nominees': [
            dict(nominee, plant='первое'), dict(nominee, plant='второе', winner=False, votes=1),
        ]}]
        self._import(data)
        self._import(data)
        self.assertEqual(Participant.objects.count(), 1)
        self.assertEqual(Nominee.objects.count(), 2)

    def test_pages(self):
        p = Participant.objects.create(display_name='Борис', slug='boris', tg_id=1)
        Nominee.objects.create(nomination=self.nomination, participant=p, is_winner=True, votes=5)
        Image.objects.create(url='https://example.com/1.jpg', marathon=self.marathon, contestant=self.contestant, participant=p)
        for url in ['/', '/gallery', '/gallery?marathon=2023&winners=1', '/participant/boris', '/marathon/2023', '/marathon/contest/C188']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.get('/marathon/2023'), '/participant/boris')
        self.assertContains(self.client.get('/gallery'), 'https://example.com/1.jpg')
        self.assertEqual(self.client.get('/participant/nobody').status_code, 404)
