import datetime
import json
import io
import tempfile
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import translation
from PIL import Image as PILImage

from marathon.models import Marathon, Contestant, Nomination, Image, Participant, Nominee


class FinalsTest(TestCase):
    def setUp(self):
        self.marathon = Marathon.objects.create(name='2023', description='', seeding_date=datetime.date(2023, 10, 1))
        self.contestant = Contestant.objects.create(genus='Lithops', short_name='C188', marathon=self.marathon)
        self.nomination = Nomination.objects.create(title='Лучший C188', category='Конкурсные', marathon=self.marathon, is_published=True)

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
    """Расписание Марафона 2026 из data/events.json: октябрь + вторая дата посева + 4 недели × 11 месяцев, ru/en/de."""

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
        events = self.Event.objects.filter(marathon=self.m, date__gt=datetime.date(2026, 10, 1)).order_by('date', 'id')
        self.assertEqual(events.count(), 2 + 4 * 11)
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

    def test_second_sowing_date_goes_before_week_1(self):
        self._sync()
        self._sync()
        nov1 = self.Event.objects.filter(marathon=self.m, date=datetime.date(2026, 11, 1)).order_by('id')
        self.assertEqual([e.title_ru for e in nov1], ['Посев (вторая дата)', 'Неделя 1: конкурсный вид — C188'])
        self.assertEqual((nov1[0].title_en, nov1[0].title_de), ('Sowing (second date)', 'Aussaat (zweiter Termin)'))
        with mock.patch('marathon.views.datetime') as vdt:
            vdt.date.today.return_value = datetime.date(2026, 11, 1)
            r = self.client.get('/marathon/2026')
        html = r.content.decode()
        self.assertLess(html.index('Посев (вторая дата)'), html.index('Неделя 1: конкурсный вид — C188'))
        self.assertEqual(r.context['now_event'].title_ru, 'Неделя 1: конкурсный вид — C188')  # последнее событие дня

    def test_sync_fixes_day_order_when_week_1_already_exists(self):
        # БД, где расписание уже синхронизировано без второй даты посева
        self.Event.objects.create(marathon=self.m, date=datetime.date(2026, 11, 1), title='Неделя 1: конкурсный вид — C188')
        self._sync()
        nov1 = self.Event.objects.filter(marathon=self.m, date=datetime.date(2026, 11, 1)).order_by('id')
        self.assertEqual([e.title_ru for e in nov1], ['Посев (вторая дата)', 'Неделя 1: конкурсный вид — C188'])

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


def _jpeg(size=(1200, 800)):
    buf = io.BytesIO()
    PILImage.new('RGB', size, (120, 160, 90)).save(buf, 'JPEG')
    return buf.getvalue()


class NominationVisibilityTest(TestCase):
    """Фото и номинанты неопубликованной номинации не видны публично; «по номерам» — без имён."""

    def setUp(self):
        self.marathon = Marathon.objects.create(name='2025', description='', seeding_date=datetime.date(2025, 10, 1))
        self.alice = Participant.objects.create(display_name='Алиса', slug='alice')
        self.hidden = Nomination.objects.create(title='Лучший C300', category='Конкурсные', marathon=self.marathon)
        Nominee.objects.create(nomination=self.hidden, participant=self.alice)
        self.photo = Image.objects.create(url='https://storage.yandexcloud.net/lithops.life/finals/2025/nominations/1/a.jpg',
                                          marathon=self.marathon, nomination=self.hidden, participant=self.alice)

    def test_unpublished_nomination_is_hidden_everywhere(self):
        self.assertNotContains(self.client.get('/marathon/2025'), 'Лучший C300')
        self.assertNotContains(self.client.get('/gallery'), self.photo.url)
        page = self.client.get('/participant/alice')
        self.assertNotContains(page, self.photo.url)
        self.assertNotContains(page, 'Лучший C300')
        self.assertEqual(self.client.get(f'/photo/{self.photo.pk}/thumb').status_code, 404)
        self.assertEqual(self.client.get(f'/photo/{self.photo.pk}/download').status_code, 404)

    def test_published_nomination_is_shown(self):
        Nomination.objects.filter(pk=self.hidden.pk).update(is_published=True)
        self.assertContains(self.client.get('/marathon/2025'), 'Лучший C300')
        self.assertContains(self.client.get('/marathon/2025'), '/participant/alice')
        self.assertContains(self.client.get('/gallery'), self.photo.url)

    def test_numbered_nomination_does_not_reveal_names(self):
        Nomination.objects.filter(pk=self.hidden.pk).update(is_published=True, nominee_label='number')
        page = self.client.get('/marathon/2025')
        self.assertContains(page, 'Номинант 1')
        self.assertNotContains(page, '/participant/alice')
        self.assertNotContains(self.client.get('/gallery'), self.photo.url)
        self.assertNotContains(self.client.get('/participant/alice'), 'Лучший C300')

    def test_pages_render_in_all_languages(self):
        Nomination.objects.filter(pk=self.hidden.pk).update(is_published=True, nominee_label='number')
        self.addCleanup(translation.activate, 'ru')  # LocaleMiddleware оставляет язык активным для следующих тестов
        for lang in ('ru', 'en', 'de'):
            with self.subTest(lang=lang):
                self.client.cookies['django_language'] = lang
                self.assertEqual(self.client.get('/marathon/2025').status_code, 200)


