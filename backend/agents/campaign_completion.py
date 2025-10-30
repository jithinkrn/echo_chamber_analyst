"""
Auto-completion task for campaigns based on end_date and budget limits.
"""

import logging
from datetime import datetime
from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal

from common.models import Campaign

logger = get_task_logger(__name__)


@shared_task(
    name='check_and_complete_campaigns',
    bind=True,
    max_retries=3,
    default_retry_delay=300
)
def check_and_complete_campaigns(self):
    """
    Periodic task to check and automatically mark campaigns as completed based on:
    1. End date has passed
    2. Budget limit has been reached or exceeded

    Runs every 10 minutes to check for campaigns that should be completed.
    """
    logger.info("🔍 Checking campaigns for auto-completion...")

    try:
        now = timezone.now()
        completed_count = 0

        # Find active campaigns that should be completed
        campaigns_to_complete = Campaign.objects.filter(
            Q(status='active') | Q(status='paused')  # Check both active and paused campaigns
        ).filter(
            Q(end_date__lte=now) |  # End date has passed
            Q(budget_limit__lte=models.F('current_spend'))  # Budget exceeded
        )

        for campaign in campaigns_to_complete:
            reason = []

            # Check end date
            if campaign.end_date and campaign.end_date <= now:
                reason.append(f"end date reached ({campaign.end_date.strftime('%Y-%m-%d')})")

            # Check budget limit
            if campaign.budget_limit and campaign.current_spend >= campaign.budget_limit:
                reason.append(f"budget limit reached (${campaign.current_spend}/${campaign.budget_limit})")

            if reason:
                campaign.status = 'completed'
                campaign.schedule_enabled = False  # Disable scheduling
                campaign.save(update_fields=['status', 'schedule_enabled'])

                completed_count += 1
                logger.info(
                    f"✅ Auto-completed campaign '{campaign.name}' (ID: {campaign.id}) - "
                    f"Reason: {', '.join(reason)}"
                )

        result = {
            'status': 'success',
            'checked_at': now.isoformat(),
            'completed_count': completed_count,
            'message': f'Checked campaigns and auto-completed {completed_count} campaign(s)'
        }

        if completed_count > 0:
            logger.info(f"🎉 Auto-completed {completed_count} campaign(s)")
        else:
            logger.debug("No campaigns needed completion")

        return result

    except Exception as e:
        logger.error(f"❌ Error in check_and_complete_campaigns: {str(e)}")
        raise self.retry(exc=e)


# Import models after task definition to avoid circular imports
from django.db import models
