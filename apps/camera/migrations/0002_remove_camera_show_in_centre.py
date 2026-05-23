from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('camera', '0002_rename_camera_hall_sn_idx_camera_came_hall_id_6ab9d3_idx'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='camera',
            name='show_in_centre',
        ),
    ]
