# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-09-28 11:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gradapp', '0012_auto_20160927_1134'),
    ]

    operations = [
        migrations.AlterField(
            model_name='evalassignment',
            name='grade_assignment_comments',
            field=models.TextField(blank=True, default='', max_length=3000),
        ),
    ]