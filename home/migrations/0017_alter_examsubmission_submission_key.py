# Generated by Django 5.0.7 on 2024-08-30 01:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0016_remove_examsubmission_id_examsubmission_student_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="examsubmission",
            name="submission_key",
            field=models.CharField(
                blank=True,
                max_length=255,
                primary_key=True,
                serialize=False,
                unique=True,
            ),
        ),
    ]
