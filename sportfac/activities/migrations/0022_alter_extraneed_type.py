# Generated by Django 3.2.20 on 2023-10-05 03:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0021_auto_20230321_0628'),
    ]

    operations = [
        migrations.AlterField(
            model_name='extraneed',
            name='type',
            field=models.CharField(choices=[('B', 'Boolean'), ('C', 'Characters'), ('I', 'Integer'), ('IM', 'Image')], default='C', max_length=2, verbose_name='Type of answer'),
        ),
    ]