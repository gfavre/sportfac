from django.db import migrations, models
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0004_auto_20201029_1524'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppointmentType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('label', models.CharField(max_length=50, verbose_name='Displayed name')),
                ('start', models.DateTimeField()),
                ('end', models.DateTimeField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='appointmentslot',
            name='title',
        ),
    ]
