from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('counting', '0003_hallevent'),
    ]

    operations = [
        migrations.DeleteModel(
            name='HallEvent',
        ),
    ]
