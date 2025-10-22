"""
Default Sources Configuration

This module defines default sources that are available for all brands.
Users can select from these defaults or add custom sources.
"""

DEFAULT_SOURCES = {
    "reddit": [
        {
            "id": "default_reddit_1",
            "name": "r/malefashionadvice",
            "platform": "reddit",
            "url": "https://reddit.com/r/malefashionadvice",
            "description": "Men's fashion advice and discussions",
            "category": "fashion",
            "member_count": 1200000,
            "is_default": True
        },
        {
            "id": "default_reddit_2",
            "name": "r/streetwear",
            "platform": "reddit",
            "url": "https://reddit.com/r/streetwear",
            "description": "Streetwear fashion community",
            "category": "fashion",
            "member_count": 800000,
            "is_default": True
        },
        {
            "id": "default_reddit_3",
            "name": "r/BuyItForLife",
            "platform": "reddit",
            "url": "https://reddit.com/r/BuyItForLife",
            "description": "Durable product recommendations",
            "category": "reviews",
            "member_count": 900000,
            "is_default": True
        },
        {
            "id": "default_reddit_4",
            "name": "r/reviews",
            "platform": "reddit",
            "url": "https://reddit.com/r/reviews",
            "description": "Product reviews and discussions",
            "category": "reviews",
            "member_count": 250000,
            "is_default": True
        },
        {
            "id": "default_reddit_5",
            "name": "r/techwearclothing",
            "platform": "reddit",
            "url": "https://reddit.com/r/techwearclothing",
            "description": "Technical clothing and gear",
            "category": "fashion",
            "member_count": 150000,
            "is_default": True
        },
        {
            "id": "default_reddit_6",
            "name": "r/sneakers",
            "platform": "reddit",
            "url": "https://reddit.com/r/sneakers",
            "description": "Sneaker enthusiasts community",
            "category": "fashion",
            "member_count": 2500000,
            "is_default": True
        },
        {
            "id": "default_reddit_7",
            "name": "r/ProductReviews",
            "platform": "reddit",
            "url": "https://reddit.com/r/ProductReviews",
            "description": "General product reviews",
            "category": "reviews",
            "member_count": 50000,
            "is_default": True
        },
        {
            "id": "default_reddit_8",
            "name": "r/HomeImprovement",
            "platform": "reddit",
            "url": "https://reddit.com/r/HomeImprovement",
            "description": "Home improvement discussions",
            "category": "home",
            "member_count": 3000000,
            "is_default": True
        },
        {
            "id": "default_reddit_9",
            "name": "r/HVAC",
            "platform": "reddit",
            "url": "https://reddit.com/r/HVAC",
            "description": "HVAC professionals and enthusiasts",
            "category": "home",
            "member_count": 150000,
            "is_default": True
        },
        {
            "id": "default_reddit_10",
            "name": "r/gadgets",
            "platform": "reddit",
            "url": "https://reddit.com/r/gadgets",
            "description": "Technology and gadget discussions",
            "category": "technology",
            "member_count": 20000000,
            "is_default": True
        }
    ],
    "forums": [
        {
            "id": "default_forum_1",
            "name": "Stack Exchange",
            "platform": "forum",
            "url": "https://stackexchange.com",
            "description": "Q&A community network",
            "category": "general",
            "member_count": 10000000,
            "is_default": True
        },
        {
            "id": "default_forum_2",
            "name": "Quora",
            "platform": "forum",
            "url": "https://quora.com",
            "description": "Question and answer platform",
            "category": "general",
            "member_count": 300000000,
            "is_default": True
        },
        {
            "id": "default_forum_3",
            "name": "TechPowerUp Forums",
            "platform": "forum",
            "url": "https://techpowerup.com",
            "description": "Technology hardware discussions",
            "category": "technology",
            "member_count": 500000,
            "is_default": True
        },
        {
            "id": "default_forum_4",
            "name": "AnandTech Forums",
            "platform": "forum",
            "url": "https://anandtech.com",
            "description": "PC hardware and technology",
            "category": "technology",
            "member_count": 750000,
            "is_default": True
        }
    ]
}


def get_all_default_sources():
    """Get all default sources as a flat list."""
    all_sources = []
    for platform_sources in DEFAULT_SOURCES.values():
        all_sources.extend(platform_sources)
    return all_sources


def get_default_sources_by_platform(platform):
    """Get default sources for a specific platform."""
    return DEFAULT_SOURCES.get(platform, [])


def get_default_sources_by_category(category):
    """Get default sources for a specific category."""
    all_sources = get_all_default_sources()
    return [s for s in all_sources if s.get('category') == category]


def get_default_source_by_id(source_id):
    """Get a specific default source by ID."""
    all_sources = get_all_default_sources()
    for source in all_sources:
        if source['id'] == source_id:
            return source
    return None


def get_reddit_subreddit_name(source_name):
    """
    Extract subreddit name from various formats.

    Examples:
        'r/malefashionadvice' -> 'malefashionadvice'
        'malefashionadvice' -> 'malefashionadvice'
        'https://reddit.com/r/streetwear' -> 'streetwear'
    """
    import re

    # Try URL format
    url_match = re.search(r'reddit\.com/r/(\w+)', source_name)
    if url_match:
        return url_match.group(1)

    # Try r/ format
    if source_name.startswith('r/'):
        return source_name[2:]

    # Already clean
    return source_name
