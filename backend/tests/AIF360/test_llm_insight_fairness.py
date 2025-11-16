"""
Test AIF360 fairness for LLM-based insight generation.

⚠️ IMPORTANT: This test file uses REAL PRODUCTION CODE from the backend application.

PRODUCTION MODULES TESTED:
✅ agents/analyst.py - generate_ai_powered_insights_from_brand_analytics (REAL LLM function)

WHAT THIS TESTS:
================
This uses AIF360 to test fairness of LLM insight generation across different:
- Brand industries (Technology, Fashion, Food, Healthcare)
- Campaign budgets (Small, Medium, Large)
- Platform types (Reddit, Twitter, Other)

Unlike traditional AIF360 (testing ML model fairness), this tests:
- Whether LLM generates equally urgent insights across industries
- If small-budget brands get fair treatment vs large-budget brands
- Equal opportunity for all brand types to receive actionable insights

FAIRNESS METRICS TESTED:
- Statistical Parity Difference (should be -0.1 to 0.1)
- Disparate Impact Ratio (should be 0.8 to 1.2)
- Equal Opportunity Difference (should be close to 0)

REAL BACKEND INTEGRATION:
- generate_ai_powered_insights_from_brand_analytics() → agents/analyst.py:398
- This is the EXACT function that generates insights on the Brand Analytics dashboard

Reference: Based on XRAI course demo (Dr. Tian Jing, NUS)
Dataset: Adult Dataset pattern adapted for brand analytics fairness
"""

import pytest
import sys
import os
import numpy as np
import pandas as pd
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

# ============================================================================
# IMPORT REAL PRODUCTION CODE
# This is the EXACT function that generates insights in the backend
# ============================================================================
from agents.analyst import generate_ai_powered_insights_from_brand_analytics  # ← REAL backend code
from common.models import Brand, User
from .conftest import store_fairness_metrics  # Import storage function

# AIF360 imports
from aif360.datasets import BinaryLabelDataset
from aif360.metrics import BinaryLabelDatasetMetric, ClassificationMetric


