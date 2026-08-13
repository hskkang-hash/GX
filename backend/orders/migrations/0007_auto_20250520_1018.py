from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0006_remove_order_delivery_address'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='orderitem',
            name='dimension_unit',
        ),
        migrations.RemoveField(
            model_name='orderitem',
            name='weight_unit',
        ),
        migrations.RunSQL(
            """
            ALTER TABLE orders_orderitem
            ALTER COLUMN dimension_h TYPE jsonb USING NULL,
            ALTER COLUMN dimension_l TYPE jsonb USING NULL,
            ALTER COLUMN dimension_w TYPE jsonb USING NULL,
            ALTER COLUMN weight TYPE jsonb USING NULL;
            """
        ),
    ]
