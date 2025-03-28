# Generated by Django 3.2.25 on 2024-10-14 16:21

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0026_auto_20241011_1803'),
        ('appointments', '0008_auto_20241011_1803'),
    ]

    operations = [
        migrations.CreateModel(
            name='Rental',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=6, verbose_name='Amount')),
                ('paid', models.BooleanField(default=False, verbose_name='Paid')),
                ('child', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rentals', to='registrations.child', verbose_name='Child')),
                ('invoice', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rentals', to='registrations.bill', verbose_name='Invoice')),
                ('pickup_appointment', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pickup_rental', to='appointments.appointment', verbose_name='Pickup slot')),
                ('return_appointment', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='return_rental', to='appointments.appointment', verbose_name='Return slot')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
