from django.db import migrations


def forwards(apps, schema_editor):
    Marathon = apps.get_model('marathon', 'Marathon')
    Marathon.objects.filter(name='2026').update(
        format_note='Свободный посев. Год качества для растений прошлых марафонов',
        format_note_ru='Свободный посев. Год качества для растений прошлых марафонов',
        format_note_en='Free sowing. A year of quality for plants from past marathons',
    )


class Migration(migrations.Migration):
    dependencies = [('marathon', '0018_marathon_2026_title_image')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
