# Generated by Django 5.0.7 on 2024-11-13 20:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marathon', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contestant',
            name='description',
            field=models.TextField(blank=True),
        ),
    ]