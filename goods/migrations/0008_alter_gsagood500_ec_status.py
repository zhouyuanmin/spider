# Generated by Django 3.2.15 on 2023-08-07 14:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0007_auto_20230807_1413'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gsagood500',
            name='ec_status',
            field=models.BooleanField(null=True, verbose_name='EC爬取状态'),
        ),
    ]
