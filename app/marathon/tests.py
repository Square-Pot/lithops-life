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


class CarouselTest(TestCase):
    def test_carousel_prefers_starred_then_winners(self):
        from marathon.views import _carousel_images
        m = Marathon.objects.create(name='2024', description='', seeding_date=datetime.date(2024, 10, 1))
        winner = Image.objects.create(url='https://storage.yandexcloud.net/a.jpg', marathon=m, is_winner=True)
        Image.objects.create(url='https://storage.yandexcloud.net/b.jpg', marathon=m)
        self.assertEqual(list(_carousel_images(m)), [winner])
        starred = Image.objects.create(url='https://storage.yandexcloud.net/c.jpg', marathon=m, is_starred=True)
        self.assertEqual(list(_carousel_images(m)), [starred])
