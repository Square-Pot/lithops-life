from django.db import migrations

STAGES_RU = ('Каждый этап сезона посвящён одному из конкурсных видов прошлых марафонов — '
             'так за год мы пройдём их все.')
STAGES_EN = ('Each stage of the season is dedicated to one of the contest species of past marathons, '
             'so over the year we will go through all of them.')


def forwards(apps, schema_editor):
    Marathon = apps.get_model('marathon', 'Marathon')
    m = Marathon.objects.filter(name='2026').first()
    if m is None:
        return
    for field, text in (('details_ru', STAGES_RU), ('details_en', STAGES_EN)):
        paragraphs = (getattr(m, field) or '').split('\n\n')
        if text not in paragraphs:
            paragraphs.insert(1, text)  # сразу после вводного абзаца о формате
            setattr(m, field, '\n\n'.join(paragraphs))
    m.details = m.details_ru
    m.save(update_fields=['details', 'details_ru', 'details_en'])


class Migration(migrations.Migration):
    dependencies = [('marathon', '0019_marathon_2026_format_note')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
