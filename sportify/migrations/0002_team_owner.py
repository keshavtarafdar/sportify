# Generated by Django 4.2.16 on 2024-10-06 18:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sportify', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='owner',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, related_name='owned_teams', to='sportify.user'),
            preserve_default=False,
        ),
    ]
