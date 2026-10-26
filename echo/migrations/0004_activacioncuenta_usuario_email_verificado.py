import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('echo', '0003_alter_recuperacioncontrasena_codigo_expira_en_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='email_verificado',
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name='ActivacionCuenta',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('token_hash', models.CharField(max_length=64, unique=True)),
                ('expira_en', models.DateTimeField()),
                (
                    'usuario',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='activacion_cuenta',
                        to='echo.usuario',
                    ),
                ),
            ],
        ),
    ]
