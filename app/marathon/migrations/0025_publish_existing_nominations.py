from django.db import migrations

# Номинации прошлых финалов уже на сайте — оставляем их видимыми.
# Номинации финала 2025 Кристина наполняет в кабинете скрыто и публикует сама.
HIDDEN_MARATHONS = ['2025']


def publish_existing(apps, schema_editor):
    Nomination = apps.get_model('marathon', 'Nomination')
    Nomination.objects.exclude(marathon__name__in=HIDDEN_MARATHONS).update(is_published=True)


class Migration(migrations.Migration):

    dependencies = [
        ('marathon', '0024_nomination_publish_label'),
    ]

    operations = [
        migrations.RunPython(publish_existing, migrations.RunPython.noop),
    ]
