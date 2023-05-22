# Generated by Django 3.2.15 on 2023-05-22 21:48

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ECGood',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='创建时间')),
                ('update_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('delete_at', models.DateTimeField(default=None, null=True, verbose_name='删除时间')),
                ('note', models.CharField(blank=True, default='', max_length=255, verbose_name='备注')),
                ('part', models.CharField(blank=True, default='', max_length=255, verbose_name='零件号')),
                ('manufacturer', models.CharField(blank=True, default='', max_length=255, verbose_name='制造商')),
                ('mfr_part_no', models.CharField(blank=True, default='', max_length=255, verbose_name='制造商零件号')),
                ('vendor_part_no', models.CharField(blank=True, default='', max_length=255, verbose_name='供应商零件号')),
                ('msrp', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, verbose_name='制造商建议零售价')),
                ('federal_govt_spa', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, verbose_name='联邦政府价格')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]