# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-09-26 21:49
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gradapp', '0010_auto_20160926_2144'),
    ]

    operations = [
        migrations.AlterField(
            model_name='evalassignment',
            name='grade_assignment',
            field=models.FloatField(blank=True, help_text='/10', null=True, validators=[django.core.validators.MaxValueValidator(10), django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='evalassignment',
            name='grade_evaluation',
            field=models.FloatField(blank=True, help_text='/10', null=True, validators=[django.core.validators.MaxValueValidator(10), django.core.validators.MinValueValidator(0)]),
        ),
    ]
