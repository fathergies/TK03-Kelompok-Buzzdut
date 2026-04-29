# Generated for TK03 ticket status frontend support.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ticketing', '0002_seat_ticket_hasrelationship'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='status',
            field=models.CharField(
                choices=[
                    ('ACTIVE', 'Aktif'),
                    ('USED', 'Terpakai'),
                    ('CANCELLED', 'Dibatalkan'),
                ],
                default='ACTIVE',
                max_length=20,
            ),
        ),
    ]
