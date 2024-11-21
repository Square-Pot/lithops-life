# Generated by Django 5.0.7 on 2024-11-10 19:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Contestant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('genus', models.CharField(max_length=100)),
                ('species', models.CharField(max_length=100)),
                ('subspecies', models.CharField(blank=True, max_length=100)),
                ('variety', models.CharField(blank=True, max_length=100)),
                ('cultivar', models.CharField(blank=True, max_length=100)),
                ('field_number', models.CharField(blank=True, max_length=100)),
                ('short_name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('category', models.CharField(blank=True, max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField()),
                ('author', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('is_winner', models.BooleanField(default=False)),
                ('is_starred', models.BooleanField(default=False)),
                ('contestant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='images', to='marathon.contestant')),
            ],
        ),
        migrations.AddField(
            model_name='contestant',
            name='title_image',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contestant_title_image', to='marathon.image'),
        ),
        migrations.CreateModel(
            name='Marathon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('seeding_date', models.DateField()),
                ('state', models.CharField(choices=[('pending', 'Pending'), ('in_progress', 'In progress'), ('final', 'Final'), ('completed', 'Completed')], default='pending', max_length=50)),
                ('title_image', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='marathon_title_image', to='marathon.image')),
            ],
        ),
        migrations.AddField(
            model_name='image',
            name='marathon',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='images', to='marathon.marathon'),
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('published', models.BooleanField(default=False)),
                ('marathon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marathon.marathon')),
            ],
        ),
        migrations.AddField(
            model_name='contestant',
            name='marathon',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marathon.marathon'),
        ),
        migrations.CreateModel(
            name='Nomination',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('category', models.CharField(max_length=100)),
                ('winner_name', models.CharField(blank=True, max_length=255)),
                ('winner_username', models.CharField(blank=True, max_length=255)),
                ('poll_date', models.DateField()),
                ('marathon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='marathon.marathon')),
                ('poll_image', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='nomination_poll_image', to='marathon.image')),
            ],
        ),
        migrations.AddField(
            model_name='image',
            name='nomination',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='images', to='marathon.nomination'),
        ),
    ]
