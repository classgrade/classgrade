# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-01-05 16:02
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gradapp', '0028_auto_20170105_1435'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignmentype',
            name='questions_statement',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.TextField(default=''), default=list, size=None),
        ),
    ]