# Toyxona loyihasi uchun alohida migratsiya (SmartBozor 0001_initial bilan nom to'qnashuvini oldini oladi)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_uz', models.CharField(max_length=100, verbose_name='Viloyat nomi')),
            ],
            options={'verbose_name': 'Viloyat', 'verbose_name_plural': 'Viloyatlar'},
        ),
        migrations.CreateModel(
            name='District',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_uz', models.CharField(max_length=100, verbose_name='Tuman nomi')),
                ('region', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='main.region')),
            ],
            options={'verbose_name': 'Tuman', 'verbose_name_plural': 'Tumanlar'},
        ),
        migrations.CreateModel(
            name='Hall',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_uz', models.CharField(max_length=100, verbose_name='Toyxona nomi')),
                ('slug', models.CharField(max_length=30, unique=True, verbose_name='Slug')),
                ('server_user', models.CharField(blank=True, default=None, max_length=50, null=True)),
                ('server_ip', models.GenericIPAddressField(blank=True, default=None, null=True)),
                ('server_port', models.PositiveSmallIntegerField(default=22)),
                ('is_online', models.BooleanField(default=False, editable=False, verbose_name='Online')),
                ('app_version', models.CharField(default='-', editable=False, max_length=50)),
                ('max_capacity', models.PositiveIntegerField(default=0, verbose_name="Maksimal sig'im")),
                ('activity_suspended', models.BooleanField(default=False, verbose_name="Faoliyati to'xtatilgan")),
                ('district', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='main.district', verbose_name='Joylashgan tuman')),
            ],
            options={
                'verbose_name': 'Toyxona',
                'verbose_name_plural': 'Toyxonalar',
                'permissions': (('hall_online', 'Toyxona server holati'),),
            },
        ),
    ]
