import logging
from typing import Dict, List, Optional
from ddgs import DDGS
from bs4 import BeautifulSoup
import httpx
from langchain_openai import ChatOpenAI
import asyncio
from urllib.parse import urlparse
from datetime import datetime
import json
import re

# Configure logging
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
TIMEOUT = 10.0
MAX_CONTENT_LENGTH = 4000
DEFAULT_MAX_RESULTS = 3

class SearchUtils:
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Fix the duplicate llm assignment
        self.llm = llm or ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            max_tokens=2000
        )

    async def search_for_links(self, query: str, websites: List[str], max_results_per_site: int = DEFAULT_MAX_RESULTS) -> List[str]:
        """
        Search for links using DuckDuckGo with improved error handling
        """
        all_links = []
        logger.info(f"🔎 Searching for '{query}' across {len(websites)} websites...")
        
        try:
            # Use asyncio to make DuckDuckGo search async-compatible
            loop = asyncio.get_event_loop()
            
            for site in websites:
                site_domain = self._clean_domain(site)
                search_term = f"{query} site:{site_domain}"
                logger.debug(f"  → Querying: {search_term}")
                
                try:
                    # Run DuckDuckGo search in thread pool since it's synchronous
                    results = await loop.run_in_executor(
                        None, 
                        self._search_duckduckgo, 
                        search_term, 
                        max_results_per_site
                    )
                    
                    valid_links = [
                        r.get("href") for r in results 
                        if r.get("href") and r["href"].startswith("http") 
                        and "duckduckgo.com/y.js" not in r["href"]
                        and site_domain in r["href"]  # Ensure link is from target site
                    ]
                    all_links.extend(valid_links)
                    logger.debug(f"Found {len(valid_links)} valid links for {site_domain}")
                    
                    # Rate limiting to avoid being blocked
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"Error searching {site_domain}: {str(e)}")
                    continue
                        
        except Exception as e:
            logger.error(f"Search operation failed: {str(e)}")
            # Don't raise, return what we have
            
        logger.info(f"Search complete - Found {len(all_links)} total links")
        return all_links
    
    def _search_duckduckgo(self, search_term: str, max_results: int) -> List[Dict]:
        """Synchronous DuckDuckGo search wrapper"""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(search_term, max_results=max_results))
                return results
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            return []
    
    @staticmethod
    def _clean_domain(domain: str) -> str:
        """Clean and format domain name"""
        domain = domain.lower().replace("www.", "").replace("https://", "").replace("http://", "")
        if domain.endswith("/"):
            domain = domain[:-1]
        return domain

    async def fetch_content(self, url: str) -> Optional[Dict[str, str]]:
        """
        Fetch content with fallbacks and better error handling
        """
        try:
            logger.debug(f"Fetching content from: {url}")
            
            # Try web scraping first
            content = await self._scrape_content(url)
            if content:
                logger.debug(f"Successfully scraped content from {url}")
                return content
                
            # Fallback 1: Try API if available
            content = await self._try_api_fetch(url)
            if content:
                logger.debug(f"Successfully fetched via API from {url}")
                return content
                
            # Fallback 2: Create minimal content if all else fails
            logger.warning(f"Could not fetch content from {url}, creating minimal entry")
            return {
                'url': url,
                'title': f"Content from {urlparse(url).netloc}",
                'content': f"Content retrieved from {url}",
                'domain': urlparse(url).netloc,
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"All content fetch methods failed for {url}: {str(e)}")
            return None

    async def _scrape_content(self, url: str) -> Optional[Dict[str, str]]:
        """Enhanced web scraping with better error handling"""
        try:
            async with httpx.AsyncClient(
                headers=self.headers,
                timeout=TIMEOUT,
                follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove script and style elements
                for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    element.decompose()
                
                title = soup.find('title')
                title_text = title.get_text(strip=True) if title else "No Title"
                
                content = self._extract_main_content(soup)
                
                # Truncate content to avoid token limits
                if len(content) > MAX_CONTENT_LENGTH:
                    content = content[:MAX_CONTENT_LENGTH] + "..."
                
                return {
                    'url': url,
                    'title': title_text,
                    'content': content,
                    'domain': urlparse(url).netloc,
                    'scraped_at': datetime.now().isoformat()
                }
                
        except httpx.TimeoutException:
            logger.warning(f"Timeout while scraping {url}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error {e.response.status_code} while scraping {url}")
            return None
        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {str(e)}")
            return None

    async def _try_api_fetch(self, url: str) -> Optional[Dict[str, str]]:
        """Try API-based content fetch (Reddit API, etc.)"""
        try:
            # Reddit API example
            if "reddit.com" in url:
                return await self._fetch_reddit_content(url)
            
            # Add other API integrations here as needed
            return None
            
        except Exception as e:
            logger.warning(f"API fetch failed for {url}: {e}")
            return None

    async def _fetch_reddit_content(self, url: str) -> Optional[Dict[str, str]]:
        """Fetch Reddit content using JSON API"""
        try:
            # Convert Reddit URL to JSON API
            if "/comments/" in url:
                json_url = url.rstrip('/') + ".json"
                
                async with httpx.AsyncClient(headers=self.headers, timeout=TIMEOUT) as client:
                    response = await client.get(json_url)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    if isinstance(data, list) and len(data) > 0:
                        post_data = data[0]["data"]["children"][0]["data"]
                        
                        return {
                            'url': url,
                            'title': post_data.get("title", ""),
                            'content': post_data.get("selftext", "") or post_data.get("title", ""),
                            'domain': "reddit.com",
                            'author': post_data.get("author", ""),
                            'score': post_data.get("score", 0),
                            'num_comments': post_data.get("num_comments", 0),
                            'created_utc': post_data.get("created_utc", 0)
                        }
            
            return None
            
        except Exception as e:
            logger.warning(f"Reddit API fetch failed: {e}")
            return None

    async def _get_cached_content(self, url: str) -> Optional[Dict[str, str]]:
        """Get cached content if available"""
        # TODO: Implement caching logic here if needed
        # For now, return None
        return None
    
    @staticmethod
    def _extract_main_content(soup: BeautifulSoup) -> str:
        """Extract main content from BeautifulSoup object"""
        content_selectors = [
            'article',
            '.post-content',
            '.entry-content',
            'main',
            '#content',
            '.content',
            '.post',
            '.article-body',
            '[role="main"]'
        ]
        
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                return content_element.get_text(strip=True, separator=' ')
        
        # Fallback to body content, but filter out navigation and ads
        if soup.body:
            # Remove common navigation and ad elements
            for unwanted in soup.body(["nav", "aside", ".sidebar", ".advertisement", ".ad"]):
                unwanted.decompose()
            return soup.body.get_text(strip=True, separator=' ')
        
        return ''

    async def analyze_content(self, content: Dict[str, str]) -> Optional[Dict]:
        """
        Analyze content using GPT with improved prompting
        """
        try:
            prompt = f"""Analyze the following web content for brand mentions, product discussions, and user feedback:

URL: {content['url']}
Title: {content['title']}
Content: {content['content'][:1500]}

Extract and provide:
1. Main topic/theme
2. Brand or product mentions
3. User sentiment (positive/negative/neutral)
4. Specific complaints or praise
5. Pain points mentioned
6. Relevance to fashion/clothing (0-10 scale)

Format your response as a structured analysis focusing on actionable insights for brand monitoring."""

            response = await self.llm.ainvoke(prompt)
            
            return {
                'url': content['url'],
                'title': content['title'],
                'domain': content['domain'],
                'analysis': response.content,
                'raw_content': content['content'][:500],  # Store truncated raw content
                'scraped_at': content.get('scraped_at', datetime.now().isoformat())
            }
            
        except Exception as e:
            logger.error(f"Error analyzing content from {content.get('url', 'unknown')}: {str(e)}")
            return None

    async def process_batch(self, urls: List[str]) -> List[Dict]:
        """
        Process a batch of URLs: fetch and analyze content with concurrency control
        """
        if not urls:
            return []
        
        logger.info(f"Processing batch of {len(urls)} URLs")
        
        # Limit concurrency to avoid overwhelming servers
        semaphore = asyncio.Semaphore(3)
        
        async def process_url(url: str) -> Optional[Dict]:
            async with semaphore:
                content = await self.fetch_content(url)
                if content:
                    return await self.analyze_content(content)
                return None
        
        # Process URLs concurrently
        tasks = [process_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None values and exceptions
        valid_results = []
        for result in results:
            if isinstance(result, dict) and result is not None:
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Task failed with exception: {result}")
        
        logger.info(f"Successfully processed {len(valid_results)} out of {len(urls)} URLs")
        return valid_results

    async def search_and_analyze(self, query: str, websites: List[str], max_results_per_site: int = DEFAULT_MAX_RESULTS) -> List[Dict]:
        """
        Main interface method: Search for content and analyze it
        """
        try:
            logger.info(f"Starting search and analysis for query: '{query}'")
            
            # Get links from search
            links = await self.search_for_links(query, websites, max_results_per_site)
            
            if not links:
                logger.warning(f"No links found for query: '{query}'")
                return []
            
            # Process links in batches
            results = await self.process_batch(links)
            
            logger.info(f"✓ Completed search and analysis: found {len(links)} links, analyzed {len(results)} items")
            return results
            
        except Exception as e:
            logger.error(f"Search and analyze operation failed for query '{query}': {str(e)}")
            return []

    async def search_forums_specifically(self, brand_name: str, keywords: List[str], target_platforms: Dict[str, List[str]]) -> Dict[str, List[Dict]]:
        """
        Specialized method for forum-specific searches for scout data collection
        """
        forum_results = {}
        
        for platform, websites in target_platforms.items():
            logger.info(f"Searching {platform} for brand: {brand_name}")
            
            # Create forum-specific search queries
            search_queries = [
                f'"{brand_name}" review forum',
                f'"{brand_name}" problems issues discussion',
                f'"{brand_name}" quality experience',
            ]
            
            # Add keyword-specific searches
            for keyword in keywords[:3]:  # Limit to avoid too many requests
                search_queries.append(f'"{brand_name}" {keyword} forum discussion')
            
            platform_results = []
            
            for query in search_queries[:3]:  # Limit queries per platform
                try:
                    results = await self.search_and_analyze(query, websites, max_results_per_site=2)
                    platform_results.extend(results)
                    
                    # Rate limiting between queries
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"Failed to search {platform} with query '{query}': {e}")
                    continue
            
            forum_results[platform] = platform_results
            
            # Rate limiting between platforms
            await asyncio.sleep(2)
        
        return forum_results

# Example usage and testing
async def test_search_utils():
    """Test function for SearchUtils"""
    search_utils = SearchUtils()
    
    # Test basic search
    results = await search_utils.search_and_analyze(
        query="shirt transparency problems",
        websites=["reddit.com"],
        max_results_per_site=2
    )
    
    print(f"Found and analyzed {len(results)} items")
    for result in results:
        print(f"- {result['title']} ({result['url']})")

if __name__ == "__main__":
    asyncio.run(test_search_utils())