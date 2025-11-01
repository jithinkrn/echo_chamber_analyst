# Generated migration for adding week_number to PainPoint unique constraint
# This enables proper week-by-week pain point tracking across 4 weeks

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0011_alter_community_unique_together_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='painpoint',
            unique_together={('keyword', 'campaign', 'community', 'week_number')},
        ),
    ]
