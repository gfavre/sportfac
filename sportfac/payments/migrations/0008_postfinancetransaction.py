# Generated by Django 3.2.16 on 2023-07-14 09:09

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0018_alter_bill_payment_method'),
        ('payments', '0007_alter_datatranstransaction_webhook'),
    ]

    operations = [
        migrations.CreateModel(
            name='PostfinanceTransaction',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('status', model_utils.fields.StatusField(choices=[('PENDING', 'Pending'), ('CONFIRMED', 'Confirmed'), ('PROCESSING', 'Processing'), ('FAILED', 'Failed'), ('AUTHORIZED', 'Authorized'), ('COMPLETED', 'Completed'), ('FULFILL', 'Fulfill'), ('DECLINE', 'Decline'), ('VOIDED', 'Voided')], default='PENDING', max_length=100, no_check_for_status=True, verbose_name='status')),
                ('status_changed', model_utils.fields.MonitorField(default=django.utils.timezone.now, monitor='status', verbose_name='status changed')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('transaction_id', models.BigIntegerField(db_index=True)),
                ('payment_page_url', models.URLField(blank=True, null=True)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='postfinance_transactions', to='registrations.bill')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]