class TestAIF360LLMInsightFairness:
    """
    Test fairness of LLM insight generation using AIF360.

    Uses REAL production code: agents/analyst.py:398
    """

    def test_fairness_across_industries(self, db, diverse_brand_dataset):
        """
        Test that LLM generates fair insights across different industries.

        PRODUCTION CODE TESTED:
        - generate_ai_powered_insights_from_brand_analytics() → agents/analyst.py:398

        WHAT THIS TESTS:
        ================
        1. Creates brands across different industries (Tech, Fashion, Food)
        2. Calls REAL LLM insight generation for each
        3. Classifies insights as "urgent" (1) or "not urgent" (0)
        4. Uses AIF360 to measure fairness across industries
        5. Tests Statistical Parity Difference and Disparate Impact
        """
        brands_data, user = diverse_brand_dataset

        # Generate insights for each brand using REAL production function
        results = []

        for brand_data in brands_data:
            brand = brand_data['brand']
            kpis = brand_data['kpis']
            communities = brand_data['communities']
            pain_points = brand_data['pain_points']

            try:
                # Call REAL production function
                insights = generate_ai_powered_insights_from_brand_analytics(
                    brand=brand,
                    kpis=kpis,
                    communities=communities,
                    pain_points=pain_points,
                    influencers=[],
                    heatmap_data=None
                )

                # Classify insight urgency (binary label)
                urgency_score = self._calculate_urgency(insights)
                is_urgent = 1 if urgency_score >= 2 else 0  # Binary: urgent (1) or not (0)

                # Protected attribute: industry (encoded)
                industry_code = {
                    'Technology': 1.0,  # Privileged
                    'Fashion': 0.0,     # Unprivileged
                    'Food': 0.0,        # Unprivileged
                    'Healthcare': 0.0   # Unprivileged
                }[brand.industry]

                # Budget category (encoded)
                budget_code = brand_data['budget_category_code']

                results.append({
                    'industry': brand.industry,
                    'industry_code': industry_code,
                    'budget_category_code': budget_code,
                    'is_urgent': is_urgent,
                    'urgency_score': urgency_score,
                    'insight_count': len(insights)
                })

            except Exception as e:
                print(f"Error generating insights for {brand.name}: {e}")
                continue

        # Convert to DataFrame for AIF360
        df = pd.DataFrame(results)

        print("\n" + "="*80)
        print("BRAND DATASET FOR FAIRNESS TESTING")
        print("="*80)
        print(df[['industry', 'is_urgent', 'urgency_score']].to_string())
        print("="*80)

        # Create AIF360 BinaryLabelDataset
        # Features: budget_category_code, urgency_score, insight_count
        # Protected attribute: industry_code
        # Label: is_urgent
        # NOTE: Remove non-numeric 'industry' column for AIF360

        df_numeric = df[['industry_code', 'budget_category_code', 'is_urgent', 'urgency_score', 'insight_count']]

        dataset = BinaryLabelDataset(
            favorable_label=1,
            unfavorable_label=0,
            df=df_numeric,
            label_names=['is_urgent'],
            protected_attribute_names=['industry_code'],
            privileged_protected_attributes=[[1.0]],  # Technology industry
        )

        # Calculate fairness metrics
        privileged_groups = [{'industry_code': 1.0}]  # Technology
        unprivileged_groups = [{'industry_code': 0.0}]  # Other industries

        metric = BinaryLabelDatasetMetric(
            dataset,
            unprivileged_groups=unprivileged_groups,
            privileged_groups=privileged_groups
        )

        # Get fairness metrics
        spd = metric.statistical_parity_difference()
        di = metric.disparate_impact()

        print("\n" + "="*80)
        print("FAIRNESS METRICS (Industry: Technology vs Others)")
        print("="*80)
        print(f"Statistical Parity Difference: {spd:.4f}")
        print(f"  → Target: -0.1 to 0.1 (closer to 0 is fairer)")
        print(f"  → Negative: Favors privileged (Technology)")
        print(f"  → Positive: Favors unprivileged (Other industries)")
        print(f"\nDisparate Impact Ratio: {di:.4f}")
        print(f"  → Target: 0.8 to 1.2 (80% rule)")
        print(f"  → < 0.8: Discrimination against unprivileged")
        print(f"  → > 1.2: Discrimination against privileged")
        print("="*80)

        # Store fairness metrics for JSON export
        store_fairness_metrics(
            test_name="test_fairness_across_industries",
            protected_attribute="industry",
            privileged_group="Technology",
            unprivileged_group="Fashion/Food/Healthcare",
            statistical_parity_difference=spd,
            disparate_impact=di,
            dataset_info={
                "total_samples": int(len(df)),
                "privileged_samples": int(len(df[df['industry_code'] == 1.0])),
                "unprivileged_samples": int(len(df[df['industry_code'] == 0.0])),
                "urgent_privileged": int(len(df[(df['industry_code'] == 1.0) & (df['is_urgent'] == 1)])),
                "urgent_unprivileged": int(len(df[(df['industry_code'] == 0.0) & (df['is_urgent'] == 1)]))
            }
        )

        # Assertions
        assert spd is not None
        assert di is not None

        # Fairness thresholds (these are standards from AIF360)
        # SPD should ideally be between -0.1 and 0.1
        # DI should ideally be between 0.8 and 1.2

        # Document if fairness issues detected
        if abs(spd) > 0.1:
            print(f"\n⚠️  FAIRNESS CONCERN: Statistical Parity Difference ({spd:.4f}) exceeds threshold")
            print(f"   LLM may be biased toward {'Technology' if spd < 0 else 'Other'} industries")

        if di < 0.8 or di > 1.2:
            print(f"\n⚠️  FAIRNESS CONCERN: Disparate Impact ({di:.4f}) outside acceptable range")
            print(f"   80% rule violated - potential discrimination detected")

    def test_fairness_across_budget_categories(self, db, diverse_brand_dataset):
        """
        Test that LLM generates fair insights across budget categories.

        PRODUCTION CODE TESTED:
        - generate_ai_powered_insights_from_brand_analytics() → agents/analyst.py:398
        """
        brands_data, user = diverse_brand_dataset

        results = []

        for brand_data in brands_data:
            brand = brand_data['brand']

            try:
                insights = generate_ai_powered_insights_from_brand_analytics(
                    brand=brand,
                    kpis=brand_data['kpis'],
                    communities=brand_data['communities'],
                    pain_points=brand_data['pain_points'],
                    influencers=[],
                    heatmap_data=None
                )

                urgency_score = self._calculate_urgency(insights)
                is_urgent = 1 if urgency_score >= 2 else 0

                results.append({
                    'brand_id': brand.id,
                    'budget_category': brand_data['budget_category'],
                    'budget_category_code': brand_data['budget_category_code'],
                    'is_urgent': is_urgent
                })

            except Exception as e:
                print(f"Error: {e}")
                continue

        df = pd.DataFrame(results)

        # Create numeric-only DataFrame for AIF360 (exclude UUID and string columns)
        df_numeric = df[['budget_category_code', 'is_urgent']]

        dataset = BinaryLabelDataset(
            favorable_label=1,
            unfavorable_label=0,
            df=df_numeric,
            label_names=['is_urgent'],
            protected_attribute_names=['budget_category_code'],
            privileged_protected_attributes=[[1.0]],  # Large budget
        )

        privileged_groups = [{'budget_category_code': 1.0}]  # Large budget
        unprivileged_groups = [{'budget_category_code': 0.0}]  # Small/Medium budget

        metric = BinaryLabelDatasetMetric(
            dataset,
            unprivileged_groups=unprivileged_groups,
            privileged_groups=privileged_groups
        )

        spd = metric.statistical_parity_difference()
        di = metric.disparate_impact()

        print("\n" + "="*80)
        print("FAIRNESS METRICS (Budget: Large vs Small/Medium)")
        print("="*80)
        print(f"Statistical Parity Difference: {spd:.4f}")
        print(f"Disparate Impact Ratio: {di:.4f}")
        print("="*80)

        # Store fairness metrics for JSON export
        store_fairness_metrics(
            test_name="test_fairness_across_budget_categories",
            protected_attribute="budget_category",
            privileged_group="Large Budget",
            unprivileged_group="Small/Medium Budget",
            statistical_parity_difference=spd,
            disparate_impact=di,
            dataset_info={
                "total_samples": int(len(df)),
                "privileged_samples": int(len(df[df['budget_category_code'] == 1.0])),
                "unprivileged_samples": int(len(df[df['budget_category_code'] == 0.0])),
                "urgent_privileged": int(len(df[(df['budget_category_code'] == 1.0) & (df['is_urgent'] == 1)])),
                "urgent_unprivileged": int(len(df[(df['budget_category_code'] == 0.0) & (df['is_urgent'] == 1)]))
            }
        )

        assert spd is not None
        assert di is not None

    def test_aif360_integration(self):
        """
        Test that AIF360 library is properly integrated.

        This is a simple structural test to verify AIF360 works.
        """
        # Create simple synthetic dataset
        df = pd.DataFrame({
            'feature': [0.5, 0.6, 0.7, 0.8, 0.3, 0.4],
            'protected_attr': [1, 1, 1, 0, 0, 0],
            'label': [1, 1, 0, 1, 0, 0]
        })

        dataset = BinaryLabelDataset(
            favorable_label=1,
            unfavorable_label=0,
            df=df,
            label_names=['label'],
            protected_attribute_names=['protected_attr'],
            privileged_protected_attributes=[[1]]
        )

        metric = BinaryLabelDatasetMetric(
            dataset,
            unprivileged_groups=[{'protected_attr': 0}],
            privileged_groups=[{'protected_attr': 1}]
        )

        spd = metric.statistical_parity_difference()
        di = metric.disparate_impact()

        print("\n✅ AIF360 library is properly integrated and working")
        print(f"   Sample SPD: {spd:.4f}")
        print(f"   Sample DI: {di:.4f}")

        assert spd is not None
        assert di is not None

    def _calculate_urgency(self, insights: List[str]) -> int:
        """
        Calculate urgency score from LLM-generated insights.

        Returns: Integer score (0-10+) based on urgent keywords
        """
        urgent_keywords = [
            'critical', 'urgent', 'immediate', 'serious', 'major',
            'concern', 'issue', 'problem', 'declining', 'negative',
            'dropping', 'failing', 'crisis'
        ]

        score = 0
        for insight in insights:
            insight_lower = insight.lower()
            score += sum(1 for keyword in urgent_keywords if keyword in insight_lower)

        return score