@override_settings(ALLOWED_HOSTS=['testserver'])
class ManageNominationsTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Permission, User
        self.marathon = Marathon.objects.create(name='2025', description='', seeding_date=datetime.date(2025, 10, 1))
        self.nomination = Nomination.objects.create(title='Лучший C300', category='Конкурсные', marathon=self.marathon)
        self.alice = Participant.objects.create(display_name='Алиса', slug='alice', tg_username='alice_tg')
        self.user = User.objects.create_user('kristina', password='pw')
        self.user.user_permissions.add(Permission.objects.get(codename='manage_nominations'))
        self.s3 = mock.Mock()
        patcher = mock.patch('marathon.storage._client', return_value=self.s3)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _login(self):
        self.client.login(username='kristina', password='pw')

    def _url(self):
        return f'/manage/nomination/{self.nomination.pk}'

    def test_access(self):
        from django.contrib.auth.models import User
        self.assertRedirects(self.client.get('/manage/'), '/manage/login?next=/manage/', fetch_redirect_response=False)
        User.objects.create_user('guest', password='pw')
        self.client.login(username='guest', password='pw')
        self.assertEqual(self.client.get('/manage/').status_code, 403)
        self._login()
        page = self.client.get('/manage/')
        self.assertContains(page, 'Лучший C300')
        self.assertContains(page, 'скрыта')
        self.assertEqual(self.client.get('/manage/login').status_code, 200)

    def test_create_nomination_hidden_with_number_label(self):
        self._login()
        response = self.client.post('/manage/', {'marathon': '2025', 'title': 'Лучшая тройка', 'category': 'Конкурсные', 'nominee_label': 'number'})
        created = Nomination.objects.get(title_ru='Лучшая тройка')
        self.assertRedirects(response, f'/manage/nomination/{created.pk}', fetch_redirect_response=False)
        self.assertFalse(created.is_published)
        self.assertEqual(created.nominee_label, 'number')

    def test_add_nominees_existing_and_new(self):
        self._login()
        self.client.post(self._url(), {'action': 'add_nominee', 'participant': self.alice.pk})
        self.client.post(self._url(), {'action': 'add_nominee', 'participant': self.alice.pk})
        self.client.post(self._url(), {'action': 'add_nominee', 'new_name': 'Борис Петров', 'new_username': '@boris'})
        self.client.post(self._url(), {'action': 'add_nominee', 'new_name': 'Борис', 'new_username': 'boris'})
        self.assertEqual(self.nomination.nominees.count(), 2)
        boris = Participant.objects.get(tg_username='boris')
        self.assertEqual(boris.slug, 'boris-petrov')
        self.assertContains(self.client.get(self._url()), 'Борис Петров')

    def test_upload_resizes_and_links_photo(self):
        self._login()
        nominee = Nominee.objects.create(nomination=self.nomination, participant=self.alice)
        upload = io.BytesIO(_jpeg((4000, 3000)))
        upload.name = 'IMG_1.jpg'
        response = self.client.post(f'/manage/nominee/{nominee.pk}/photos', {'photo': upload})
        self.assertEqual(response.status_code, 200, response.content)
        img = Image.objects.get(pk=response.json()['id'])
        self.assertEqual((img.nomination, img.participant, img.marathon), (self.nomination, self.alice, self.marathon))
        self.assertRegex(img.url, r'^https://storage\.yandexcloud\.net/lithops\.life/finals/2025/nominations/\d+/[0-9a-f]{32}\.jpg$')
        kwargs = self.s3.put_object.call_args.kwargs
        self.assertEqual(kwargs['Key'], img.url.split('/lithops.life/')[1])
        self.assertEqual(PILImage.open(io.BytesIO(kwargs['Body'])).size, (2560, 1920))

    def test_upload_rejects_non_images_and_needs_permission(self):
        nominee = Nominee.objects.create(nomination=self.nomination, participant=self.alice)
        upload = io.BytesIO(b'not an image')
        upload.name = 'x.jpg'
        self.assertEqual(self.client.post(f'/manage/nominee/{nominee.pk}/photos', {'photo': upload}).status_code, 302)
        self._login()
        upload.seek(0)
        self.assertEqual(self.client.post(f'/manage/nominee/{nominee.pk}/photos', {'photo': upload}).status_code, 400)
        self.assertFalse(self.nomination.images.exists())
        self.s3.put_object.assert_not_called()

    def test_storage_failure_keeps_database_clean(self):
        self._login()
        nominee = Nominee.objects.create(nomination=self.nomination, participant=self.alice)
        self.s3.put_object.side_effect = RuntimeError('boom')
        upload = io.BytesIO(_jpeg())
        upload.name = 'a.jpg'
        self.assertEqual(self.client.post(f'/manage/nominee/{nominee.pk}/photos', {'photo': upload}).status_code, 502)
        self.assertFalse(self.nomination.images.exists())

    def test_missing_keys_is_a_clear_error(self):
        from marathon import storage
        mock.patch.stopall()
        with mock.patch.dict('os.environ', {'AWS_ACCESS_KEY_ID': '', 'AWS_SECRET_ACCESS_KEY': ''}):
            with self.assertRaisesRegex(storage.StorageError, 'нет ключей'):
                storage.upload_nominee_photo(self.nomination, b'x')

    def test_delete_photo_and_nominee_remove_objects(self):
        self._login()
        nominee = Nominee.objects.create(nomination=self.nomination, participant=self.alice)
        base = 'https://storage.yandexcloud.net/lithops.life/finals/2025/nominations/1/'
        one = Image.objects.create(url=base + 'a.jpg', nomination=self.nomination, participant=self.alice, marathon=self.marathon)
        Image.objects.create(url=base + 'b.jpg', nomination=self.nomination, participant=self.alice, marathon=self.marathon)
        self.client.post(self._url(), {'action': 'delete_photo', 'photo': one.pk})
        self.s3.delete_object.assert_called_once_with(Bucket='lithops.life', Key='finals/2025/nominations/1/a.jpg')
        self.assertEqual(self.nomination.images.count(), 1)
        self.client.post(self._url(), {'action': 'delete_nominee', 'nominee': nominee.pk})
        self.assertFalse(self.nomination.images.exists())
        self.assertFalse(Nominee.objects.exists())
        self.assertTrue(Participant.objects.filter(pk=self.alice.pk).exists())

    def test_publish_toggle_and_manager_sees_hidden_thumb(self):
        self._login()
        self.client.post(self._url(), {'action': 'settings', 'is_published': 'on', 'nominee_label': 'number'})
        self.nomination.refresh_from_db()
        self.assertTrue(self.nomination.is_published)
        self.assertEqual(self.nomination.nominee_label, 'number')
        self.client.post(self._url(), {'action': 'settings', 'nominee_label': 'name'})
        self.nomination.refresh_from_db()
        self.assertFalse(self.nomination.is_published)
        img = Image.objects.create(url='https://storage.yandexcloud.net/lithops.life/x.jpg', nomination=self.nomination, marathon=self.marathon)
        fake = mock.Mock(content=_jpeg(), raise_for_status=lambda: None)
        with tempfile.TemporaryDirectory() as cache, override_settings(WATERMARK_CACHE_DIR=cache), \
                mock.patch('marathon.views.requests.get', return_value=fake):
            self.assertEqual(self.client.get(f'/photo/{img.pk}/thumb').status_code, 200)
