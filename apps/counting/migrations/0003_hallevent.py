import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('counting', '0002_rename_peoplecount_hall_time_idx_counting_pe_hall_id_43a6aa_idx'),
        ('main', '0001_toyxona_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HallEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('started_at', models.DateTimeField(verbose_name='Boshlangan')),
                ('ended_at', models.DateTimeField(blank=True, null=True, verbose_name='Tugagan')),
                ('peak_count', models.PositiveIntegerField(default=0, verbose_name="Eng ko'p odam")),
                ('is_active', models.BooleanField(default=True, verbose_name='Hozir davom etmoqda')),
                ('hall', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='main.hall', verbose_name='Toyxona')),
            ],
            options={
                'verbose_name': 'Toy (tadbir)',
                'verbose_name_plural': 'Toylar',
                'ordering': ('-started_at',),
            },
        ),
        migrations.AddIndex(
            model_name='hallevent',
            index=models.Index(fields=['hall', 'is_active'], name='counting_ha_hall_id_active_idx'),
        ),
    ]
