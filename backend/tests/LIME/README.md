# LIME Explainability Testing Suite

## Overview

This test suite uses LIME (Local Interpretable Model-agnostic Explanations) methodology to explain sentiment scores through keyword attribution.

## What is Tested

### Sentiment Keyword Attribution
- **Keyword Extraction**: Identifying sentiment-bearing words in text
- **Contribution Calculation**: Computing each keyword's impact on sentiment
- **Label Classification**: Determining sentiment labels (positive/neutral/negative)
- **HTML Highlighting**: Visualizing keyword contributions in text
- **Explanation Generation**: Creating human-readable explanations

## How LIME Works for Sentiment

LIME explains sentiment predictions by:
1. Identifying keywords that influence sentiment
2. Calculating contribution scores for each keyword
3. Highlighting positive keywords (green) and negative keywords (red)
4. Generating explanations showing which words drove the sentiment score

## Sentiment Keywords

### Positive Keywords (Increase Sentiment)
- love, excellent, amazing, best, perfect
- wonderful, fantastic, good, awesome
- satisfied, happy, great

### Negative Keywords (Decrease Sentiment)
- terrible, awful, horrible, hate, worst
- bad, disappointed, poor, useless
- garbage, frustrated, angry

## Running Tests

### Run all LIME tests:
```bash
cd backend
pytest tests/LIME/ -v
```

### Run with detailed output:
```bash
pytest tests/LIME/ -v -s
```

### Generate HTML report:
```bash
pytest tests/LIME/ --html=tests/LIME/results/lime_report.html --self-contained-html
```

## Test Categories

### 1. Keyword Extraction Tests
- Extract positive sentiment keywords
- Extract negative sentiment keywords
- Handle mixed sentiment content
- Account for keyword frequency

### 2. Sentiment Explanation Tests
- Generate complete explanation structure
- Classify sentiment labels correctly
- Extract top contributing words
- Limit word contributions to top 10

### 3. Explanation Text Tests
- Generate human-readable explanations
- Format positive sentiment explanations
- Format negative sentiment explanations
- Include relevant keywords in text

### 4. HTML Highlighting Tests
- Generate highlighted HTML
- Highlight positive words in green
- Highlight negative words in red
- Preserve original text content

### 5. Edge Case Tests
- Handle empty text
- Handle text with no sentiment keywords
- Handle very long text
- Handle mixed-case keywords
- Ensure reproducibility

## Test Results

Results are automatically saved to:
- `tests/LIME/results/lime_sentiment_results.json`
- HTML reports (if generated)

## Expected Outcomes

All tests should pass, demonstrating:
- ✅ Accurate keyword extraction
- ✅ Correct contribution calculation
- ✅ Proper sentiment label classification
- ✅ Meaningful explanations
- ✅ Functional HTML highlighting
- ✅ Robust edge case handling

## Example Output

### Positive Review Explanation:
```
Sentiment is positive (score: 0.85) due to:
  Positive: love, excellent, amazing
  Negative: (none)

Word Contributions:
  - love: +0.30
  - excellent: +0.30
  - amazing: +0.30
  - best: +0.30
```

### Negative Review Explanation:
```
Sentiment is negative (score: -0.82) due to:
  Positive: (none)
  Negative: terrible, awful, horrible

Word Contributions:
  - terrible: -0.30
  - awful: -0.30
  - horrible: -0.30
  - worst: -0.30
```

### Mixed Sentiment Explanation:
```
Sentiment is neutral (score: 0.15) due to:
  Positive: excellent, great
  Negative: terrible, disappointing

Word Contributions:
  - excellent: +0.30
  - great: +0.30
  - terrible: -0.30
  - disappointing: -0.30
```

## Integration with Production

LIME explanations can be exposed via API:

```python
# Example API endpoint
GET /api/content/{id}/sentiment_explanation/
Response: {
  "sentiment_score": 0.85,
  "sentiment_label": "positive",
  "word_contributions": [...],
  "highlighted_html": "<span style='background-color: green'>love</span> this product",
  "explanation_text": "Sentiment is positive (0.85) due to: Positive: love, excellent"
}
```

## Frontend Visualization

The highlighted HTML can be rendered directly in the UI:
- Positive words: Green background
- Negative words: Red background
- Opacity: 0.3 for readability

## Dependencies

- Base Python libraries (no external LIME library required for this simplified implementation)
- In production, consider using: `lime==0.2.0.1` for advanced LIME functionality

## References

- [LIME Paper](https://arxiv.org/abs/1602.04938)
- [LIME Documentation](https://lime-ml.readthedocs.io/)
- [Interpretable ML Book](https://christophm.github.io/interpretable-ml-book/lime.html)
