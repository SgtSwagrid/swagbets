# Generated by Django 3.0.3 on 2020-03-02 18:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('markets', '0009_auto_20200302_1752'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='proposition',
            options={'ordering': ['-active', 'resolves', 'code']},
        ),
        migrations.RemoveField(
            model_name='proposition',
            name='expected_resolve',
        ),
        migrations.AlterField(
            model_name='proposition',
            name='resolves',
            field=models.DateTimeField(help_text='The time at which this proposition resolved/will resolve.'),
        ),
    ]