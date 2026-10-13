import re

from django.db import migrations

# копия правила marathon.models.normalize_tg_username: миграция не должна зависеть от будущего кода модели
TG_USERNAME_RE = re.compile(r'^[A-Za-z0-9_]{5,32}$')


def normalize(apps, schema_editor):
    """tg_username без «@» (import_finals сохранял «@name»); не похожее на хэндл («-» — хэндл скрыт) → пусто.
    Идемпотентно; при коллизии — остановка без изменений."""
    Participant = apps.get_model('marathon', 'Participant')
    seen = {}
    changes = []
    for p in Participant.objects.order_by('id'):
        clean = (p.tg_username or '').strip().lstrip('@').strip()
        if not TG_USERNAME_RE.match(clean):
            clean = ''
        if clean:
            other = seen.setdefault(clean.lower(), p.slug)
            if other != p.slug:
                raise RuntimeError(f'tg_username совпадает после нормализации у участников {other} и {p.slug}: объедините их в админке и повторите migrate')
        if clean != p.tg_username:
            changes.append((p.pk, clean))
    for pk, clean in changes:
        Participant.objects.filter(pk=pk).update(tg_username=clean)


class Migration(migrations.Migration):

    dependencies = [
        ('marathon', '0025_publish_existing_nominations'),
    ]

    operations = [
        migrations.RunPython(normalize, migrations.RunPython.noop),
    ]
