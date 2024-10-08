# Generated by Django 5.0.7 on 2024-08-30 01:25

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0015_examsubmission"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="examsubmission",
            name="id",
        ),
        migrations.AddField(
            model_name="examsubmission",
            name="student",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="exam_submissions",
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="examsubmission",
            name="submission_key",
            field=models.CharField(
                blank=False,
                max_length=255,
                primary_key=True,
                serialize=False,
                unique=True,
            ),
        ),
    ]
