import json
import re
from pathlib import Path

from django.db import migrations

NOMINATIONS_JSON = Path(__file__).resolve().parents[1] / 'data' / 'nominations.json'

DESCRIPTIONS_DE = {
    '2023': 'Der erste jährliche Aizoaceae-Aussaatmarathon',
    '2024': 'Der zweite jährliche Aizoaceae-Aussaatmarathon',
    '2025': 'Der dritte jährliche Aizoaceae-Aussaatmarathon',
    '2026': 'Der vierte jährliche Aizoaceae-Marathon',
}
FORMAT_NOTE_DE_2026 = 'Freie Aussaat. Ein Jahr der Qualität für Pflanzen früherer Marathons'
DETAILS_DE_2026 = (
    'Der Marathon 2026 ist ein Jahr der Qualität. In dieser Saison gibt es keine Wettbewerbssämlinge mit regelmäßigen '
    'Berichten. Die Saison ist den Pflanzen früherer Marathons gewidmet — Wettbewerbsarten und andere: Wer noch lebende '
    'Pflanzen aus 2023, 2024 und 2025 hat, ist automatisch dabei.\n\n'
    'Jede Etappe der Saison ist einer der Wettbewerbsarten früherer Marathons gewidmet — so gehen wir im Laufe des '
    'Jahres alle durch.\n\n'
    'Ziele: vergleichen, wie dieselben Arten bei verschiedenen Teilnehmenden 1, 2 und 3 Jahre nach der Aussaat aussehen '
    '(und nach Möglichkeit die Wettbewerbstabellen ergänzen); die Pflanzen in Ordnung bringen — Umtopfen, Pikieren, '
    'Umstellen; Platz für künftige Marathons schaffen.\n\n'
    'Die Aussaat fällt nicht aus: Der 1. Oktober bleibt der wichtigste Aussaattag, junge Aussaaten sind willkommen, '
    'und die Aussaat kann um einen Monat verschoben werden.'
)

EVENT_FIXED = {
    'Sowing': 'Aussaat',
    "Finale: collecting finalists' photos": 'Finale: Sammeln der Finalfotos',
    'Finale: voting': 'Finale: Abstimmungen',
    'Finale: voting (tentative)': 'Finale: Abstimmungen (voraussichtlich)',
    'Finale: results and prizes': 'Finale: Ergebnisse und Preise',
}
AGE = [
    (r'^1 week$', '1 Woche'), (r'^(\d+) weeks$', r'\1 Wochen'),
    (r'^1 month$', '1 Monat'), (r'^1\.5 months$', '1,5 Monate'), (r'^(\d+) months$', r'\1 Monate'),
    (r'^[Hh]alf a year$', 'ein halbes Jahr'), (r'^1 year$', '1 Jahr'), (r'^1\.5 years$', '1,5 Jahre'),
]


def event_de(title_en):
    title_en = re.sub(r'\s+', ' ', title_en or '').strip()
    if title_en in EVENT_FIXED:
        return EVENT_FIXED[title_en]
    m = re.match(r'^Stage ?(\d+)\. Age ?-? (.+)$', title_en)
    if not m:
        return None
    age = m.group(2).strip()
    for pattern, repl in AGE:
        if re.match(pattern, age):
            return f'Phase {m.group(1)}. Alter - {re.sub(pattern, repl, age)}'
    return None


def forwards(apps, schema_editor):
    Marathon = apps.get_model('marathon', 'Marathon')
    Event = apps.get_model('marathon', 'Event')
    Nomination = apps.get_model('marathon', 'Nomination')

    for name, text in DESCRIPTIONS_DE.items():
        Marathon.objects.filter(name=name).update(description_de=text)
    Marathon.objects.filter(name='2026').update(details_de=DETAILS_DE_2026, format_note_de=FORMAT_NOTE_DE_2026)

    # старые немецкие заголовки частично неверные («Phase 14» у первого этапа) — пересобираем все из английских
    for event in Event.objects.all():
        de = event_de(event.title_en)
        if de:
            event.title_de = de
            event.save(update_fields=['title_de'])

    by_en = {(row['marathon'], row['title_en']): row for row in json.loads(NOMINATIONS_JSON.read_text(encoding='utf-8'))}
    for nomination in Nomination.objects.select_related('marathon'):
        row = by_en.get((nomination.marathon.name, nomination.title_en))
        if row:
            nomination.title_de, nomination.category_de = row['title_de'], row['category_de']
            nomination.save(update_fields=['title_de', 'category_de'])


class Migration(migrations.Migration):
    dependencies = [('marathon', '0022_german_fields')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
