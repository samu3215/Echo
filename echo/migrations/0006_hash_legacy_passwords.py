from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import migrations


def hash_legacy_passwords(apps, schema_editor):
    Usuario = apps.get_model('echo', 'Usuario')
    database = schema_editor.connection.alias

    for usuario in Usuario.objects.using(database).only('pk', 'password').iterator():
        try:
            identify_hasher(usuario.password)
        except (ValueError, TypeError):
            usuario.password = make_password(usuario.password)
            usuario.save(using=database, update_fields=['password'])


class Migration(migrations.Migration):
    dependencies = [
        ('echo', '0005_remove_activation_flow'),
    ]

    operations = [
        migrations.RunPython(hash_legacy_passwords, migrations.RunPython.noop),
    ]