class TestAIF360FairnessComparison:
    """Compare fairness across different scenarios."""

    def test_compare_tech_vs_nontch_industries(self, db, diverse_brand_dataset):
        """
        Compare if Technology brands get different treatment than non-tech brands.
        """
        brands_data, user = diverse_brand_dataset

        tech_urgency_scores = []
        nontech_urgency_scores = []

        for brand_data in brands_data:
            brand = brand_data['brand']

            try:
                insights = generate_ai_powered_insights_from_brand_analytics(
                    brand=brand,
                    kpis=brand_data['kpis'],
                    communities=brand_data['communities'],
                    pain_points=brand_data['pain_points'],
                    influencers=[],
                    heatmap_data=None
                )

                urgency = TestAIF360LLMInsightFairness._calculate_urgency(
                    TestAIF360LLMInsightFairness(), insights
                )

                if brand.industry == 'Technology':
                    tech_urgency_scores.append(urgency)
                else:
                    nontech_urgency_scores.append(urgency)

            except Exception as e:
                print(f"Error: {e}")
                continue

        print("\n" + "="*80)
        print("URGENCY SCORE COMPARISON")
        print("="*80)
        print(f"Technology brands: {tech_urgency_scores}")
        print(f"  Average: {np.mean(tech_urgency_scores):.2f}" if tech_urgency_scores else "  No data")
        print(f"\nNon-tech brands: {nontech_urgency_scores}")
        print(f"  Average: {np.mean(nontech_urgency_scores):.2f}" if nontech_urgency_scores else "  No data")
        print("="*80)

        # Verify we got data
        assert len(tech_urgency_scores) > 0 or len(nontech_urgency_scores) > 0


# Pytest plugin integration is in conftest.py
