# Generated by Django 5.1.1 on 2024-11-16 22:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sportify', '0013_userprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='google_pfpURL',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.DeleteModel(
            name='UserProfile',
        ),
    ]
