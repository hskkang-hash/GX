from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0026_change_external_order_status_to_many_to_many'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderstatusmapping',
            name='name',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ] 