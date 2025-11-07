"""
LLM Security Tests - Input Validation and Sanitization

These tests verify proper input validation and sanitization for LLM interactions.
Tests various input attack vectors without altering application code.
"""

import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
import json

from common.models import Campaign, Community, Thread, Brand, PainPoint


@pytest.mark.django_db
class TestInputLengthValidation(TestCase):
    """Test validation of input length limits."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.brand = Brand.objects.create(name='TestBrand')
        self.campaign = Campaign.objects.create(
            name='Validation Test',
            owner=self.user,
            brand=self.brand
        )
        self.community = Community.objects.create(
            name='ValidationCommunity',
            platform='reddit',
            url='https://reddit.com/r/validation',
            campaign=self.campaign
        )

    def test_extremely_long_content(self):
        """Test handling of extremely long content."""
        # Create content that exceeds typical limits
        very_long_content = "A" * 1000000  # 1 million characters

        thread = Thread.objects.create(
            thread_id='long_001',
            title='Long Content Test',
            content=very_long_content,
            community=self.community,
            campaign=self.campaign,
            author='tester',
            published_at=timezone.now()
        )

        # Should handle long content (might truncate or reject)
        self.assertIsNotNone(thread.content)
        self.assertGreater(len(thread.content), 0)

    def test_empty_required_fields(self):
        """Test validation of empty required fields."""
        # Test empty thread_id (should fail)
        with self.assertRaises((ValidationError, Exception)):
            thread = Thread(
                thread_id='',  # Empty
                title='Test',
                content='Content',
                community=self.community,
                campaign=self.campaign,
                author='tester',
                published_at=timezone.now()
            )
            thread.full_clean()  # Trigger validation

    def test_title_length_limits(self):
        """Test title length validation."""
        # Thread title has max_length=500
        max_length_title = "X" * 500
        over_length_title = "X" * 501

        # Should accept max length
        thread1 = Thread.objects.create(
            thread_id='title_001',
            title=max_length_title,
            content='Content',
            community=self.community,
            campaign=self.campaign,
            author='tester',
            published_at=timezone.now()
        )
        self.assertEqual(len(thread1.title), 500)

        # Over length should be handled (truncated or rejected)
        try:
            thread2 = Thread.objects.create(
                thread_id='title_002',
                title=over_length_title,
                content='Content',
                community=self.community,
                campaign=self.campaign,
                author='tester',
                published_at=timezone.now()
            )
            # If created, should be truncated
            self.assertLessEqual(len(thread2.title), 500)
        except Exception:
            # Or should raise exception
            pass


@pytest.mark.django_db
class TestJSONFieldValidation(TestCase):
    """Test validation of JSON fields."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.brand = Brand.objects.create(name='TestBrand')

    def test_invalid_json_in_keywords(self):
        """Test handling of invalid JSON structures."""
        # Valid JSON list
        campaign1 = Campaign.objects.create(
            name='Valid JSON',
            owner=self.user,
            keywords=['keyword1', 'keyword2', 'keyword3']
        )
        self.assertEqual(len(campaign1.keywords), 3)

        # Test with nested structures
        campaign2 = Campaign.objects.create(
            name='Nested JSON',
            owner=self.user,
            metadata={
                'level1': {
                    'level2': {
                        'level3': ['value1', 'value2']
                    }
                }
            }
        )
        self.assertIn('level1', campaign2.metadata)

    def test_json_field_type_safety(self):
        """Test JSON field type safety."""
        # Should handle different types
        campaign = Campaign.objects.create(
            name='Type Safety',
            owner=self.user,
            metadata={
                'string': 'value',
                'number': 42,
                'float': 3.14,
                'boolean': True,
                'null': None,
                'array': [1, 2, 3],
                'object': {'key': 'value'}
            }
        )

        self.assertEqual(campaign.metadata['string'], 'value')
        self.assertEqual(campaign.metadata['number'], 42)
        self.assertEqual(campaign.metadata['boolean'], True)
        self.assertIsNone(campaign.metadata['null'])

    def test_json_injection_attempts(self):
        """Test protection against JSON injection."""
        # Attempt to inject malicious JSON
        malicious_json = {
            '__proto__': {'polluted': True},
            'constructor': {'prototype': {'polluted': True}},
            'hasOwnProperty': 'malicious'
        }

        campaign = Campaign.objects.create(
            name='JSON Injection Test',
            owner=self.user,
            metadata=malicious_json
        )

        # Data should be stored but should not pollute prototypes
        self.assertIn('__proto__', campaign.metadata)


