# Generated by Django 3.2.15 on 2023-05-30 12:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0002_ecgood'),
    ]

    operations = [
        migrations.AddField(
            model_name='good',
            name='coo',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='原产地'),
        ),
    ]