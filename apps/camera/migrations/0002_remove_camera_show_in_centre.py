from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('camera', '0001_toyxona_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='camera',
            name='show_in_centre',
        ),
    ]
