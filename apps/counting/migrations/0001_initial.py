# Generated manually for toyxona project

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('camera', '0001_toyxona_initial'),
        ('main', '0001_toyxona_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PeopleCount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count', models.PositiveIntegerField(default=0, verbose_name='Odamlar soni')),
                ('recorded_at', models.DateTimeField(db_index=True, verbose_name='Vaqt')),
                ('camera', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='camera.camera', verbose_name='Kamera')),
                ('hall', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.hall', verbose_name='Toyxona')),
            ],
            options={
                'verbose_name': 'Odamlar soni',
                'verbose_name_plural': 'Odamlar soni tarixi',
                'ordering': ('-recorded_at',),
                'indexes': [models.Index(fields=['hall', '-recorded_at'], name='peoplecount_hall_time_idx')],
            },
        ),
    ]