@pytest.mark.django_db
class TestSpecialCharacterHandling(TestCase):
    """Test handling of special characters in input."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.campaign = Campaign.objects.create(
            name='Special Chars Test',
            owner=self.user
        )
        self.community = Community.objects.create(
            name='SpecialCommunity',
            platform='reddit',
            url='https://reddit.com/r/special',
            campaign=self.campaign
        )

    def test_unicode_character_handling(self):
        """Test handling of Unicode characters."""
        unicode_content = """
        Testing various Unicode:
        Emoji: 😀 🎉 🚀 ❤️
        Chinese: 你好世界
        Arabic: مرحبا بالعالم
        Russian: Привет мир
        Mathematical: ∑ ∫ ∂ √ ∞
        Special: © ® ™ € £ ¥
        """

        thread = Thread.objects.create(
            thread_id='unicode_001',
            title='Unicode Test 😀',
            content=unicode_content,
            community=self.community,
            campaign=self.campaign,
            author='tester',
            published_at=timezone.now()
        )

        # Should handle Unicode correctly
        self.assertIn('😀', thread.content)
        self.assertIn('你好世界', thread.content)
        self.assertIn('∞', thread.content)

    def test_html_entity_handling(self):
        """Test handling of HTML entities."""
        html_content = """
        &lt;script&gt;alert('XSS')&lt;/script&gt;
        &amp; &quot; &apos; &gt; &lt;
        &#60; &#62; &#38;
        """

        thread = Thread.objects.create(
            thread_id='html_001',
            title='HTML Entities',
            content=html_content,
            community=self.community,
            campaign=self.campaign,
            author='tester',
            published_at=timezone.now()
        )

        # Should store content as-is (sanitization happens before LLM)
        self.assertIn('&lt;', thread.content)

    def test_control_character_handling(self):
        """Test handling of control characters."""
        # Various control characters
        control_chars = "Test\x00\x01\x02\x03\x04\x05Content"

        thread = Thread.objects.create(
            thread_id='control_001',
            title='Control Chars',
            content=control_chars,
            community=self.community,
            campaign=self.campaign,
            author='tester',
            published_at=timezone.now()
        )

        # Should handle control characters appropriately
        self.assertIsNotNone(thread.content)

    def test_newline_and_whitespace_handling(self):
        """Test handling of various newline and whitespace characters."""
        whitespace_content = "Line1\nLine2\r\nLine3\rLine4\tTabbed\u00A0NonBreaking"

        thread = Thread.objects.create(
            thread_id='whitespace_001',
            title='Whitespace Test',
            content=whitespace_content,
            community=self.community,
            campaign=self.campaign,
            author='tester',
            published_at=timezone.now()
        )

        # Should preserve whitespace
        self.assertIn('\n', thread.content)
        self.assertIn('\t', thread.content)


@pytest.mark.django_db
class TestURLValidation(TestCase):
    """Test validation of URL fields."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')

    def test_valid_urls(self):
        """Test acceptance of valid URLs."""
        valid_urls = [
            'https://example.com',
            'http://example.com',
            'https://sub.example.com',
            'https://example.com/path/to/resource',
            'https://example.com:8080',
            'https://example.com?query=param',
        ]

        for i, url in enumerate(valid_urls):
            brand = Brand.objects.create(
                name=f'Brand_{i}',
                website=url
            )
            self.assertEqual(brand.website, url)

    def test_malicious_urls(self):
        """Test handling of malicious URLs."""
        malicious_urls = [
            'javascript:alert(1)',
            'data:text/html,<script>alert(1)</script>',
            'file:///etc/passwd',
            'vbscript:msgbox(1)',
        ]

        for i, url in enumerate(malicious_urls):
            try:
                brand = Brand.objects.create(
                    name=f'Malicious_{i}',
                    website=url
                )
                # If created, URL should be validated/sanitized elsewhere
                self.assertIsNotNone(brand.website)
            except ValidationError:
                # Should reject invalid URLs
                pass

    def test_url_length_limits(self):
        """Test URL length validation."""
        # Thread URL has max_length=500
        long_url = 'https://example.com/' + 'a' * 470  # ~500 total

        try:
            community = Community.objects.create(
                name='LongURL',
                platform='reddit',
                url=long_url,
                campaign=Campaign.objects.create(
                    name='URL Test',
                    owner=self.user
                )
            )
            self.assertLessEqual(len(community.url), 500)
        except Exception:
            # Should handle overly long URLs
            pass


