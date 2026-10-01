import datetime
import json
import io
import tempfile
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image as PILImage

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


class WatermarkDownloadTest(TestCase):
    def setUp(self):
        self.marathon = Marathon.objects.create(name='2023', description='', seeding_date=datetime.date(2023, 10, 1))

    def _jpeg(self):
        buf = io.BytesIO()
        PILImage.new('RGB', (1200, 800), (120, 160, 90)).save(buf, 'JPEG')
        return buf.getvalue()

    def test_download_is_watermarked_and_cached(self):
        img = Image.objects.create(url='https://storage.yandexcloud.net/lithops.life/etc/01.jpg', marathon=self.marathon)
        fake = mock.Mock(content=self._jpeg(), raise_for_status=lambda: None)
        with tempfile.TemporaryDirectory() as cache, override_settings(WATERMARK_CACHE_DIR=cache), \
                mock.patch('marathon.views.requests.get', return_value=fake) as get:
            thumb = self.client.get(f'/photo/{img.id}/thumb')
            self.assertEqual(PILImage.open(io.BytesIO(b''.join(thumb.streaming_content))).size, (600, 400))
            thumb.close()
            get.reset_mock()
            for _ in range(2):
                r = self.client.get(f'/photo/{img.id}/download')
                self.assertEqual(r.status_code, 200)
                self.assertIn('attachment', r['Content-Disposition'])
                body = b''.join(r.streaming_content)
                r.close()
            self.assertEqual(get.call_count, 1)
        result = PILImage.open(io.BytesIO(body)).convert('RGB')
        self.assertEqual(result.size, (1200, 800))
        self.assertNotEqual(result.getpixel((1100, 700)), (120, 160, 90))  # в углу знак
        self.assertEqual(result.getpixel((50, 50)), result.getpixel((60, 60)))  # остальное не тронуто

    def test_download_refuses_title_images_and_foreign_hosts(self):
        title = Image.objects.create(url='https://storage.yandexcloud.net/lithops.life/title_img/x.jpg')
        foreign = Image.objects.create(url='http://169.254.169.254/latest', marathon=self.marathon)
        self.assertEqual(self.client.get(f'/photo/{title.id}/download').status_code, 404)
        self.assertEqual(self.client.get(f'/photo/{foreign.id}/download').status_code, 404)
        self.assertEqual(self.client.get(f'/photo/{foreign.id}/thumb').status_code, 404)

    def test_thumb_falls_back_to_original_when_s3_fails(self):
        import requests
        img = Image.objects.create(url='https://storage.yandexcloud.net/lithops.life/etc/02.jpg', marathon=self.marathon)
        with tempfile.TemporaryDirectory() as cache, override_settings(WATERMARK_CACHE_DIR=cache), \
                mock.patch('marathon.views.requests.get', side_effect=requests.ConnectionError):
            r = self.client.get(f'/photo/{img.id}/thumb')
        self.assertRedirects(r, img.url, fetch_redirect_response=False)


class CarouselTest(TestCase):
    def test_carousel_prefers_starred_then_winners(self):
        from marathon.views import _carousel_images
        m = Marathon.objects.create(name='2024', description='', seeding_date=datetime.date(2024, 10, 1))
        winner = Image.objects.create(url='https://storage.yandexcloud.net/a.jpg', marathon=m, is_winner=True)
        Image.objects.create(url='https://storage.yandexcloud.net/b.jpg', marathon=m)
        self.assertEqual(list(_carousel_images(m)), [winner])
        starred = Image.objects.create(url='https://storage.yandexcloud.net/c.jpg', marathon=m, is_starred=True)
        self.assertEqual(list(_carousel_images(m)), [starred])


