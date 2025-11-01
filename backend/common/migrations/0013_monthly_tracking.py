# Generated migration for switching from weekly to monthly tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0012_add_week_to_painpoint_constraint'),
    ]

    operations = [
        # Remove old unique_together constraints
        migrations.AlterUniqueTogether(
            name='painpoint',
            unique_together=set(),
        ),

        # Add month_year field to PainPoint
        migrations.AddField(
            model_name='painpoint',
            name='month_year',
            field=models.CharField(blank=True, max_length=7, null=True),
        ),

        # Add month_year field to Thread
        migrations.AddField(
            model_name='thread',
            name='month_year',
            field=models.CharField(blank=True, max_length=7, null=True),
        ),

        # Add collection_months field to Campaign
        migrations.AddField(
            model_name='campaign',
            name='collection_months',
            field=models.IntegerField(default=6),
        ),

        # Remove old fields (optional - can keep for backward compatibility)
        migrations.RemoveField(
            model_name='painpoint',
            name='week_number',
        ),
        migrations.RemoveField(
            model_name='thread',
            name='week_number',
        ),
        migrations.RemoveField(
            model_name='campaign',
            name='collection_weeks',
        ),

        # Add new unique_together constraint for PainPoint
        migrations.AlterUniqueTogether(
            name='painpoint',
            unique_together={('keyword', 'campaign', 'community', 'month_year')},
        ),
    ]
