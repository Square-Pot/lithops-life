from django.db import migrations

# кроп финального фото 2023 (finals/2023/66721.jpg, Алёна Яковлева); файл заливается в S3 вручную
URL = 'https://storage.yandexcloud.net/lithops.life/title_img/marathon_2026_title.jpg'


def forwards(apps, schema_editor):
    Marathon = apps.get_model('marathon', 'Marathon')
    Image = apps.get_model('marathon', 'Image')
    marathon = Marathon.objects.filter(name='2026').first()
    if marathon is None or marathon.title_image_id:
        return
    image, _ = Image.objects.get_or_create(
        url=URL, defaults={'author': 'Алёна Яковлева', 'description': 'Обложка Марафона 2026: Марафон 2023 через год'})
    marathon.title_image = image
    marathon.save(update_fields=['title_image'])


class Migration(migrations.Migration):
    dependencies = [('marathon', '0017_marathon_2026_and_tables')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
