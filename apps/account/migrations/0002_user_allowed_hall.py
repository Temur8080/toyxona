import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0001_initial'),
        ('main', '0001_toyxona_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='allowed_hall',
            field=models.ManyToManyField(blank=True, to='main.hall', verbose_name='Ruxsat berilgan toyxonalar'),
        ),
    ]
