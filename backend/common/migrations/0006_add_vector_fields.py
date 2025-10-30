# Generated migration for pgvector embedding fields

from django.db import migrations, models
from pgvector.django import VectorExtension, VectorField


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0005_campaign_metadata_influencer_advocacy_score_and_more'),
    ]

    operations = [
        # Enable pgvector extension
        VectorExtension(),

        # Add embedding fields to ProcessedContent
        migrations.AddField(
            model_name='processedcontent',
            name='embedding',
            field=VectorField(dimensions=1536, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='processedcontent',
            name='embedding_model',
            field=models.CharField(max_length=100, default='text-embedding-3-small'),
        ),
        migrations.AddField(
            model_name='processedcontent',
            name='embedding_created_at',
            field=models.DateTimeField(null=True, blank=True),
        ),

        # Add embedding fields to Insight
        migrations.AddField(
            model_name='insight',
            name='embedding',
            field=VectorField(dimensions=1536, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='insight',
            name='embedding_model',
            field=models.CharField(max_length=100, default='text-embedding-3-small'),
        ),
        migrations.AddField(
            model_name='insight',
            name='embedding_created_at',
            field=models.DateTimeField(null=True, blank=True),
        ),

        # Add embedding fields to PainPoint
        migrations.AddField(
            model_name='painpoint',
            name='embedding',
            field=VectorField(dimensions=1536, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='painpoint',
            name='embedding_model',
            field=models.CharField(max_length=100, default='text-embedding-3-small'),
        ),
        migrations.AddField(
            model_name='painpoint',
            name='embedding_created_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
