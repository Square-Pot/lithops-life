from django.db import migrations

# старое короткое имя остаётся в marathon.views.LEGACY_SHORT_NAMES для редиректа: ссылки ходят по чату
RENAMES = {'C. angelica ssp. tetragonum': 'C. angelicae ssp. tetragonum'}
DESCRIPTIONS_EN = {
    '2023': 'The First Annual Aizoaceae Sowing Marathon',
    '2024': 'The Second Annual Aizoaceae Sowing Marathon',
    '2025': 'The Third Annual Aizoaceae Sowing Marathon',
}
CONFIRMED_BY_ORGANIZER = ['alenaalexandrovnaya', 'msuvertok', 'ttolkova', 'm_sosnitskiy']


def forwards(apps, schema_editor):
    Contestant = apps.get_model('marathon', 'Contestant')
    Marathon = apps.get_model('marathon', 'Marathon')
    Participant = apps.get_model('marathon', 'Participant')
    for old, new in RENAMES.items():
        Contestant.objects.filter(short_name=old).update(short_name=new)
    for name, text in DESCRIPTIONS_EN.items():
        Marathon.objects.filter(name=name).update(description_en=text)
    Participant.objects.filter(slug__in=CONFIRMED_BY_ORGANIZER, note__contains='уверенностью').update(note='')


class Migration(migrations.Migration):
    dependencies = [('marathon', '0014_nomination_translation')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
