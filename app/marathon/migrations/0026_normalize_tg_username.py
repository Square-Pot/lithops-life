from django.db import migrations


def normalize(apps, schema_editor):
    """tg_username без «@» (import_finals сохранял «@name»). Идемпотентно; при коллизии — остановка без изменений."""
    Participant = apps.get_model('marathon', 'Participant')
    seen = {}
    changes = []
    for p in Participant.objects.order_by('id'):
        clean = (p.tg_username or '').strip().lstrip('@').strip()
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
