# Generated by Django 3.0.3 on 2020-03-02 16:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('markets', '0006_auto_20200302_1657'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tokens',
            options={'ordering': ['user', '-quantity', 'proposition'], 'verbose_name_plural': 'tokens'},
        ),
    ]