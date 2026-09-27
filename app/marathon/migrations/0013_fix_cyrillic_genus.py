from django.db import migrations

# кириллица, похожая на латиницу: «Сonophytum» с русской С давал на сайте «С. angelicae»
LOOKALIKES = str.maketrans('АВСЕНКМОРТХасеорх', 'ABCEHKMOPTXaceopx')


def fix_genus(apps, schema_editor):
    Contestant = apps.get_model('marathon', 'Contestant')
    for c in Contestant.objects.all():
        fixed = {f: getattr(c, f).translate(LOOKALIKES) for f in ('genus', 'species', 'subspecies', 'variety')}
        if any(getattr(c, f) != v for f, v in fixed.items()):
            for f, v in fixed.items():
                setattr(c, f, v)
            c.save(update_fields=list(fixed))


class Migration(migrations.Migration):
    dependencies = [('marathon', '0012_participants_nominees')]
    operations = [migrations.RunPython(fix_genus, migrations.RunPython.noop)]
