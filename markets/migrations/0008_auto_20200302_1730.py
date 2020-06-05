# Generated by Django 3.0.3 on 2020-03-02 17:30

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('markets', '0007_auto_20200302_1658'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='proposition',
            options={'ordering': ['-active', 'expected_resolve', 'code']},
        ),
        migrations.RenameField(
            model_name='proposition',
            old_name='resolve_date',
            new_name='expected_resolve',
        ),
        migrations.RemoveField(
            model_name='proposition',
            name='creation_date',
        ),
        migrations.AddField(
            model_name='proposition',
            name='resolves',
            field=models.DateTimeField(auto_now=True, help_text='The time at which this proposition actually resolved.'),
        ),
        migrations.AddField(
            model_name='proposition',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2020, 3, 2, 17, 30, 38, 872566), help_text='The time at which this proposition was created.'),
            preserve_default=False,
        ),
    ]