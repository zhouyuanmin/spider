# Generated by Django 3.2.15 on 2023-06-16 14:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0002_alter_gsagood_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gsagood',
            name='url',
            field=models.CharField(max_length=255, unique=True, verbose_name='url'),
        ),
    ]
