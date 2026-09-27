import datetime

from django.db import migrations

DETAILS_RU = (
    'Марафон 2026 — год качества. Конкурсных сеянцев с регулярной отчётностью в этом сезоне нет. '
    'Сезон посвящён растениям предыдущих марафонов, конкурсным и не только: участвуют автоматически все, '
    'у кого живы растения 2023, 2024 и 2025 годов.\n\n'
    'Цели: сравнить, как выглядят одни и те же виды у разных участников через 1, 2 и 3 года после посева '
    '(и по возможности дополнить конкурсные таблицы); привести растения в порядок — пересадка, пикировка, '
    'перестановка; освободить место под будущие марафоны.\n\n'
    'Посевы не отменяются: 1 октября — по-прежнему основной посевной день, молодые посевы приветствуются, '
    'посев можно сдвинуть на месяц.'
)
DETAILS_EN = (
    'Marathon 2026 is a year of quality. This season has no contest seedlings with regular reports. '
    'It is dedicated to plants from previous marathons, contest and otherwise: everyone whose plants '
    'from 2023, 2024 and 2025 are still alive takes part automatically.\n\n'
    "Goals: compare how the same species look in different growers' hands 1, 2 and 3 years after sowing "
    '(and, where possible, complete the contest tables); tidy up the plants — repotting, pricking out, '
    'rearranging; free up space for future marathons.\n\n'
    'Sowing is not cancelled: 1 October is still the main sowing day, young sowings are welcome, '
    'and sowing can be shifted by a month.'
)
TABLES = {
    '2024': ('https://docs.google.com/spreadsheets/d/1_3qnfAIQWgoRt2tQl8_fJk1ppUj9ZsOJ-yJH-TMMa_w/edit?usp=sharing',
             'https://docs.google.com/spreadsheets/d/1K4DFI9FQn6XIFgYnnL4TKUWNhA-2l9H1-d8F7ePbZ5E/edit?usp=sharing'),
    '2025': ('https://docs.google.com/spreadsheets/d/1LRQJVSxFm2zROZfo0H3PTMT-cePIKD9g-qxabnADP8Y/edit?usp=sharing', ''),
    '2026': ('https://docs.google.com/spreadsheets/d/1dCiNCFHRDVcof29vQ4z3SI25qL8NqIg1bDDAw8ulIo0/edit?usp=sharing', ''),
}


def forwards(apps, schema_editor):
    Marathon = apps.get_model('marathon', 'Marathon')
    Contestant = apps.get_model('marathon', 'Contestant')

    m, _ = Marathon.objects.get_or_create(
        name='2026',
        defaults={'seeding_date': datetime.date(2026, 10, 1), 'state': 'pending', 'participants_number': 0},
    )
    m.description = m.description_ru = 'Четвёртый ежегодный марафон аизовых'
    m.description_en = 'The Fourth Annual Aizoaceae Marathon'
    m.details = m.details_ru = DETAILS_RU
    m.details_en = DETAILS_EN
    m.format_note = m.format_note_ru = 'Конкурсных видов нет — год качества'
    m.format_note_en = 'No contest species — a year of quality'
    m.save()

    for name, (sowing, data) in TABLES.items():
        Marathon.objects.filter(name=name).update(sowing_table_url=sowing, data_table_url=data)

    # полное имя «L. julii ssp. julii, C205 (green form)»; короткое «C205 [green form]» не меняем
    Contestant.objects.filter(short_name='C205 [green form]', field_number='C205').update(field_number='C205 (green form)')


class Migration(migrations.Migration):
    dependencies = [('marathon', '0016_marathon_format_fields')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
