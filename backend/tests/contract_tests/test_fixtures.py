"""
Test fixtures and utilities for contract tests.

This module provides shared test data, mock utilities, and helper functions
for all node contract tests without impacting existing code.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import random


class TestDataGenerator:
    """Generate realistic test data for contract tests"""
    
    @staticmethod
    def generate_threads(count: int = 10, brand_name: str = "TestBrand") -> List[Dict[str, Any]]:
        """Generate realistic thread data for testing"""
        thread_templates = [
            {
                'title_template': f'{brand_name} is {{sentiment_word}} for productivity',
                'content_template': f'I have been using {brand_name} for {{duration}} and {{experience}}',
                'sentiment': 'positive'
            },
            {
                'title_template': f'{brand_name} vs {{competitor}} comparison',
                'content_template': f'{brand_name} has {{feature_comparison}} but {{competitor}} is {{comparison_aspect}}',
                'sentiment': 'neutral'
            },
            {
                'title_template': f'{brand_name} {{issue_type}} issues',
                'content_template': f'Had problems with {brand_name} {{issue_details}}. {{resolution_status}}',
                'sentiment': 'negative'
            }
        ]
        
        sentiment_words = {
            'positive': ['amazing', 'fantastic', 'excellent', 'great', 'wonderful'],
            'negative': ['terrible', 'awful', 'disappointing', 'frustrating', 'poor'],
            'neutral': ['okay', 'decent', 'average', 'standard', 'typical']
        }
        
        threads = []
        for i in range(count):
            template = random.choice(thread_templates)
            
            # Generate thread data based on template
            if template['sentiment'] == 'positive':
                title = template['title_template'].format(
                    sentiment_word=random.choice(sentiment_words['positive'])
                )
                content = template['content_template'].format(
                    duration=random.choice(['2 weeks', '1 month', '3 months', '6 months']),
                    experience=random.choice(['my productivity increased significantly', 'it has been amazing', 'I love the features'])
                )
                quality_score = random.uniform(0.7, 1.0)
                engagement_score = random.randint(15, 100)
            
            elif template['sentiment'] == 'negative':
                title = template['title_template'].format(
                    issue_type=random.choice(['support', 'login', 'sync', 'performance'])
                )
                content = template['content_template'].format(
                    issue_details=random.choice(['response time', 'feature access', 'data sync']),
                    resolution_status=random.choice(['Not resolved yet', 'Still waiting', 'Poor experience'])
                )
                quality_score = random.uniform(0.4, 0.8)
                engagement_score = random.randint(5, 50)
            
            else:  # neutral
                title = template['title_template'].format(
                    competitor=random.choice(['CompetitorA', 'CompetitorB', 'Alternative'])
                )
                content = template['content_template'].format(
                    feature_comparison=random.choice(['better features', 'more options', 'good interface']),
                    competitor=random.choice(['CompetitorA', 'CompetitorB']),
                    comparison_aspect=random.choice(['cheaper', 'simpler', 'more established'])
                )
                quality_score = random.uniform(0.5, 0.9)
                engagement_score = random.randint(10, 80)
            
            thread = {
                'id': f'thread_{i+1}',
                'title': title,
                'content': content,
                'source_url': f'https://example-{random.choice(["reddit", "forum", "reviews"])}.com/thread/{i+1}',
                'community': random.choice(['technology', 'productivity', 'reviews', 'support']),
                'engagement_metrics': {
                    'score': engagement_score,
                    'comments': random.randint(0, 25),
                    'views': random.randint(50, 500)
                },
                'collected_at': (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                'quality_score': quality_score,
                'sentiment': template['sentiment']
            }
            
            threads.append(thread)
        
        return threads
    
    @staticmethod
    def generate_knowledge_base(brand_name: str = "TestBrand") -> List[Dict[str, Any]]:
        """Generate knowledge base entries for testing"""
        return [
            {
                'id': 'kb_features_1',
                'content': f'{brand_name} is a comprehensive productivity platform offering real-time collaboration, task management, document editing, and team communication tools. It integrates seamlessly with popular business applications.',
                'metadata': {
                    'source': 'product_documentation',
                    'category': 'features',
                    'last_updated': datetime.now().isoformat(),
                    'relevance_tags': ['productivity', 'collaboration', 'features', 'integration']
                }
            },
            {
                'id': 'kb_pricing_1',
                'content': f'{brand_name} offers flexible pricing plans: Individual at $9.99/month, Team at $19.99/month per user, and Enterprise with custom pricing. All plans include core features with advanced capabilities in higher tiers.',
                'metadata': {
                    'source': 'pricing_page',
                    'category': 'pricing',
                    'last_updated': datetime.now().isoformat(),
                    'relevance_tags': ['pricing', 'plans', 'cost', 'individual', 'team', 'enterprise']
                }
            },
            {
                'id': 'kb_support_1',
                'content': f'{brand_name} provides 24/7 customer support through multiple channels: live chat, email tickets, phone support for premium users, and extensive documentation. Response times vary by plan level.',
                'metadata': {
                    'source': 'support_documentation',
                    'category': 'support',
                    'last_updated': datetime.now().isoformat(),
                    'relevance_tags': ['support', 'help', 'customer service', 'contact']
                }
            },
            {
                'id': 'kb_security_1',
                'content': f'{brand_name} implements enterprise-grade security with end-to-end encryption, SOC 2 compliance, GDPR compliance, and regular security audits. Data is stored in secure, geographically distributed data centers.',
                'metadata': {
                    'source': 'security_documentation',
                    'category': 'security',
                    'last_updated': datetime.now().isoformat(),
                    'relevance_tags': ['security', 'privacy', 'encryption', 'compliance', 'GDPR']
                }
            },
            {
                'id': 'kb_integrations_1',
                'content': f'{brand_name} integrates with over 100 popular business tools including Slack, Microsoft Teams, Google Workspace, Salesforce, Jira, and GitHub. Custom integrations available via REST API.',
                'metadata': {
                    'source': 'integration_documentation',
                    'category': 'integrations',
                    'last_updated': datetime.now().isoformat(),
                    'relevance_tags': ['integrations', 'api', 'slack', 'teams', 'google', 'salesforce']
                }
            }
        ]
    
    @staticmethod
    def generate_pain_points(severity_range: tuple = (1, 10)) -> List[Dict[str, Any]]:
        """Generate realistic pain points for testing"""
        pain_point_templates = [
            {
                'category': 'customer_support',
                'descriptions': [
                    'Long response times for support tickets',
                    'Limited support hours for lower-tier plans',
                    'Difficulty reaching human agents'
                ],
                'severity_range': (5, 8)
            },
            {
                'category': 'pricing',
                'descriptions': [
                    'Pricing perceived as too high for small teams',
                    'Limited features in basic plan',
                    'No trial period for enterprise features'
                ],
                'severity_range': (4, 7)
            },
            {
                'category': 'usability',
                'descriptions': [
                    'Steep learning curve for new users',
                    'Interface can be overwhelming',
                    'Mobile app lacks some desktop features'
                ],
                'severity_range': (3, 6)
            },
            {
                'category': 'performance',
                'descriptions': [
                    'Slow loading times during peak hours',
                    'Occasional sync issues between devices',
                    'Memory usage concerns on older devices'
                ],
                'severity_range': (6, 9)
            }
        ]
        
        pain_points = []
        for template in pain_point_templates:
            description = random.choice(template['descriptions'])
            severity = random.randint(*template['severity_range'])
            
            pain_point = {
                'category': template['category'],
                'description': description,
                'severity_score': severity,
                'frequency': random.randint(1, 10),
                'supporting_evidence': [f'thread_{random.randint(1, 100)}' for _ in range(random.randint(1, 5))],
                'recommended_actions': generate_recommendations(template['category'])
            }
            pain_points.append(pain_point)
        
        return pain_points


def generate_recommendations(category: str) -> List[str]:
    """Generate recommendations based on pain point category"""
    recommendations_map = {
        'customer_support': [
            'Increase support team capacity during peak hours',
            'Implement better self-service options',
            'Provide support training for faster resolution'
        ],
        'pricing': [
            'Consider more flexible pricing tiers',
            'Offer extended trial periods',
            'Provide volume discounts for larger teams'
        ],
        'usability': [
            'Improve onboarding process',
            'Create more tutorial content',
            'Simplify interface for new users'
        ],
        'performance': [
            'Optimize server infrastructure',
            'Implement better caching strategies',
            'Provide performance monitoring tools'
        ]
    }
    
    return recommendations_map.get(category, ['Address identified issues', 'Monitor closely'])


class MockUtilities:
    """Utility functions for mocking in contract tests"""
    
    @staticmethod
    def simulate_processing_time(base_time: float = 0.1, variance: float = 0.05) -> float:
        """Simulate realistic processing time with variance"""
        import time
        processing_time = base_time + random.uniform(-variance, variance)
        time.sleep(max(0, processing_time))
        return processing_time
    
    @staticmethod
    def generate_confidence_score(base_confidence: float = 0.8, variance: float = 0.1) -> float:
        """Generate realistic confidence scores"""
        confidence = base_confidence + random.uniform(-variance, variance)
        return max(0.0, min(1.0, confidence))
    
    @staticmethod
    def mock_api_response(success: bool = True, data: Any = None, error_type: str = None) -> Dict[str, Any]:
        """Generate mock API response"""
        if success:
            return {
                'success': True,
                'data': data,
                'timestamp': datetime.now().isoformat(),
                'response_time_ms': random.randint(50, 500)
            }
        else:
            return {
                'success': False,
                'error': {
                    'type': error_type or 'mock_error',
                    'message': f'Mock {error_type or "error"} for testing',
                    'code': random.randint(400, 500)
                },
                'timestamp': datetime.now().isoformat(),
                'response_time_ms': random.randint(100, 1000)
            }
    
    @staticmethod
    def simulate_rate_limit(calls_made: int, limit: int = 100) -> Dict[str, Any]:
        """Simulate rate limiting"""
        remaining = max(0, limit - calls_made)
        is_rate_limited = remaining == 0
        
        return {
            'is_rate_limited': is_rate_limited,
            'calls_remaining': remaining,
            'calls_made': calls_made,
            'reset_time': (datetime.now() + timedelta(hours=1)).isoformat() if is_rate_limited else None
        }


class ContractTestValidators:
    """Validators for contract test compliance"""
    
    @staticmethod
    def validate_response_structure(response: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """Validate that response has required structure"""
        missing_fields = [field for field in required_fields if field not in response]
        
        return {
            'is_valid': len(missing_fields) == 0,
            'missing_fields': missing_fields,
            'extra_fields': [field for field in response.keys() if field not in required_fields],
            'validation_errors': [f'Missing required field: {field}' for field in missing_fields]
        }
    
    @staticmethod
    def validate_score_range(score: float, min_value: float = 0.0, max_value: float = 1.0) -> bool:
        """Validate that score is within expected range"""
        return min_value <= score <= max_value
    
    @staticmethod
    def validate_timestamp_format(timestamp_str: str) -> bool:
        """Validate timestamp format"""
        try:
            datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_list_structure(data_list: List[Dict[str, Any]], required_item_fields: List[str]) -> Dict[str, Any]:
        """Validate structure of list items"""
        validation_results = []
        
        for i, item in enumerate(data_list):
            item_validation = ContractTestValidators.validate_response_structure(item, required_item_fields)
            if not item_validation['is_valid']:
                validation_results.append({
                    'index': i,
                    'errors': item_validation['validation_errors']
                })
        
        return {
            'is_valid': len(validation_results) == 0,
            'total_items': len(data_list),
            'invalid_items': validation_results
        }


# Performance test utilities
class PerformanceTestHelpers:
    """Helpers for performance testing in contracts"""
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs) -> Dict[str, Any]:
        """Measure function execution time"""
        import time
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000  # Convert to ms
        
        return {
            'execution_time_ms': execution_time,
            'success': success,
            'result': result,
            'error': error
        }
    
    @staticmethod
    def generate_performance_baseline() -> Dict[str, float]:
        """Generate baseline performance metrics"""
        return {
            'scout_data_collection_ms': 2500.0,
            'content_cleaning_ms': 150.0,
            'sentiment_analysis_ms': 300.0,
            'rag_response_generation_ms': 1200.0,
            'trend_analysis_ms': 800.0,
            'competitive_analysis_ms': 600.0
        }


# Configuration test utilities
class ConfigurationTestHelpers:
    """Helpers for testing configuration handling"""
    
    @staticmethod
    def generate_valid_configs() -> Dict[str, Dict[str, Any]]:
        """Generate valid configurations for different nodes"""
        return {
            'scout_config': {
                'brand_name': 'TestBrand',
                'competitors': ['CompetitorA', 'CompetitorB'],
                'sources': ['reddit', 'forums', 'reviews'],
                'max_results_per_source': 50,
                'date_range_days': 30
            },
            'cleaner_config': {
                'remove_pii': True,
                'pii_replacement_strategy': 'placeholder',
                'spam_threshold': 0.7,
                'quality_threshold': 0.3,
                'enable_deduplication': True
            },
            'analyst_config': {
                'sentiment_analysis': {'enabled': True, 'granularity': 'sentence'},
                'trend_analysis': {'enabled': True, 'time_windows': ['1d', '7d', '30d']},
                'topic_modeling': {'enabled': True, 'num_topics': 10}
            },
            'chatbot_config': {
                'retrieval': {'max_results': 5, 'relevance_threshold': 0.7},
                'generation': {'max_tokens': 500, 'temperature': 0.7},
                'safety': {'content_filtering': True, 'toxicity_threshold': 0.1}
            }
        }
    
    @staticmethod
    def generate_invalid_configs() -> Dict[str, List[Dict[str, Any]]]:
        """Generate invalid configurations for testing error handling"""
        return {
            'scout_config': [
                {},  # Empty config
                {'brand_name': ''},  # Empty brand name
                {'brand_name': 'Test', 'sources': []},  # No sources
                {'brand_name': 'Test', 'sources': ['invalid_source']}  # Invalid source
            ],
            'cleaner_config': [
                {'spam_threshold': 1.5},  # Invalid threshold
                {'quality_threshold': -0.1},  # Negative threshold
                {'pii_replacement_strategy': 'invalid_strategy'}  # Invalid strategy
            ],
            'analyst_config': [
                {'sentiment_analysis': {'granularity': 'invalid_level'}},  # Invalid granularity
                {'trend_analysis': {'time_windows': []}},  # Empty time windows
                {'topic_modeling': {'num_topics': -1}}  # Invalid number
            ],
            'chatbot_config': [
                {'retrieval': {'max_results': -1}},  # Negative max results
                {'generation': {'temperature': 2.0}},  # Invalid temperature
                {'safety': {'toxicity_threshold': 1.5}}  # Invalid threshold
            ]
        }


# Export all utilities for easy importing
__all__ = [
    'TestDataGenerator',
    'MockUtilities', 
    'ContractTestValidators',
    'PerformanceTestHelpers',
    'ConfigurationTestHelpers'
]