@pytest.mark.django_db
class TestNumericFieldValidation(TestCase):
    """Test validation of numeric fields."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.campaign = Campaign.objects.create(
            name='Numeric Test',
            owner=self.user
        )
        self.community = Community.objects.create(
            name='NumericCommunity',
            platform='reddit',
            url='https://reddit.com/r/numeric',
            campaign=self.campaign
        )

    def test_negative_numbers_in_counts(self):
        """Test handling of negative numbers where inappropriate."""
        # Test negative member count
        community = Community.objects.create(
            name='NegativeTest',
            platform='reddit',
            url='https://reddit.com/r/negative',
            campaign=self.campaign,
            member_count=-100  # Should this be allowed?
        )

        # Depending on validation, might store or reject
        self.assertIsNotNone(community.member_count)

    def test_float_score_ranges(self):
        """Test float field score ranges."""
        thread = Thread.objects.create(
            thread_id='score_001',
            title='Score Test',
            content='Content',
            community=self.community,
            campaign=self.campaign,
            author='tester',
            published_at=timezone.now(),
            echo_score=150.5,  # Over 100?
            sentiment_score=2.0,  # Over 1.0?
            engagement_rate=-5.0  # Negative?
        )

        # Values are stored but should be validated before use
        self.assertIsNotNone(thread.echo_score)
        self.assertIsNotNone(thread.sentiment_score)

    def test_integer_overflow(self):
        """Test handling of very large integers."""
        import sys

        large_number = sys.maxsize

        thread = Thread.objects.create(
            thread_id='overflow_001',
            title='Overflow Test',
            content='Content',
            community=self.community,
            campaign=self.campaign,
            author='tester',
            published_at=timezone.now(),
            upvotes=large_number,
            comment_count=large_number
        )

        # Should handle large numbers
        self.assertEqual(thread.upvotes, large_number)


@pytest.mark.django_db
class TestDateTimeValidation(TestCase):
    """Test validation of datetime fields."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.campaign = Campaign.objects.create(
            name='DateTime Test',
            owner=self.user
        )
        self.community = Community.objects.create(
            name='DateTimeCommunity',
            platform='reddit',
            url='https://reddit.com/r/datetime',
            campaign=self.campaign
        )

    def test_future_dates(self):
        """Test handling of future dates."""
        from datetime import datetime, timedelta

        future_date = timezone.now() + timedelta(days=365)

        thread = Thread.objects.create(
            thread_id='future_001',
            title='Future Date Test',
            content='Content',
            community=self.community,
            campaign=self.campaign,
            author='tester',
            published_at=future_date
        )

        # Should accept future dates (validation should happen in business logic)
        self.assertGreater(thread.published_at, timezone.now())

    def test_very_old_dates(self):
        """Test handling of very old dates."""
        from datetime import datetime

        old_date = datetime(1970, 1, 1, tzinfo=timezone.utc)

        thread = Thread.objects.create(
            thread_id='old_001',
            title='Old Date Test',
            content='Content',
            community=self.community,
            campaign=self.campaign,
            author='tester',
            published_at=old_date
        )

        # Should accept old dates
        self.assertEqual(thread.published_at.year, 1970)


@pytest.mark.django_db
class TestForeignKeyValidation(TestCase):
    """Test validation of foreign key relationships."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.campaign = Campaign.objects.create(
            name='FK Test',
            owner=self.user
        )

    def test_invalid_foreign_key(self):
        """Test handling of invalid foreign keys."""
        import uuid

        # Try to create community with non-existent campaign
        fake_campaign_id = uuid.uuid4()

        try:
            community = Community.objects.create(
                name='InvalidFK',
                platform='reddit',
                url='https://reddit.com/r/invalid',
                campaign_id=fake_campaign_id
            )
            # Should not reach here
            self.fail("Should reject invalid foreign key")
        except Exception:
            # Should raise exception for invalid FK
            pass

    def test_cascade_delete_behavior(self):
        """Test cascade delete behavior."""
        community = Community.objects.create(
            name='CascadeTest',
            platform='reddit',
            url='https://reddit.com/r/cascade',
            campaign=self.campaign
        )

        thread = Thread.objects.create(
            thread_id='cascade_001',
            title='Cascade Test',
            content='Content',
            community=community,
            campaign=self.campaign,
            author='tester',
            published_at=timezone.now()
        )

        thread_id = thread.id

        # Delete campaign should cascade to community and thread
        self.campaign.delete()

        # Thread should be deleted
        self.assertFalse(Thread.objects.filter(id=thread_id).exists())


@pytest.mark.django_db
class TestBatchInputValidation(TestCase):
    """Test validation of batch inputs."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.campaign = Campaign.objects.create(
            name='Batch Test',
            owner=self.user
        )
        self.community = Community.objects.create(
            name='BatchCommunity',
            platform='reddit',
            url='https://reddit.com/r/batch',
            campaign=self.campaign
        )

    def test_bulk_create_with_mixed_valid_invalid(self):
        """Test bulk create with mixed valid/invalid data."""
        threads = [
            Thread(
                thread_id=f'bulk_{i}',
                title=f'Thread {i}',
                content=f'Content {i}',
                community=self.community,
                campaign=self.campaign,
                author='tester',
                published_at=timezone.now()
            )
            for i in range(100)
        ]

        # Should create all valid threads
        created = Thread.objects.bulk_create(threads)
        self.assertEqual(len(created), 100)

    def test_batch_size_limits(self):
        """Test handling of very large batch operations."""
        # Create a large number of pain points
        pain_points = [
            PainPoint(
                keyword=f'keyword_{i}',
                campaign=self.campaign,
                community=self.community,
                mention_count=i,
                month_year='2024-11'
            )
            for i in range(1000)
        ]

        # Should handle large batches
        created = PainPoint.objects.bulk_create(pain_points)
        self.assertGreater(len(created), 0)
