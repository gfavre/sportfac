# Generated by Django 3.2.20 on 2024-02-12 14:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0021_alter_bill_payment_method'),
        ('absences', '0003_auto_20220811_1825'),
    ]

    operations = [
        migrations.AlterField(
            model_name='absence',
            name='child',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='absences', to='registrations.child'),
        ),
    ]
