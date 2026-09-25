from django.db import migrations, models


def mark_practical_reminders(apps, schema_editor):
    name = "mailer/practical_reminder.html"
    apps.get_model("mailer", "GenericEmail").objects.filter(body_template__name=name).update(is_html=True)
    apps.get_model("mailer", "MailArchive").objects.filter(template=name).update(is_html=True)


class Migration(migrations.Migration):
    dependencies = [("mailer", "0008_alter_mailarchive_status")]
    operations = [
        migrations.AddField("genericemail", "is_html", models.BooleanField(default=False, verbose_name="Mail HTML")),
        migrations.AddField("mailarchive", "is_html", models.BooleanField(default=False, verbose_name="Mail HTML")),
        migrations.RunPython(mark_practical_reminders, migrations.RunPython.noop),
    ]
