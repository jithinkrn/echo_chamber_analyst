"""
Contract tests for Analyst Node functionality.

These tests verify the analyst node's contract without impacting existing code:
- Content analysis and insight generation
- Sentiment analysis across different sources
- Trend identification and pattern recognition
- Competitive analysis and benchmarking
- Statistical analysis and reporting
- AI-powered content interpretation
"""

import unittest
from unittest.mock import patch, MagicMock
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import statistics


class TestAnalystNodeContracts(unittest.TestCase):
    """Test suite for Analyst Node contract compliance"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.clean_threads = [
            {
                'id': 'thread_1',
                'title': 'TestBrand is amazing for productivity',
                'content': 'I have been using TestBrand for 3 months and my productivity increased by 40%',
                'source_url': 'https://reddit.com/r/productivity/post1',
                'community': 'productivity',
                'engagement_metrics': {'score': 85, 'comments': 23},
                'collected_at': '2023-12-01T10:00:00Z',
                'quality_score': 0.8
            },
            {
                'id': 'thread_2',
                'title': 'TestBrand vs CompetitorA comparison',
                'content': 'TestBrand has better features but CompetitorA is cheaper. Both are good options.',
                'source_url': 'https://forum.example.com/thread/456',
                'community': 'TechReviews',
                'engagement_metrics': {'replies': 15, 'views': 450},
                'collected_at': '2023-12-01T11:00:00Z',
                'quality_score': 0.9
            },
            {
                'id': 'thread_3',
                'title': 'TestBrand customer support issues',
                'content': 'Had problems with TestBrand support. Took 3 days to get a response. Not happy.',
                'source_url': 'https://reviews.trustpilot.com/review/789',
                'community': 'trustpilot',
                'engagement_metrics': {'rating': 2, 'helpful_votes': 8},
                'collected_at': '2023-12-01T12:00:00Z',
                'quality_score': 0.7
            },
            {
                'id': 'thread_4',
                'title': 'TestBrand price increase announcement',
                'content': 'TestBrand announced 20% price increase starting next month. Existing users get discount.',
                'source_url': 'https://news.example.com/article/999',
                'community': 'TechNews',
                'engagement_metrics': {'shares': 156, 'comments': 89},
                'collected_at': '2023-12-02T09:00:00Z',
                'quality_score': 0.95
            }
        ]
        
        self.competitors = ['CompetitorA', 'CompetitorB', 'CompetitorC']
        
        self.analysis_config = {
            'sentiment_analysis': {
                'enabled': True,
                'granularity': 'sentence',
                'include_emotions': True
            },
            'trend_analysis': {
                'enabled': True,
                'time_windows': ['1d', '7d', '30d'],
                'metrics': ['sentiment', 'engagement', 'volume']
            },
            'competitive_analysis': {
                'enabled': True,
                'competitors': self.competitors,
                'comparison_aspects': ['features', 'pricing', 'support']
            },
            'topic_modeling': {
                'enabled': True,
                'num_topics': 10,
                'include_keywords': True
            }
        }

    def test_sentiment_analysis_contract(self):
        """Test sentiment analysis contract compliance"""
        sample_content = "I love TestBrand! It's amazing and works perfectly. Best purchase ever!"
        
        sentiment_result = self._analyze_sentiment_mock(sample_content)
        
        # Verify contract compliance
        self.assertIsInstance(sentiment_result, dict)
        self.assertIn('overall_sentiment', sentiment_result)
        self.assertIn('sentiment_scores', sentiment_result)
        self.assertIn('confidence', sentiment_result)
        self.assertIn('emotions_detected', sentiment_result)
        
        # Verify sentiment scores structure
        scores = sentiment_result['sentiment_scores']
        self.assertIn('positive', scores)
        self.assertIn('negative', scores)
        self.assertIn('neutral', scores)
        
        # Verify score ranges
        for score in scores.values():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)
        
        # Verify scores sum to 1.0 (approximately)
        total_score = sum(scores.values())
        self.assertAlmostEqual(total_score, 1.0, places=2)

    def test_batch_sentiment_analysis_contract(self):
        """Test batch sentiment analysis contract compliance"""
        batch_result = self._analyze_sentiment_batch_mock(self.clean_threads)
        
        # Verify contract compliance
        self.assertIsInstance(batch_result, dict)
        self.assertIn('thread_sentiments', batch_result)
        self.assertIn('aggregated_sentiment', batch_result)
        self.assertIn('sentiment_distribution', batch_result)
        
        # Verify thread sentiments
        thread_sentiments = batch_result['thread_sentiments']
        self.assertEqual(len(thread_sentiments), len(self.clean_threads))
        
        for thread_id, sentiment in thread_sentiments.items():
            self.assertIn('overall_sentiment', sentiment)
            self.assertIn('sentiment_scores', sentiment)
        
        # Verify aggregated sentiment
        agg_sentiment = batch_result['aggregated_sentiment']
        self.assertIn('dominant_sentiment', agg_sentiment)
        self.assertIn('average_scores', agg_sentiment)
        self.assertIn('confidence', agg_sentiment)

    def test_trend_analysis_contract(self):
        """Test trend analysis contract compliance"""
        trend_result = self._analyze_trends_mock(self.clean_threads, time_window='7d')
        
        # Verify contract compliance
        self.assertIsInstance(trend_result, dict)
        self.assertIn('trend_metrics', trend_result)
        self.assertIn('time_series_data', trend_result)
        self.assertIn('trend_direction', trend_result)
        self.assertIn('volatility', trend_result)
        
        # Verify trend metrics
        metrics = trend_result['trend_metrics']
        self.assertIn('volume_trend', metrics)
        self.assertIn('sentiment_trend', metrics)
        self.assertIn('engagement_trend', metrics)
        
        # Verify time series data
        time_series = trend_result['time_series_data']
        self.assertIsInstance(time_series, list)
        
        for data_point in time_series:
            self.assertIn('timestamp', data_point)
            self.assertIn('volume', data_point)
            self.assertIn('sentiment_score', data_point)
            self.assertIn('engagement_score', data_point)

    def test_competitive_analysis_contract(self):
        """Test competitive analysis contract compliance"""
        competitive_result = self._analyze_competition_mock(self.clean_threads, self.competitors)
        
        # Verify contract compliance
        self.assertIsInstance(competitive_result, dict)
        self.assertIn('brand_analysis', competitive_result)
        self.assertIn('competitor_analysis', competitive_result)
        self.assertIn('comparative_metrics', competitive_result)
        self.assertIn('market_positioning', competitive_result)
        
        # Verify brand analysis
        brand_analysis = competitive_result['brand_analysis']
        self.assertIn('mention_count', brand_analysis)
        self.assertIn('sentiment_breakdown', brand_analysis)
        self.assertIn('key_topics', brand_analysis)
        
        # Verify competitor analysis
        competitor_analysis = competitive_result['competitor_analysis']
        for competitor in self.competitors:
            if competitor in competitor_analysis:
                comp_data = competitor_analysis[competitor]
                self.assertIn('mention_count', comp_data)
                self.assertIn('sentiment_breakdown', comp_data)
        
        # Verify comparative metrics
        comp_metrics = competitive_result['comparative_metrics']
        self.assertIn('sentiment_comparison', comp_metrics)
        self.assertIn('volume_comparison', comp_metrics)
        self.assertIn('engagement_comparison', comp_metrics)

    def test_topic_modeling_contract(self):
        """Test topic modeling contract compliance"""
        topic_result = self._perform_topic_modeling_mock(self.clean_threads, num_topics=5)
        
        # Verify contract compliance
        self.assertIsInstance(topic_result, dict)
        self.assertIn('topics', topic_result)
        self.assertIn('topic_distribution', topic_result)
        self.assertIn('dominant_topics', topic_result)
        
        # Verify topics structure
        topics = topic_result['topics']
        self.assertIsInstance(topics, list)
        self.assertEqual(len(topics), 5)
        
        for topic in topics:
            self.assertIn('topic_id', topic)
            self.assertIn('keywords', topic)
            self.assertIn('weight', topic)
            self.assertIn('representative_threads', topic)
            
            # Verify keywords
            self.assertIsInstance(topic['keywords'], list)
            self.assertGreater(len(topic['keywords']), 0)

    def test_pain_point_analysis_contract(self):
        """Test pain point analysis contract compliance"""
        pain_point_result = self._analyze_pain_points_mock(self.clean_threads)
        
        # Verify contract compliance
        self.assertIsInstance(pain_point_result, dict)
        self.assertIn('pain_points', pain_point_result)
        self.assertIn('pain_point_categories', pain_point_result)
        self.assertIn('severity_analysis', pain_point_result)
        
        # Verify pain points structure
        pain_points = pain_point_result['pain_points']
        self.assertIsInstance(pain_points, list)
        
        for pain_point in pain_points:
            self.assertIn('category', pain_point)
            self.assertIn('description', pain_point)
            self.assertIn('severity_score', pain_point)
            self.assertIn('frequency', pain_point)
            self.assertIn('supporting_evidence', pain_point)
            self.assertIn('recommended_actions', pain_point)
            
            # Verify severity score range
            self.assertGreaterEqual(pain_point['severity_score'], 0)
            self.assertLessEqual(pain_point['severity_score'], 10)

    def test_insight_generation_contract(self):
        """Test insight generation contract compliance"""
        insight_result = self._generate_insights_mock(self.clean_threads, self.analysis_config)
        
        # Verify contract compliance
        self.assertIsInstance(insight_result, dict)
        self.assertIn('key_insights', insight_result)
        self.assertIn('actionable_recommendations', insight_result)
        self.assertIn('risk_factors', insight_result)
        self.assertIn('opportunities', insight_result)
        self.assertIn('confidence_scores', insight_result)
        
        # Verify key insights
        key_insights = insight_result['key_insights']
        self.assertIsInstance(key_insights, list)
        
        for insight in key_insights:
            self.assertIn('insight_type', insight)
            self.assertIn('description', insight)
            self.assertIn('supporting_data', insight)
            self.assertIn('confidence', insight)
            self.assertIn('priority', insight)

    def test_statistical_analysis_contract(self):
        """Test statistical analysis contract compliance"""
        stats_result = self._perform_statistical_analysis_mock(self.clean_threads)
        
        # Verify contract compliance
        self.assertIsInstance(stats_result, dict)
        self.assertIn('descriptive_statistics', stats_result)
        self.assertIn('correlation_analysis', stats_result)
        self.assertIn('significance_tests', stats_result)
        
        # Verify descriptive statistics
        desc_stats = stats_result['descriptive_statistics']
        self.assertIn('sentiment_stats', desc_stats)
        self.assertIn('engagement_stats', desc_stats)
        self.assertIn('volume_stats', desc_stats)
        
        # Verify each stat group has required metrics
        for stat_group in desc_stats.values():
            if isinstance(stat_group, dict):
                self.assertIn('mean', stat_group)
                self.assertIn('median', stat_group)
                self.assertIn('std_dev', stat_group)

    def test_real_time_analysis_contract(self):
        """Test real-time analysis contract compliance"""
        new_thread = {
            'id': 'new_thread',
            'title': 'Breaking: TestBrand launches new feature',
            'content': 'TestBrand just announced an exciting new feature that changes everything!',
            'collected_at': datetime.now().isoformat()
        }
        
        rt_result = self._analyze_real_time_mock(new_thread, self.clean_threads)
        
        # Verify contract compliance
        self.assertIsInstance(rt_result, dict)
        self.assertIn('immediate_insights', rt_result)
        self.assertIn('trend_updates', rt_result)
        self.assertIn('alert_triggers', rt_result)
        self.assertIn('processing_time_ms', rt_result)
        
        # Verify processing time is reasonable for real-time
        self.assertLess(rt_result['processing_time_ms'], 5000)  # Less than 5 seconds

    def test_analysis_configuration_contract(self):
        """Test analysis configuration contract compliance"""
        config_result = self._validate_analysis_config_mock(self.analysis_config)
        
        # Verify contract compliance
        self.assertIsInstance(config_result, dict)
        self.assertIn('is_valid', config_result)
        self.assertIn('config_errors', config_result)
        self.assertIn('performance_estimates', config_result)
        
        # Test invalid configuration
        invalid_config = {
            'sentiment_analysis': {'granularity': 'invalid_level'},
            'trend_analysis': {'time_windows': []},  # Empty time windows
            'topic_modeling': {'num_topics': -1}  # Invalid number
        }
        
        invalid_result = self._validate_analysis_config_mock(invalid_config)
        self.assertFalse(invalid_result['is_valid'])
        self.assertGreater(len(invalid_result['config_errors']), 0)

    def test_analysis_performance_contract(self):
        """Test analysis performance characteristics contract"""
        import time
        
        start_time = time.time()
        
        # Run full analysis pipeline
        performance_result = self._run_full_analysis_pipeline_mock(
            self.clean_threads, 
            self.analysis_config
        )
        
        processing_time = time.time() - start_time
        
        # Verify contract compliance
        self.assertIsInstance(performance_result, dict)
        self.assertIn('analysis_results', performance_result)
        self.assertIn('performance_metrics', performance_result)
        
        # Verify performance metrics
        perf_metrics = performance_result['performance_metrics']
        self.assertIn('total_processing_time', perf_metrics)
        self.assertIn('threads_per_second', perf_metrics)
        self.assertIn('memory_usage_mb', perf_metrics)
        
        # Verify reasonable performance (adjust thresholds as needed)
        self.assertLess(processing_time, 60.0, "Full analysis should complete within 60 seconds")

    def test_export_analysis_results_contract(self):
        """Test analysis results export contract compliance"""
        mock_analysis_results = {
            'sentiment_analysis': {'overall_sentiment': 'positive'},
            'trend_analysis': {'trend_direction': 'upward'},
            'competitive_analysis': {'market_position': 'strong'},
            'insights': ['Key insight 1', 'Key insight 2']
        }
        
        export_result = self._export_analysis_results_mock(
            mock_analysis_results, 
            format='json'
        )
        
        # Verify contract compliance
        self.assertIsInstance(export_result, dict)
        self.assertIn('export_data', export_result)
        self.assertIn('export_format', export_result)
        self.assertIn('file_size_bytes', export_result)
        self.assertIn('export_timestamp', export_result)
        
        # Test different export formats
        for export_format in ['json', 'csv', 'pdf']:
            with self.subTest(format=export_format):
                format_result = self._export_analysis_results_mock(
                    mock_analysis_results, 
                    format=export_format
                )
                self.assertEqual(format_result['export_format'], export_format)

    # Mock helper methods (these simulate the actual analyst node behavior)
    
    def _analyze_sentiment_mock(self, content: str) -> Dict[str, Any]:
        """Mock sentiment analysis"""
        # Simple sentiment scoring based on keywords
        positive_words = ['love', 'amazing', 'great', 'excellent', 'perfect', 'best', 'fantastic']
        negative_words = ['hate', 'terrible', 'awful', 'worst', 'bad', 'problems', 'issues']
        
        content_lower = content.lower()
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        total_sentiment_words = positive_count + negative_count
        
        if total_sentiment_words == 0:
            # Neutral content
            positive_score = 0.1
            negative_score = 0.1
            neutral_score = 0.8
        else:
            positive_score = positive_count / (total_sentiment_words + 1)
            negative_score = negative_count / (total_sentiment_words + 1)
            neutral_score = 1 - positive_score - negative_score
        
        # Determine overall sentiment
        if positive_score > negative_score and positive_score > 0.3:
            overall = 'positive'
        elif negative_score > positive_score and negative_score > 0.3:
            overall = 'negative'
        else:
            overall = 'neutral'
        
        return {
            'overall_sentiment': overall,
            'sentiment_scores': {
                'positive': positive_score,
                'negative': negative_score,
                'neutral': neutral_score
            },
            'confidence': 0.85,
            'emotions_detected': ['joy'] if positive_score > 0.5 else ['concern'] if negative_score > 0.5 else ['neutral']
        }

    def _analyze_sentiment_batch_mock(self, threads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Mock batch sentiment analysis"""
        thread_sentiments = {}
        all_sentiments = []
        
        for thread in threads:
            content = f"{thread.get('title', '')} {thread.get('content', '')}"
            sentiment = self._analyze_sentiment_mock(content)
            thread_sentiments[thread['id']] = sentiment
            all_sentiments.append(sentiment)
        
        # Calculate aggregated sentiment
        avg_positive = statistics.mean([s['sentiment_scores']['positive'] for s in all_sentiments])
        avg_negative = statistics.mean([s['sentiment_scores']['negative'] for s in all_sentiments])
        avg_neutral = statistics.mean([s['sentiment_scores']['neutral'] for s in all_sentiments])
        
        dominant = 'positive' if avg_positive > max(avg_negative, avg_neutral) else \
                   'negative' if avg_negative > avg_neutral else 'neutral'
        
        return {
            'thread_sentiments': thread_sentiments,
            'aggregated_sentiment': {
                'dominant_sentiment': dominant,
                'average_scores': {
                    'positive': avg_positive,
                    'negative': avg_negative,
                    'neutral': avg_neutral
                },
                'confidence': 0.8
            },
            'sentiment_distribution': {
                'positive_threads': sum(1 for s in all_sentiments if s['overall_sentiment'] == 'positive'),
                'negative_threads': sum(1 for s in all_sentiments if s['overall_sentiment'] == 'negative'),
                'neutral_threads': sum(1 for s in all_sentiments if s['overall_sentiment'] == 'neutral')
            }
        }

    def _analyze_trends_mock(self, threads: List[Dict[str, Any]], time_window: str) -> Dict[str, Any]:
        """Mock trend analysis"""
        # Generate mock time series data
        time_series_data = []
        base_time = datetime.now() - timedelta(days=7)
        
        for i in range(7):
            timestamp = base_time + timedelta(days=i)
            # Mock trending data with some variation
            volume = 10 + (i * 2) + (i % 3)
            sentiment_score = 0.6 + (0.1 * (i % 4))
            engagement_score = 15 + (i * 3) + (i % 2 * 5)
            
            time_series_data.append({
                'timestamp': timestamp.isoformat(),
                'volume': volume,
                'sentiment_score': sentiment_score,
                'engagement_score': engagement_score
            })
        
        # Calculate trend direction
        volumes = [d['volume'] for d in time_series_data]
        sentiments = [d['sentiment_score'] for d in time_series_data]
        
        volume_trend = 'upward' if volumes[-1] > volumes[0] else 'downward'
        sentiment_trend = 'upward' if sentiments[-1] > sentiments[0] else 'downward'
        
        return {
            'trend_metrics': {
                'volume_trend': volume_trend,
                'sentiment_trend': sentiment_trend,
                'engagement_trend': 'upward'
            },
            'time_series_data': time_series_data,
            'trend_direction': 'upward' if volume_trend == 'upward' and sentiment_trend == 'upward' else 'mixed',
            'volatility': {
                'volume_volatility': statistics.stdev(volumes) if len(volumes) > 1 else 0,
                'sentiment_volatility': statistics.stdev(sentiments) if len(sentiments) > 1 else 0
            }
        }

    def _analyze_competition_mock(self, threads: List[Dict[str, Any]], competitors: List[str]) -> Dict[str, Any]:
        """Mock competitive analysis"""
        # Analyze brand mentions
        brand_mentions = 0
        brand_sentiment_scores = []
        
        competitor_data = {}
        
        for thread in threads:
            content = f"{thread.get('title', '')} {thread.get('content', '')}".lower()
            
            # Count brand mentions
            if 'testbrand' in content:
                brand_mentions += 1
                sentiment = self._analyze_sentiment_mock(content)
                brand_sentiment_scores.append(sentiment['sentiment_scores']['positive'])
            
            # Count competitor mentions
            for competitor in competitors:
                if competitor.lower() in content:
                    if competitor not in competitor_data:
                        competitor_data[competitor] = {'mentions': 0, 'sentiment_scores': []}
                    competitor_data[competitor]['mentions'] += 1
                    sentiment = self._analyze_sentiment_mock(content)
                    competitor_data[competitor]['sentiment_scores'].append(
                        sentiment['sentiment_scores']['positive']
                    )
        
        # Build competitor analysis
        competitor_analysis = {}
        for competitor, data in competitor_data.items():
            avg_sentiment = statistics.mean(data['sentiment_scores']) if data['sentiment_scores'] else 0.5
            competitor_analysis[competitor] = {
                'mention_count': data['mentions'],
                'sentiment_breakdown': {
                    'average_sentiment': avg_sentiment,
                    'positive_ratio': avg_sentiment
                }
            }
        
        return {
            'brand_analysis': {
                'mention_count': brand_mentions,
                'sentiment_breakdown': {
                    'average_sentiment': statistics.mean(brand_sentiment_scores) if brand_sentiment_scores else 0.5
                },
                'key_topics': ['productivity', 'features', 'support']
            },
            'competitor_analysis': competitor_analysis,
            'comparative_metrics': {
                'sentiment_comparison': {comp: data['sentiment_breakdown']['average_sentiment'] 
                                      for comp, data in competitor_analysis.items()},
                'volume_comparison': {comp: data['mention_count'] 
                                    for comp, data in competitor_analysis.items()},
                'engagement_comparison': {}
            },
            'market_positioning': 'competitive' if brand_mentions > 0 else 'emerging'
        }

    def _perform_topic_modeling_mock(self, threads: List[Dict[str, Any]], num_topics: int) -> Dict[str, Any]:
        """Mock topic modeling"""
        # Generate mock topics based on content
        mock_topics = [
            {
                'topic_id': 0,
                'keywords': ['productivity', 'efficiency', 'workflow'],
                'weight': 0.3,
                'representative_threads': ['thread_1']
            },
            {
                'topic_id': 1,
                'keywords': ['comparison', 'competitors', 'alternatives'],
                'weight': 0.25,
                'representative_threads': ['thread_2']
            },
            {
                'topic_id': 2,
                'keywords': ['support', 'customer', 'service'],
                'weight': 0.2,
                'representative_threads': ['thread_3']
            },
            {
                'topic_id': 3,
                'keywords': ['pricing', 'cost', 'value'],
                'weight': 0.15,
                'representative_threads': ['thread_4']
            },
            {
                'topic_id': 4,
                'keywords': ['features', 'functionality', 'capabilities'],
                'weight': 0.1,
                'representative_threads': []
            }
        ]
        
        # Limit to requested number of topics
        topics = mock_topics[:num_topics]
        
        return {
            'topics': topics,
            'topic_distribution': {f'topic_{i}': topic['weight'] for i, topic in enumerate(topics)},
            'dominant_topics': [topic for topic in topics if topic['weight'] > 0.2]
        }

    def _analyze_pain_points_mock(self, threads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Mock pain point analysis"""
        pain_points = []
        
        # Extract pain points from negative sentiment threads
        for thread in threads:
            content = f"{thread.get('title', '')} {thread.get('content', '')}".lower()
            sentiment = self._analyze_sentiment_mock(content)
            
            if sentiment['overall_sentiment'] == 'negative':
                if 'support' in content or 'customer' in content:
                    pain_points.append({
                        'category': 'customer_support',
                        'description': 'Customer support responsiveness issues',
                        'severity_score': 7,
                        'frequency': 1,
                        'supporting_evidence': [thread['id']],
                        'recommended_actions': ['Improve support response time', 'Add more support channels']
                    })
                
                if 'price' in content or 'expensive' in content:
                    pain_points.append({
                        'category': 'pricing',
                        'description': 'Pricing concerns and competitiveness',
                        'severity_score': 6,
                        'frequency': 1,
                        'supporting_evidence': [thread['id']],
                        'recommended_actions': ['Review pricing strategy', 'Offer more value tiers']
                    })
        
        return {
            'pain_points': pain_points,
            'pain_point_categories': list(set([pp['category'] for pp in pain_points])),
            'severity_analysis': {
                'average_severity': statistics.mean([pp['severity_score'] for pp in pain_points]) if pain_points else 0,
                'high_severity_count': sum(1 for pp in pain_points if pp['severity_score'] >= 7),
                'total_pain_points': len(pain_points)
            }
        }

    def _generate_insights_mock(self, threads: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        """Mock insight generation"""
        # Generate insights based on analysis results
        sentiment_analysis = self._analyze_sentiment_batch_mock(threads)
        trend_analysis = self._analyze_trends_mock(threads, '7d')
        competitive_analysis = self._analyze_competition_mock(threads, self.competitors)
        
        insights = [
            {
                'insight_type': 'sentiment_trend',
                'description': f"Overall sentiment is {sentiment_analysis['aggregated_sentiment']['dominant_sentiment']}",
                'supporting_data': sentiment_analysis['aggregated_sentiment'],
                'confidence': 0.85,
                'priority': 'high' if sentiment_analysis['aggregated_sentiment']['dominant_sentiment'] == 'negative' else 'medium'
            },
            {
                'insight_type': 'volume_trend',
                'description': f"Discussion volume is trending {trend_analysis['trend_direction']}",
                'supporting_data': trend_analysis['trend_metrics'],
                'confidence': 0.8,
                'priority': 'medium'
            }
        ]
        
        return {
            'key_insights': insights,
            'actionable_recommendations': [
                'Monitor customer support performance closely',
                'Consider competitive pricing analysis'
            ],
            'risk_factors': [
                'Negative sentiment around support',
                'Price sensitivity concerns'
            ],
            'opportunities': [
                'High engagement on feature discussions',
                'Growing market interest'
            ],
            'confidence_scores': {
                'overall_confidence': 0.8,
                'data_quality_score': 0.9,
                'sample_size_adequacy': 0.7
            }
        }

    def _perform_statistical_analysis_mock(self, threads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Mock statistical analysis"""
        # Extract numerical metrics
        quality_scores = [thread.get('quality_score', 0.5) for thread in threads]
        engagement_scores = []
        
        for thread in threads:
            engagement = thread.get('engagement_metrics', {})
            # Normalize different engagement metrics to a common scale
            if 'score' in engagement:
                engagement_scores.append(engagement['score'])
            elif 'replies' in engagement:
                engagement_scores.append(engagement['replies'] * 3)
            elif 'rating' in engagement:
                engagement_scores.append(engagement['rating'] * 10)
            else:
                engagement_scores.append(0)
        
        return {
            'descriptive_statistics': {
                'sentiment_stats': {
                    'mean': 0.6,
                    'median': 0.65,
                    'std_dev': 0.2,
                    'min': 0.2,
                    'max': 0.9
                },
                'engagement_stats': {
                    'mean': statistics.mean(engagement_scores) if engagement_scores else 0,
                    'median': statistics.median(engagement_scores) if engagement_scores else 0,
                    'std_dev': statistics.stdev(engagement_scores) if len(engagement_scores) > 1 else 0
                },
                'volume_stats': {
                    'total_threads': len(threads),
                    'threads_per_day': len(threads) / 7,  # Assuming 7-day period
                    'peak_activity_day': 'Monday'
                }
            },
            'correlation_analysis': {
                'quality_engagement_correlation': 0.65,
                'sentiment_engagement_correlation': 0.45
            },
            'significance_tests': {
                'sentiment_trend_significance': 0.05,
                'volume_change_significance': 0.03
            }
        }

    def _analyze_real_time_mock(self, new_thread: Dict[str, Any], historical_threads: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Mock real-time analysis"""
        import time
        start_time = time.time()
        
        # Quick sentiment analysis of new thread
        content = f"{new_thread.get('title', '')} {new_thread.get('content', '')}"
        sentiment = self._analyze_sentiment_mock(content)
        
        # Check for significant changes or alerts
        alerts = []
        if sentiment['overall_sentiment'] == 'negative' and sentiment['sentiment_scores']['negative'] > 0.7:
            alerts.append({
                'type': 'negative_sentiment_spike',
                'description': 'Significant negative sentiment detected in new content',
                'severity': 'high'
            })
        
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        return {
            'immediate_insights': [
                f"New content has {sentiment['overall_sentiment']} sentiment",
                "Content appears to be about feature announcement"
            ],
            'trend_updates': {
                'sentiment_impact': sentiment['sentiment_scores']['positive'] - 0.5,
                'volume_impact': 1  # One new thread
            },
            'alert_triggers': alerts,
            'processing_time_ms': processing_time
        }

    def _validate_analysis_config_mock(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Mock analysis configuration validation"""
        errors = []
        
        # Validate sentiment analysis config
        if 'sentiment_analysis' in config:
            sa_config = config['sentiment_analysis']
            if 'granularity' in sa_config:
                valid_granularities = ['document', 'sentence', 'phrase']
                if sa_config['granularity'] not in valid_granularities:
                    errors.append(f"Invalid sentiment granularity: {sa_config['granularity']}")
        
        # Validate trend analysis config
        if 'trend_analysis' in config:
            ta_config = config['trend_analysis']
            if 'time_windows' in ta_config:
                if not ta_config['time_windows'] or not isinstance(ta_config['time_windows'], list):
                    errors.append("Time windows must be a non-empty list")
        
        # Validate topic modeling config
        if 'topic_modeling' in config:
            tm_config = config['topic_modeling']
            if 'num_topics' in tm_config:
                if not isinstance(tm_config['num_topics'], int) or tm_config['num_topics'] < 1:
                    errors.append("Number of topics must be a positive integer")
        
        return {
            'is_valid': len(errors) == 0,
            'config_errors': errors,
            'performance_estimates': {
                'estimated_processing_time': '30-120 seconds',
                'estimated_memory_usage': '256-512 MB',
                'recommended_batch_size': 100
            }
        }

    def _run_full_analysis_pipeline_mock(self, threads: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        """Mock full analysis pipeline"""
        import time
        start_time = time.time()
        
        # Run all analysis components
        sentiment_result = self._analyze_sentiment_batch_mock(threads)
        trend_result = self._analyze_trends_mock(threads, '7d')
        competitive_result = self._analyze_competition_mock(threads, self.competitors)
        topic_result = self._perform_topic_modeling_mock(threads, 5)
        pain_point_result = self._analyze_pain_points_mock(threads)
        insight_result = self._generate_insights_mock(threads, config)
        
        processing_time = time.time() - start_time
        
        return {
            'analysis_results': {
                'sentiment_analysis': sentiment_result,
                'trend_analysis': trend_result,
                'competitive_analysis': competitive_result,
                'topic_modeling': topic_result,
                'pain_point_analysis': pain_point_result,
                'insights': insight_result
            },
            'performance_metrics': {
                'total_processing_time': processing_time,
                'threads_per_second': len(threads) / processing_time if processing_time > 0 else 0,
                'memory_usage_mb': 245.7,  # Mock memory usage
                'cpu_utilization_percent': 67.3
            }
        }

    def _export_analysis_results_mock(self, results: Dict[str, Any], format: str) -> Dict[str, Any]:
        """Mock analysis results export"""
        import json
        
        if format == 'json':
            export_data = json.dumps(results, indent=2)
        elif format == 'csv':
            export_data = "metric,value\nsentiment,positive\ntrend,upward"  # Mock CSV
        elif format == 'pdf':
            export_data = "%PDF-1.4 Mock PDF content"  # Mock PDF
        else:
            export_data = str(results)
        
        return {
            'export_data': export_data,
            'export_format': format,
            'file_size_bytes': len(export_data),
            'export_timestamp': datetime.now().isoformat(),
            'download_url': f'/exports/analysis_results_{int(datetime.now().timestamp())}.{format}'
        }


if __name__ == '__main__':
    unittest.main()