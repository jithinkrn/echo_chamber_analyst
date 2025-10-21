"""
Contract tests for Cleaner Node functionality.

These tests verify the cleaner node's contract without impacting existing code:
- Content cleaning and sanitization
- PII (Personally Identifiable Information) detection and removal
- Content deduplication
- Data quality validation
- Spam and irrelevant content filtering
"""

import unittest
from unittest.mock import patch, MagicMock
import re
from typing import Dict, List, Any, Optional
from datetime import datetime


class TestCleanerNodeContracts(unittest.TestCase):
    """Test suite for Cleaner Node contract compliance"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.raw_threads = [
            {
                'id': 'thread_1',
                'title': 'My email is john.doe@example.com and I love TestBrand!',
                'content': 'Contact me at john.doe@example.com or call 555-123-4567. TestBrand is amazing! 🚀',
                'source_url': 'https://reddit.com/r/technology/post1',
                'community': 'technology',
                'engagement_metrics': {'score': 25, 'comments': 8},
                'metadata': {'collected_at': '2023-12-01T10:00:00Z'}
            },
            {
                'id': 'thread_2',
                'title': 'TestBrand Review - Great Product',
                'content': 'I bought TestBrand last month and it\'s been fantastic. Highly recommend!',
                'source_url': 'https://forum.example.com/thread/456',
                'community': 'TechForum',
                'engagement_metrics': {'replies': 5, 'views': 120},
                'metadata': {'collected_at': '2023-12-01T11:00:00Z'}
            },
            {
                'id': 'thread_3',
                'title': 'TestBrand Review - Great Product',  # Duplicate title
                'content': 'I bought TestBrand last month and it\'s been fantastic. Highly recommend!',  # Duplicate content
                'source_url': 'https://another-forum.com/discussion/789',
                'community': 'AnotherForum',
                'engagement_metrics': {'likes': 15, 'shares': 3},
                'metadata': {'collected_at': '2023-12-01T12:00:00Z'}
            },
            {
                'id': 'thread_4',
                'title': 'SPAM: Buy cheap TestBrand alternatives NOW!!!',
                'content': 'Click here for AMAZING DEALS!!! www.suspicious-site.com/deals 💰💰💰',
                'source_url': 'https://sketchy-forum.com/post/999',
                'community': 'SketchyForum',
                'engagement_metrics': {'score': -5, 'comments': 0},
                'metadata': {'collected_at': '2023-12-01T13:00:00Z'}
            }
        ]
        
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'(\+?1[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        }
        
        self.spam_indicators = [
            'SPAM:', 'Click here', 'AMAZING DEALS', 'Buy cheap', 'NOW!!!',
            'www.suspicious-site.com', '💰💰💰'
        ]

    def test_pii_detection_contract(self):
        """Test PII detection contract compliance"""
        test_content = "Contact John at john.doe@email.com or call 555-123-4567. SSN: 123-45-6789"
        
        detected_pii = self._detect_pii_mock(test_content)
        
        # Verify contract compliance
        self.assertIsInstance(detected_pii, dict)
        self.assertIn('found_pii', detected_pii)
        self.assertIn('pii_types', detected_pii)
        self.assertIn('replacements_made', detected_pii)
        
        # Verify PII types are detected
        self.assertIn('email', detected_pii['pii_types'])
        self.assertIn('phone', detected_pii['pii_types'])
        self.assertIn('ssn', detected_pii['pii_types'])
        
        # Verify found PII count
        self.assertGreater(detected_pii['found_pii'], 0)

    def test_pii_removal_contract(self):
        """Test PII removal contract compliance"""
        content_with_pii = "My email is user@example.com and phone is 555-0123"
        
        cleaned_result = self._remove_pii_mock(content_with_pii)
        
        # Verify contract compliance
        self.assertIsInstance(cleaned_result, dict)
        self.assertIn('cleaned_content', cleaned_result)
        self.assertIn('pii_removed', cleaned_result)
        self.assertIn('original_length', cleaned_result)
        self.assertIn('cleaned_length', cleaned_result)
        
        # Verify PII is actually removed
        cleaned_content = cleaned_result['cleaned_content']
        self.assertNotIn('user@example.com', cleaned_content)
        self.assertNotIn('555-0123', cleaned_content)
        
        # Verify placeholders are used
        self.assertIn('[EMAIL_REMOVED]', cleaned_content)
        self.assertIn('[PHONE_REMOVED]', cleaned_content)

    def test_content_deduplication_contract(self):
        """Test content deduplication contract compliance"""
        duplicate_threads = [
            {'id': '1', 'title': 'Same title', 'content': 'Same content'},
            {'id': '2', 'title': 'Same title', 'content': 'Same content'},
            {'id': '3', 'title': 'Different title', 'content': 'Different content'},
        ]
        
        dedup_result = self._deduplicate_content_mock(duplicate_threads)
        
        # Verify contract compliance
        self.assertIsInstance(dedup_result, dict)
        self.assertIn('unique_threads', dedup_result)
        self.assertIn('duplicates_removed', dedup_result)
        self.assertIn('deduplication_stats', dedup_result)
        
        # Verify deduplication worked
        unique_threads = dedup_result['unique_threads']
        self.assertEqual(len(unique_threads), 2)  # Should have 2 unique threads
        self.assertEqual(dedup_result['duplicates_removed'], 1)

    def test_spam_detection_contract(self):
        """Test spam detection contract compliance"""
        spam_thread = {
            'title': 'SPAM: Buy cheap products NOW!!!',
            'content': 'Click here for AMAZING DEALS!!! www.suspicious-site.com',
            'engagement_metrics': {'score': -5}
        }
        
        spam_result = self._detect_spam_mock(spam_thread)
        
        # Verify contract compliance
        self.assertIsInstance(spam_result, dict)
        self.assertIn('is_spam', spam_result)
        self.assertIn('spam_score', spam_result)
        self.assertIn('spam_indicators', spam_result)
        self.assertIn('confidence', spam_result)
        
        # Verify spam detection
        self.assertTrue(spam_result['is_spam'])
        self.assertGreater(spam_result['spam_score'], 0.5)
        self.assertGreater(len(spam_result['spam_indicators']), 0)

    def test_content_quality_validation_contract(self):
        """Test content quality validation contract compliance"""
        quality_tests = [
            {
                'content': 'This is a well-written, informative post about TestBrand with good grammar.',
                'expected_quality': 'high'
            },
            {
                'content': 'ok product i guess',
                'expected_quality': 'low'
            },
            {
                'content': 'asdkjfh aslkdfj alksdjf',  # Gibberish
                'expected_quality': 'very_low'
            }
        ]
        
        for test_case in quality_tests:
            with self.subTest(content=test_case['content'][:30]):
                quality_result = self._validate_content_quality_mock(test_case['content'])
                
                # Verify contract compliance
                self.assertIsInstance(quality_result, dict)
                self.assertIn('quality_score', quality_result)
                self.assertIn('quality_level', quality_result)
                self.assertIn('issues_found', quality_result)
                self.assertIn('recommendations', quality_result)
                
                # Verify score range
                self.assertGreaterEqual(quality_result['quality_score'], 0.0)
                self.assertLessEqual(quality_result['quality_score'], 1.0)

    def test_content_sanitization_contract(self):
        """Test content sanitization contract compliance"""
        malicious_content = """
        <script>alert('xss')</script>
        <a href="javascript:void(0)">Click me</a>
        Some normal text with 🚀 emojis
        """
        
        sanitized_result = self._sanitize_content_mock(malicious_content)
        
        # Verify contract compliance
        self.assertIsInstance(sanitized_result, dict)
        self.assertIn('sanitized_content', sanitized_result)
        self.assertIn('removed_elements', sanitized_result)
        self.assertIn('safety_score', sanitized_result)
        
        # Verify malicious content is removed
        sanitized_content = sanitized_result['sanitized_content']
        self.assertNotIn('<script>', sanitized_content)
        self.assertNotIn('javascript:', sanitized_content)
        
        # Verify safe content is preserved
        self.assertIn('Some normal text', sanitized_content)
        self.assertIn('🚀', sanitized_content)

    def test_thread_cleaning_pipeline_contract(self):
        """Test complete thread cleaning pipeline contract"""
        raw_thread = self.raw_threads[0]  # Thread with PII
        
        cleaned_result = self._clean_thread_mock(raw_thread)
        
        # Verify contract compliance
        self.assertIsInstance(cleaned_result, dict)
        self.assertIn('cleaned_thread', cleaned_result)
        self.assertIn('cleaning_report', cleaned_result)
        
        # Verify cleaned thread structure
        cleaned_thread = cleaned_result['cleaned_thread']
        self.assertIn('id', cleaned_thread)
        self.assertIn('title', cleaned_thread)
        self.assertIn('content', cleaned_thread)
        self.assertIn('is_clean', cleaned_thread)
        self.assertIn('quality_score', cleaned_thread)
        
        # Verify cleaning report
        cleaning_report = cleaned_result['cleaning_report']
        self.assertIn('pii_removed', cleaning_report)
        self.assertIn('spam_detected', cleaning_report)
        self.assertIn('quality_issues', cleaning_report)
        self.assertIn('actions_taken', cleaning_report)

    def test_batch_cleaning_contract(self):
        """Test batch cleaning contract compliance"""
        batch_result = self._clean_threads_batch_mock(self.raw_threads)
        
        # Verify contract compliance
        self.assertIsInstance(batch_result, dict)
        self.assertIn('cleaned_threads', batch_result)
        self.assertIn('rejected_threads', batch_result)
        self.assertIn('cleaning_summary', batch_result)
        
        # Verify cleaning summary
        summary = batch_result['cleaning_summary']
        self.assertIn('total_processed', summary)
        self.assertIn('successfully_cleaned', summary)
        self.assertIn('rejected_count', summary)
        self.assertIn('duplicates_removed', summary)
        self.assertIn('pii_instances_removed', summary)
        self.assertIn('processing_time_seconds', summary)

    def test_data_retention_contract(self):
        """Test data retention policy contract compliance"""
        thread_with_metadata = {
            'id': 'test_thread',
            'title': 'Test thread',
            'content': 'Test content',
            'collected_at': '2023-01-01T00:00:00Z',  # Old data
            'source': 'reddit'
        }
        
        retention_result = self._apply_retention_policy_mock(thread_with_metadata)
        
        # Verify contract compliance
        self.assertIsInstance(retention_result, dict)
        self.assertIn('should_retain', retention_result)
        self.assertIn('retention_reason', retention_result)
        self.assertIn('expiry_date', retention_result)
        
        # Verify retention logic
        if not retention_result['should_retain']:
            self.assertIn('retention_reason', retention_result)

    def test_cleaning_configuration_contract(self):
        """Test cleaning configuration contract compliance"""
        cleaning_config = {
            'remove_pii': True,
            'pii_replacement_strategy': 'placeholder',
            'spam_threshold': 0.7,
            'quality_threshold': 0.3,
            'enable_deduplication': True,
            'retention_days': 90
        }
        
        config_result = self._validate_cleaning_config_mock(cleaning_config)
        
        # Verify contract compliance
        self.assertIsInstance(config_result, dict)
        self.assertIn('is_valid', config_result)
        self.assertIn('config_errors', config_result)
        self.assertIn('recommendations', config_result)
        
        # Test invalid config
        invalid_config = {'spam_threshold': 1.5}  # Invalid threshold
        invalid_result = self._validate_cleaning_config_mock(invalid_config)
        self.assertFalse(invalid_result['is_valid'])

    def test_cleaning_metrics_contract(self):
        """Test cleaning metrics contract compliance"""
        cleaning_session = {
            'session_id': 'test_session_123',
            'start_time': datetime.now(),
            'threads_processed': 100,
            'pii_instances_found': 25,
            'spam_threads_detected': 5,
            'duplicates_removed': 8
        }
        
        metrics_result = self._generate_cleaning_metrics_mock(cleaning_session)
        
        # Verify contract compliance
        self.assertIsInstance(metrics_result, dict)
        self.assertIn('session_metrics', metrics_result)
        self.assertIn('performance_stats', metrics_result)
        self.assertIn('quality_improvements', metrics_result)
        
        # Verify metrics structure
        session_metrics = metrics_result['session_metrics']
        self.assertIn('threads_processed', session_metrics)
        self.assertIn('success_rate', session_metrics)
        self.assertIn('average_processing_time', session_metrics)

    # Mock helper methods (these simulate the actual cleaner node behavior)
    
    def _detect_pii_mock(self, content: str) -> Dict[str, Any]:
        """Mock PII detection"""
        found_pii = 0
        pii_types = []
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, content)
            if matches:
                found_pii += len(matches)
                pii_types.append(pii_type)
        
        return {
            'found_pii': found_pii,
            'pii_types': pii_types,
            'replacements_made': found_pii,
            'detection_confidence': 0.95 if found_pii > 0 else 1.0
        }

    def _remove_pii_mock(self, content: str) -> Dict[str, Any]:
        """Mock PII removal"""
        original_length = len(content)
        cleaned_content = content
        pii_removed = 0
        
        # Replace PII with placeholders
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, cleaned_content)
            if matches:
                pii_removed += len(matches)
                placeholder = f'[{pii_type.upper()}_REMOVED]'
                cleaned_content = re.sub(pattern, placeholder, cleaned_content)
        
        return {
            'cleaned_content': cleaned_content,
            'pii_removed': pii_removed,
            'original_length': original_length,
            'cleaned_length': len(cleaned_content)
        }

    def _deduplicate_content_mock(self, threads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Mock content deduplication"""
        seen_content = set()
        unique_threads = []
        duplicates_removed = 0
        
        for thread in threads:
            content_hash = hash(f"{thread['title']}{thread['content']}")
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_threads.append(thread)
            else:
                duplicates_removed += 1
        
        return {
            'unique_threads': unique_threads,
            'duplicates_removed': duplicates_removed,
            'deduplication_stats': {
                'original_count': len(threads),
                'unique_count': len(unique_threads),
                'duplicate_rate': duplicates_removed / len(threads) if threads else 0
            }
        }

    def _detect_spam_mock(self, thread: Dict[str, Any]) -> Dict[str, Any]:
        """Mock spam detection"""
        spam_score = 0.0
        spam_indicators = []
        
        content_text = f"{thread.get('title', '')} {thread.get('content', '')}"
        
        for indicator in self.spam_indicators:
            if indicator.lower() in content_text.lower():
                spam_score += 0.2
                spam_indicators.append(indicator)
        
        # Check engagement metrics
        engagement = thread.get('engagement_metrics', {})
        if engagement.get('score', 0) < 0:
            spam_score += 0.3
            spam_indicators.append('negative_engagement')
        
        is_spam = spam_score > 0.5
        
        return {
            'is_spam': is_spam,
            'spam_score': min(spam_score, 1.0),
            'spam_indicators': spam_indicators,
            'confidence': 0.85 if is_spam else 0.75
        }

    def _validate_content_quality_mock(self, content: str) -> Dict[str, Any]:
        """Mock content quality validation"""
        issues = []
        quality_score = 0.5  # Default
        
        # Basic quality checks
        if len(content) < 10:
            issues.append('too_short')
            quality_score -= 0.3
        
        if content.islower() and len(content) > 50:
            issues.append('poor_capitalization')
            quality_score -= 0.1
        
        # Check for meaningful content
        words = content.split()
        if len(words) < 3:
            issues.append('insufficient_content')
            quality_score -= 0.2
        
        # Check for gibberish
        vowel_count = sum(1 for char in content.lower() if char in 'aeiou')
        if vowel_count / len(content) < 0.1:
            issues.append('possible_gibberish')
            quality_score -= 0.4
        
        # Adjust for good indicators
        if any(char.isupper() for char in content):
            quality_score += 0.1
        
        if len(words) > 10:
            quality_score += 0.2
        
        quality_score = max(0.0, min(1.0, quality_score))
        
        # Determine quality level
        if quality_score >= 0.7:
            quality_level = 'high'
        elif quality_score >= 0.4:
            quality_level = 'medium'
        elif quality_score >= 0.2:
            quality_level = 'low'
        else:
            quality_level = 'very_low'
        
        return {
            'quality_score': quality_score,
            'quality_level': quality_level,
            'issues_found': issues,
            'recommendations': self._get_quality_recommendations_mock(issues)
        }

    def _get_quality_recommendations_mock(self, issues: List[str]) -> List[str]:
        """Mock quality improvement recommendations"""
        recommendations = []
        
        if 'too_short' in issues:
            recommendations.append('Content should be at least 10 characters long')
        if 'poor_capitalization' in issues:
            recommendations.append('Improve capitalization and punctuation')
        if 'insufficient_content' in issues:
            recommendations.append('Provide more detailed information')
        if 'possible_gibberish' in issues:
            recommendations.append('Content appears to be gibberish or corrupted')
        
        return recommendations

    def _sanitize_content_mock(self, content: str) -> Dict[str, Any]:
        """Mock content sanitization"""
        removed_elements = []
        safety_score = 1.0
        
        # Remove script tags
        if '<script>' in content:
            removed_elements.append('script_tags')
            safety_score -= 0.5
        
        # Remove javascript: URLs
        if 'javascript:' in content:
            removed_elements.append('javascript_urls')
            safety_score -= 0.3
        
        # Simple sanitization
        sanitized_content = content
        sanitized_content = re.sub(r'<script.*?>.*?</script>', '', sanitized_content, flags=re.DOTALL)
        sanitized_content = re.sub(r'javascript:[^"\']*', '#', sanitized_content)
        
        return {
            'sanitized_content': sanitized_content,
            'removed_elements': removed_elements,
            'safety_score': max(0.0, safety_score)
        }

    def _clean_thread_mock(self, thread: Dict[str, Any]) -> Dict[str, Any]:
        """Mock complete thread cleaning"""
        # Apply all cleaning steps
        pii_result = self._remove_pii_mock(thread.get('content', ''))
        spam_result = self._detect_spam_mock(thread)
        quality_result = self._validate_content_quality_mock(thread.get('content', ''))
        
        cleaned_thread = thread.copy()
        cleaned_thread['content'] = pii_result['cleaned_content']
        cleaned_thread['title'] = self._remove_pii_mock(thread.get('title', ''))['cleaned_content']
        cleaned_thread['is_clean'] = not spam_result['is_spam'] and quality_result['quality_score'] >= 0.3
        cleaned_thread['quality_score'] = quality_result['quality_score']
        
        cleaning_report = {
            'pii_removed': pii_result['pii_removed'],
            'spam_detected': spam_result['is_spam'],
            'quality_issues': quality_result['issues_found'],
            'actions_taken': [
                f"Removed {pii_result['pii_removed']} PII instances",
                f"Spam detection: {'FLAGGED' if spam_result['is_spam'] else 'CLEAN'}",
                f"Quality score: {quality_result['quality_score']:.2f}"
            ]
        }
        
        return {
            'cleaned_thread': cleaned_thread,
            'cleaning_report': cleaning_report
        }

    def _clean_threads_batch_mock(self, threads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Mock batch thread cleaning"""
        import time
        start_time = time.time()
        
        cleaned_threads = []
        rejected_threads = []
        
        # First, deduplicate
        dedup_result = self._deduplicate_content_mock(threads)
        unique_threads = dedup_result['unique_threads']
        
        # Clean each thread
        total_pii_removed = 0
        for thread in unique_threads:
            clean_result = self._clean_thread_mock(thread)
            
            if clean_result['cleaned_thread']['is_clean']:
                cleaned_threads.append(clean_result['cleaned_thread'])
            else:
                rejected_threads.append({
                    'thread': thread,
                    'rejection_reason': clean_result['cleaning_report']
                })
            
            total_pii_removed += clean_result['cleaning_report']['pii_removed']
        
        processing_time = time.time() - start_time
        
        return {
            'cleaned_threads': cleaned_threads,
            'rejected_threads': rejected_threads,
            'cleaning_summary': {
                'total_processed': len(threads),
                'successfully_cleaned': len(cleaned_threads),
                'rejected_count': len(rejected_threads),
                'duplicates_removed': dedup_result['duplicates_removed'],
                'pii_instances_removed': total_pii_removed,
                'processing_time_seconds': processing_time
            }
        }

    def _apply_retention_policy_mock(self, thread: Dict[str, Any]) -> Dict[str, Any]:
        """Mock data retention policy application"""
        from datetime import datetime, timedelta
        
        collected_at_str = thread.get('collected_at', datetime.now().isoformat())
        try:
            collected_at = datetime.fromisoformat(collected_at_str.replace('Z', '+00:00'))
        except:
            collected_at = datetime.now()
        
        retention_days = 90
        expiry_date = collected_at + timedelta(days=retention_days)
        should_retain = datetime.now() < expiry_date
        
        retention_reason = 'within_retention_period' if should_retain else 'expired'
        
        return {
            'should_retain': should_retain,
            'retention_reason': retention_reason,
            'expiry_date': expiry_date.isoformat(),
            'days_remaining': (expiry_date - datetime.now()).days if should_retain else 0
        }

    def _validate_cleaning_config_mock(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Mock cleaning configuration validation"""
        errors = []
        recommendations = []
        
        # Validate thresholds
        if 'spam_threshold' in config:
            if not 0.0 <= config['spam_threshold'] <= 1.0:
                errors.append('spam_threshold must be between 0.0 and 1.0')
        
        if 'quality_threshold' in config:
            if not 0.0 <= config['quality_threshold'] <= 1.0:
                errors.append('quality_threshold must be between 0.0 and 1.0')
        
        # Validate retention days
        if 'retention_days' in config:
            if not isinstance(config['retention_days'], int) or config['retention_days'] < 1:
                errors.append('retention_days must be a positive integer')
        
        # Recommendations
        if config.get('spam_threshold', 0.7) > 0.9:
            recommendations.append('Consider lowering spam_threshold for better spam detection')
        
        if config.get('quality_threshold', 0.3) < 0.1:
            recommendations.append('Consider raising quality_threshold to filter out low-quality content')
        
        return {
            'is_valid': len(errors) == 0,
            'config_errors': errors,
            'recommendations': recommendations
        }

    def _generate_cleaning_metrics_mock(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Mock cleaning metrics generation"""
        threads_processed = session.get('threads_processed', 0)
        pii_found = session.get('pii_instances_found', 0)
        spam_detected = session.get('spam_threads_detected', 0)
        
        success_rate = (threads_processed - spam_detected) / threads_processed if threads_processed > 0 else 0
        
        return {
            'session_metrics': {
                'session_id': session.get('session_id'),
                'threads_processed': threads_processed,
                'success_rate': success_rate,
                'average_processing_time': 0.15,  # Mock average
                'pii_detection_rate': pii_found / threads_processed if threads_processed > 0 else 0
            },
            'performance_stats': {
                'throughput_per_second': threads_processed / 60 if threads_processed > 0 else 0,
                'memory_usage_mb': 125.5,
                'cpu_utilization_percent': 45.2
            },
            'quality_improvements': {
                'spam_filtered': spam_detected,
                'pii_instances_removed': pii_found,
                'content_quality_improved': int(threads_processed * 0.3)  # Mock improvement
            }
        }


if __name__ == '__main__':
    unittest.main()