# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-10-05 19:46
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gradapp', '0021_evalassignment_is_questions_graded'),
    ]

    operations = [
        migrations.AlterField(
            model_name='evalquestion',
            name='grade',
            field=models.IntegerField(blank=True, help_text='0, 1, or 2', null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(2)]),
        ),
    ]
