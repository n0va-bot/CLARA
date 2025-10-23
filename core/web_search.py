import requests
from typing import Optional, Dict, List, Any
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from core.headers import get_useragent


class MullvadLetaWrapper:
    """Wrapper for Mullvad Leta privacy-focused search engine."""
    
    BASE_URL = "https://leta.mullvad.net/search"
    
    # Available search engines
    ENGINES = ["brave", "google"]
    
    # Available countries (from the HTML)
    COUNTRIES = [
        "ar", "au", "at", "be", "br", "ca", "cl", "cn", "dk", "fi", 
        "fr", "de", "hk", "in", "id", "it", "jp", "kr", "my", "mx",
        "nl", "nz", "no", "ph", "pl", "pt", "ru", "sa", "za", "es",
        "se", "ch", "tw", "tr", "uk", "us"
    ]
    
    # Available languages
    LANGUAGES = [
        "ar", "bg", "ca", "zh-hans", "zh-hant", "hr", "cs", "da", "nl",
        "en", "et", "fi", "fr", "de", "he", "hu", "is", "it", "jp",
        "ko", "lv", "lt", "nb", "pl", "pt", "ro", "ru", "sr", "sk",
        "sl", "es", "sv", "tr"
    ]
    
    # Time filters
    TIME_FILTERS = ["d", "w", "m", "y"]  # day, week, month, year
    
    def __init__(self, engine: str = "brave"):
        """
        Initialize the Mullvad Leta wrapper.
        
        Args:
            engine: Search engine to use ("brave" or "google")
        """
        if engine not in self.ENGINES:
            raise ValueError(f"Engine must be one of {self.ENGINES}")
        
        self.engine = engine
        self.session = requests.Session()
        
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with user agent."""
        return {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "cache-control": "max-age=0",
            "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": get_useragent()
        }
    
    def search(
        self,
        query: str,
        country: Optional[str] = None,
        language: Optional[str] = None,
        last_updated: Optional[str] = None,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Perform a search on Mullvad Leta.
        
        Args:
            query: Search query string
            country: Country code filter (e.g., "us", "uk")
            language: Language code filter (e.g., "en", "fr")
            last_updated: Time filter ("d", "w", "m", "y")
            page: Page number (default: 1)
            
        Returns:
            Dictionary containing search results and metadata
        """
        if country and country not in self.COUNTRIES:
            raise ValueError(f"Invalid country code. Must be one of {self.COUNTRIES}")
        
        if language and language not in self.LANGUAGES:
            raise ValueError(f"Invalid language code. Must be one of {self.LANGUAGES}")
        
        if last_updated and last_updated not in self.TIME_FILTERS:
            raise ValueError(f"Invalid time filter. Must be one of {self.TIME_FILTERS}")
        
        # Build query parameters
        params = {
            "q": query,
            "engine": self.engine
        }
        
        if country:
            params["country"] = country
        if language:
            params["language"] = language
        if last_updated:
            params["lastUpdated"] = last_updated
        if page > 1:
            params["page"] = str(page)
        
        # Set cookie for engine preference
        cookies = {"engine": self.engine}
        
        # Make request
        response = self.session.get(
            self.BASE_URL,
            params=params,
            headers=self._get_headers(),
            cookies=cookies,
            timeout=10
        )
        response.raise_for_status()
        
        # Parse results
        return self._parse_results(response.text, query, page)
    
    def _parse_results(self, html: str, query: str, page: int) -> Dict[str, Any]:
        """
        Parse HTML response and extract search results.
        
        Args:
            html: HTML response content
            query: Original search query
            page: Current page number
            
        Returns:
            Dictionary containing parsed results
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        results = {
            "query": query,
            "page": page,
            "engine": self.engine,
            "results": [],
            "infobox": None,
            "news": [],
            "cached": False
        }
        
        # Check if cached
        cache_notice = soup.find('p', class_='small')
        if cache_notice and 'cached' in cache_notice.text.lower():
            results["cached"] = True
        
        # Extract regular search results
        articles = soup.find_all('article', class_='svelte-fmlk7p')
        for article in articles:
            result = self._parse_article(article)
            if result:
                results["results"].append(result)
        
        # Extract infobox if present
        infobox_div = soup.find('div', class_='infobox')
        if infobox_div:
            results["infobox"] = self._parse_infobox(infobox_div)
        
        # Extract news results
        news_div = soup.find('div', class_='news')
        if news_div:
            news_articles = news_div.find_all('article')
            for article in news_articles:
                news_item = self._parse_news_article(article)
                if news_item:
                    results["news"].append(news_item)
        
        # Check for next page
        next_button = soup.find('button', {'data-cy': 'next-button'})
        results["has_next_page"] = next_button is not None
        
        return results
    
    def _parse_article(self, article) -> Optional[Dict[str, str]]:
        """Parse a single search result article."""
        try:
            link_tag = article.find('a', href=True)
            if not link_tag:
                return None
            
            title_tag = article.find('h3')
            snippet_tag = article.find('p', class_='result__body')
            cite_tag = article.find('cite')
            
            return {
                "url": link_tag['href'],
                "title": title_tag.get_text(strip=True) if title_tag else "",
                "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                "display_url": cite_tag.get_text(strip=True) if cite_tag else ""
            }
        except Exception as e:
            print(f"Error parsing article: {e}")
            return None
    
    def _parse_infobox(self, infobox_div) -> Dict[str, Any]:
        """Parse infobox information."""
        infobox = {}
        
        title_tag = infobox_div.find('h1')
        if title_tag:
            infobox["title"] = title_tag.get_text(strip=True)
        
        subtitle_tag = infobox_div.find('h2')
        if subtitle_tag:
            infobox["subtitle"] = subtitle_tag.get_text(strip=True)
        
        url_tag = infobox_div.find('a', rel='noreferrer')
        if url_tag:
            infobox["url"] = url_tag['href']
        
        desc_tag = infobox_div.find('p')
        if desc_tag:
            infobox["description"] = desc_tag.get_text(strip=True)
        
        return infobox
    
    def _parse_news_article(self, article) -> Optional[Dict[str, str]]:
        """Parse a news article."""
        try:
            link_tag = article.find('a', href=True)
            if not link_tag:
                return None
            
            title_tag = link_tag.find('h3')
            cite_tag = link_tag.find('cite')
            time_tag = link_tag.find('time')
            
            return {
                "url": link_tag['href'],
                "title": title_tag.get_text(strip=True) if title_tag else "",
                "source": cite_tag.get_text(strip=True) if cite_tag else "",
                "timestamp": time_tag['datetime'] if time_tag and time_tag.has_attr('datetime') else ""
            }
        except Exception as e:
            print(f"Error parsing news article: {e}")
            return None


# Example usage
if __name__ == "__main__":
    # Create wrapper instance
    leta = MullvadLetaWrapper(engine="brave")
    
    # Perform a search
    results = leta.search("python programming", country="us", language="en")
    
    # Display results
    print(f"Query: {results['query']}")
    print(f"Engine: {results['engine']}")
    print(f"Cached: {results['cached']}")
    print(f"\nFound {len(results['results'])} results:\n")
    
    for i, result in enumerate(results['results'][:5], 1):
        print(f"{i}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   {result['snippet'][:100]}...\n")
    
    if results['news']:
        print(f"\nNews ({len(results['news'])} items):")
        for news in results['news'][:3]:
            print(f"- {news['title']}")
            print(f"  {news['source']}\n")