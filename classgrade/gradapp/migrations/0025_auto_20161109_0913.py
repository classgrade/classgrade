# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-11-09 09:13
from __future__ import unicode_literals

from django.db import migrations


def fill_evaluator(apps, schema_editor):
    Evalassignment = apps.get_model("gradapp", "Evalassignment")
    for evalassignment in Evalassignment.objects.all():
        evalassignment.evaluator_bis = evalassignment.evaluator.user
        evalassignment.save()


class Migration(migrations.Migration):

    dependencies = [
        ('gradapp', '0024_auto_20161109_0854'),
    ]

    operations = [
        migrations.RunPython(fill_evaluator),
    ]
