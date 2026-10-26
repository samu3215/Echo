from django.db import migrations


def activar_cuentas_pendientes(apps, schema_editor):
    Usuario = apps.get_model('echo', 'Usuario')
    Usuario.objects.filter(email_verificado=False).update(activo=True)


class Migration(migrations.Migration):

    dependencies = [
        ('echo', '0004_activacioncuenta_usuario_email_verificado'),
    ]

    operations = [
        migrations.RunPython(activar_cuentas_pendientes, migrations.RunPython.noop),
        migrations.DeleteModel(
            name='ActivacionCuenta',
        ),
        migrations.RemoveField(
            model_name='usuario',
            name='email_verificado',
        ),
    ]
