# Generated by Django 5.0.7 on 2024-12-02 20:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('marathon', '0009_marathon_description_de_marathon_description_en_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='marathon',
            name='state_de',
        ),
        migrations.RemoveField(
            model_name='marathon',
            name='state_en',
        ),
        migrations.RemoveField(
            model_name='marathon',
            name='state_ru',
        ),
    ]