class MarathonStateTest(TestCase):
    def test_state_follows_calendar(self):
        from marathon.models import Event
        m = Marathon.objects.create(name='2025', description='', seeding_date=datetime.date(2025, 10, 1))
        d = datetime.date
        self.assertEqual(m.state_on(d(2025, 9, 30)), 'pending')
        self.assertEqual(m.state_on(d(2026, 5, 1)), 'in_progress')
        self.assertEqual(m.state_on(d(2026, 10, 1)), 'final')  # год с посева
        Event.objects.create(marathon=m, date=d(2026, 11, 1), title='Финал: голосования')
        self.assertEqual(m.state_on(d(2026, 12, 16)), 'completed')  # 45 дней без события итогов
        Event.objects.create(marathon=m, date=d(2026, 12, 20), title='Финал: итоги и призы')
        self.assertEqual(m.state_on(d(2026, 12, 19)), 'final')
        self.assertEqual(m.state_on(d(2026, 12, 20)), 'completed')


class Schedule2026Test(TestCase):
    """Расписание Марафона 2026 из data/events.json: октябрь + 4 недели × 11 месяцев, ru/en/de."""

    def setUp(self):
        from marathon.models import Event
        self.Event = Event
        for name in ('2023', '2024', '2025', '2026'):
            Marathon.objects.get_or_create(name=name, defaults={'description': '', 'seeding_date': datetime.date(int(name), 10, 1)})
        self.m = Marathon.objects.get(name='2026')

    def _sync(self):
        call_command('sync_events', stdout=io.StringIO())

    def test_sync_is_idempotent_and_covers_the_year(self):
        self._sync()
        self._sync()
        events = self.Event.objects.filter(marathon=self.m, date__gt=datetime.date(2026, 10, 1)).order_by('date')
        self.assertEqual(events.count(), 1 + 4 * 11)
        self.assertEqual(events.first().date, datetime.date(2026, 10, 2))
        self.assertEqual(events.last().date, datetime.date(2027, 9, 22))
        for e in events:
            with self.subTest(date=e.date):
                self.assertTrue(e.title_ru and e.title_en and e.title_de)
                if e.date.month != 10:
                    self.assertIn(e.date.day, (1, 8, 15, 22))
        first_weeks = {e.date.month: e.title_ru for e in events if e.date.day == 1}
        self.assertTrue(first_weeks[11].endswith('C188'))
        self.assertTrue(first_weeks[5].endswith('C300 и C205 (green form)'))
        self.assertTrue(first_weeks[9].endswith('C. angelicae ssp. tetragonum'))

    def test_schedule_does_not_change_marathon_state(self):
        self._sync()
        d = datetime.date
        self.assertEqual(self.m.state_on(d(2026, 11, 20)), 'in_progress')
        self.assertEqual(self.m.state_on(d(2027, 9, 30)), 'in_progress')
        self.assertEqual(self.m.state_on(d(2027, 10, 1)), 'final')

    def test_sync_keeps_german_title_when_json_has_none(self):
        e = self.Event.objects.create(marathon=self.m, date=datetime.date(2026, 10, 1), title='Посев', title_de='Aussaat')
        self._sync()
        e.refresh_from_db()
        self.assertEqual(e.title_de, 'Aussaat')

    def test_page_shows_schedule_in_order_by_month(self):
        self._sync()
        with mock.patch('marathon.views.datetime') as vdt:
            vdt.date.today.return_value = datetime.date(2026, 11, 10)
            r = self.client.get('/marathon/2026')
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertLess(html.index('C188'), html.index('C262'))  # идущий марафон — по возрастанию
        self.assertIn('Ноябрь 2026', html)
        self.assertEqual(r.context['now_event'].date, datetime.date(2026, 11, 8))
        from django.conf import settings
        for lang, title in (('en', 'Week 1: contest species — C188'), ('de', 'Woche 1: Wettbewerbsart — C188')):
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = lang
            with self.subTest(lang=lang):
                self.assertContains(self.client.get('/marathon/2026'), title)

    def test_finished_marathon_keeps_newest_first(self):
        self._sync()
        r = self.client.get('/marathon/2023')
        dates = [e.date for e in r.context['events']]
        self.assertEqual(dates, sorted(dates, reverse=True))
