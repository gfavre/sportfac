# Generated by Django 3.2.25 on 2024-10-17 14:52

from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0026_auto_20241011_1803'),
        ('appointments', '0009_rental'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='rental',
            options={'ordering': ('child',), 'verbose_name': 'Rental', 'verbose_name_plural': 'Rentals'},
        ),
        migrations.AlterField(
            model_name='rental',
            name='amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=6, verbose_name='Amount'),
        ),
        migrations.AlterField(
            model_name='rental',
            name='invoice',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rentals', to='registrations.bill', verbose_name='Invoice'),
        ),
        migrations.AlterField(
            model_name='rental',
            name='pickup_appointment',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pickup_rental', to='appointments.appointment', verbose_name='Pickup slot'),
        ),
        migrations.AlterField(
            model_name='rental',
            name='return_appointment',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='return_rental', to='appointments.appointment', verbose_name='Return slot'),
        ),
    ]