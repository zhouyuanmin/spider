# Generated by Django 3.2.15 on 2023-08-07 14:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0006_gsagood500'),
    ]

    operations = [
        migrations.AddField(
            model_name='gsagood500',
            name='ec_status',
            field=models.BooleanField(default=False, null=True, verbose_name='EC爬取状态'),
        ),
        migrations.AddField(
            model_name='gsagood500',
            name='federal_govt_spa',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='联邦政府价格'),
        ),
        migrations.AddField(
            model_name='gsagood500',
            name='msrp',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='制造商建议零售价'),
        ),
        migrations.AlterField(
            model_name='gsagood500',
            name='key',
            field=models.CharField(blank=True, default='', max_length=255, unique=True),
        ),
    ]