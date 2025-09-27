import logging
from typing import Dict, List, Optional
from ddgs import DDGS
from bs4 import BeautifulSoup
import httpx
from langchain_openai import ChatOpenAI
import asyncio
from urllib.parse import urlparse

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
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        self.llm = llm or ChatOpenAI()

    async def search_for_links(self, query: str, websites: List[str], max_results_per_site: int = DEFAULT_MAX_RESULTS) -> List[str]:
        """
        Search for links using DuckDuckGo
        """
        all_links = []
        logger.info(f"🔎 Searching for '{query}' across {len(websites)} websites...")
        
        try:
            with DDGS() as ddgs:
                for site in websites:
                    site_domain = self._clean_domain(site)
                    search_term = f"{query} site:{site_domain}"
                    logger.debug(f"  → Querying: {search_term}")
                    
                    try:
                        results = list(ddgs.text(search_term, max_results=max_results_per_site))
                        valid_links = [
                            r.get("href") for r in results 
                            if r.get("href") and r["href"].startswith("http") 
                            and "duckduckgo.com/y.js" not in r["href"]
                        ]
                        all_links.extend(valid_links)
                        logger.debug(f"    ✓ Found {len(valid_links)} valid links for {site_domain}")
                        
                    except Exception as e:
                        logger.warning(f"    ⚠ Error searching {site_domain}: {str(e)}")
                        continue
                        
        except Exception as e:
            logger.error(f"❌ Search operation failed: {str(e)}")
            raise
            
        logger.info(f"✓ Search complete - Found {len(all_links)} total links")
        return all_links
    
    @staticmethod
    def _clean_domain(domain: str) -> str:
        """Clean and format domain name"""
        domain = domain.lower().replace("www.", "").replace("https://", "").replace("http://", "")
        if ".com" not in domain:
            domain = f"{domain}.com"
        return domain

    async def fetch_content(self, url: str) -> Optional[Dict[str, str]]:
        """
        Fetch content with fallbacks
        """
        try:
            # Try web scraping first
            content = await self._scrape_content(url)
            if not content:
                # Fallback 1: Try API if available
                content = await self._try_api_fetch(url)
            if not content:
                # Fallback 2: Use cached content if available
                content = await self._get_cached_content(url)
            return content
        except Exception as e:
            logger.error(f"All content fetch methods failed for {url}: {str(e)}")
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
            '.content'
        ]
        
        for selector in content_selectors:
            if content := soup.select_one(selector):
                return content.get_text(strip=True, separator=' ')
        
        # Fallback to body content
        return soup.body.get_text(strip=True, separator=' ') if soup.body else ''

    async def analyze_content(self, content: Dict[str, str]) -> Optional[Dict]:
        """
        Analyze content using GPT
        """
        try:
            prompt = f"""Analyze the following content from {content['url']}:

Content: {content['content'][:2000]}

Extract and provide:
1. Main topic
2. Key points
3. Sentiment
4. Product/service mentions
5. User pain points or praise
6. Relevance score (0-10)

Provide the analysis in a structured format."""

            response = await self.llm.ainvoke(prompt)
            
            return {
                'url': content['url'],
                'title': content['title'],
                'domain': content['domain'],
                'analysis': response.content,
                'raw_content': content['content'][:500]  # Store truncated raw content
            }
            
        except Exception as e:
            logger.error(f"Error analyzing content: {str(e)}")
            return None

    async def process_batch(self, urls: List[str]) -> List[Dict]:
        """
        Process a batch of URLs: fetch and analyze content
        """
        # Fetch content from all URLs
        content_tasks = [self.fetch_content(url) for url in urls]
        contents = await asyncio.gather(*content_tasks)
        contents = [c for c in contents if c]  # Remove None values
        
        # Analyze content with GPT
        analysis_tasks = [self.analyze_content(content) for content in contents]
        results = await asyncio.gather(*analysis_tasks)
        
        return [r for r in results if r]  # Remove None values

    async def search_and_analyze(self, query: str, websites: List[str], max_results_per_site: int = DEFAULT_MAX_RESULTS) -> List[Dict]:
        """
        Main interface method: Search for content and analyze it
        """
        try:
            # Get links
            links = await self.search_for_links(query, websites, max_results_per_site)
            
            # Process links in batches
            results = await self.process_batch(links)
            
            logger.info(f"✓ Completed analysis of {len(results)} items")
            return results
            
        except Exception as e:
            logger.error(f"Search and analyze operation failed: {str(e)}")
            return []

# Example usage:
async def main():
    search_utils = SearchUtils()
    results = await search_utils.search_and_analyze(
        query="python programming",
        websites=["medium.com", "dev.to"],
        max_results_per_site=2
    )
    print(f"Found and analyzed {len(results)} items")

if __name__ == "__main__":
    asyncio.run(main())