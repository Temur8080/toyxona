import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('main', '0001_toyxona_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Camera',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_sn', models.CharField(blank=True, editable=False, max_length=100, null=True, verbose_name='Device SN')),
                ('name', models.CharField(max_length=100, verbose_name='Kamera nomi')),
                ('camera_mac', models.CharField(blank=True, default=None, editable=False, max_length=20, null=True, verbose_name='Camera MAC')),
                ('camera_ip', models.GenericIPAddressField(blank=True, default=None, editable=False, null=True, verbose_name='IP')),
                ('camera_port', models.PositiveSmallIntegerField(default=554, verbose_name='Port')),
                ('username', models.CharField(blank=True, default=None, max_length=100, null=True, verbose_name='Login')),
                ('password', models.CharField(blank=True, default=None, max_length=100, null=True, verbose_name='Parol')),
                ('roi', models.JSONField(blank=True, default=None, editable=False, null=True, verbose_name='Zona (ROI)')),
                ('screenshot', models.ImageField(blank=True, default=None, editable=False, null=True, upload_to='camera/screenshot', verbose_name='Screenshot')),
                ('is_active', models.BooleanField(default=True, verbose_name='Active')),
                ('is_online', models.BooleanField(default=False, editable=False, verbose_name='Online')),
                ('use_ai', models.BooleanField(default=False, verbose_name='AI bilan sanash')),
                ('show_in_centre', models.BooleanField(default=False, verbose_name="Markazda ko'rsatish")),
                ('hall', models.ForeignKey(db_index=False, on_delete=django.db.models.deletion.RESTRICT, to='main.hall', verbose_name='Toyxona')),
            ],
            options={
                'verbose_name': 'Kamera',
                'verbose_name_plural': 'Kameralar',
                'indexes': [models.Index(fields=['hall', 'device_sn'], name='camera_hall_sn_idx')],
            },
        ),
    ]
