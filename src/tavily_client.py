"""
Tavily Search Client for Brax Jewelers AI Assistant

This module provides web search capabilities using Tavily's search API
for finding current information about jewelry trends, pricing, and market data.
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

import requests
from pydantic import BaseModel, Field

logger = logging.getLogger("brax_jeweler.tavily_search")


class SearchResult(BaseModel):
    """Individual search result model"""
    title: str
    url: str
    content: str
    score: Optional[float] = None
    published_date: Optional[str] = None


class SearchResponse(BaseModel):
    """Tavily search response model"""
    success: bool
    query: str
    results: List[SearchResult] = []
    answer: Optional[str] = None
    follow_up_questions: Optional[List[str]] = []
    search_time: Optional[float] = None
    error: Optional[str] = None


class TavilySearchClient:
    """
    Tavily Search Client for jewelry-related web searches
    
    Provides intelligent web search capabilities specifically optimized
    for jewelry industry queries, market trends, and product information.
    """

    def __init__(self, api_key: str, base_url: str = None):
        """
        Initialize Tavily Search Client
        
        Args:
            api_key: Tavily API key
            base_url: Optional custom API endpoint
        """
        self.api_key = api_key
        self.base_url = base_url or "https://api.tavily.com"
        
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Brax-Jewelers-AI/2.0.0"
        }
        
        # Validate API key format
        if not api_key or not api_key.startswith("tvly-"):
            logger.warning("Tavily API key format appears invalid")

    def search(
        self,
        query: str,
        search_depth: str = "basic",
        include_answer: bool = True,
        include_raw_content: bool = False,
        max_results: int = 5,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> SearchResponse:
        """
        Perform web search using Tavily API
        
        Args:
            query: Search query string
            search_depth: "basic" or "advanced" search depth
            include_answer: Whether to include AI-generated answer
            include_raw_content: Include raw HTML content
            max_results: Maximum number of results to return
            include_domains: List of domains to include
            exclude_domains: List of domains to exclude
            
        Returns:
            SearchResponse with results and metadata
        """
        try:
            search_payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": search_depth,
                "include_answer": include_answer,
                "include_raw_content": include_raw_content,
                "max_results": max_results,
                "format": "json"
            }
            
            # Add domain filters if specified
            if include_domains:
                search_payload["include_domains"] = include_domains
            if exclude_domains:
                search_payload["exclude_domains"] = exclude_domains
            
            logger.info(f"Performing Tavily search for: {query}")
            start_time = datetime.now()
            
            response = requests.post(
                f"{self.base_url}/search",
                json=search_payload,
                headers=self.headers,
                timeout=30
            )
            
            search_time = (datetime.now() - start_time).total_seconds()
            response.raise_for_status()
            
            data = response.json()
            
            # Parse results
            results = []
            for result in data.get("results", []):
                results.append(SearchResult(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    content=result.get("content", ""),
                    score=result.get("score"),
                    published_date=result.get("published_date")
                ))
            
            logger.info(f"Tavily search completed: {len(results)} results in {search_time:.2f}s")
            
            return SearchResponse(
                success=True,
                query=query,
                results=results,
                answer=data.get("answer"),
                follow_up_questions=data.get("follow_up_questions", []),
                search_time=search_time
            )
            
        except requests.exceptions.Timeout:
            error_msg = f"Tavily search timeout for query: {query}"
            logger.error(error_msg)
            return SearchResponse(success=False, query=query, error=error_msg)
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"Tavily API HTTP error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            return SearchResponse(success=False, query=query, error=error_msg)
            
        except Exception as e:
            error_msg = f"Tavily search failed for query '{query}': {str(e)}"
            logger.error(error_msg)
            return SearchResponse(success=False, query=query, error=error_msg)

    def jewelry_market_search(self, query: str) -> SearchResponse:
        """
        Specialized search for jewelry market information
        
        Args:
            query: Market-related query
            
        Returns:
            SearchResponse optimized for jewelry market data
        """
        # Enhance query with jewelry-specific context
        enhanced_query = f"jewelry market {query} trends pricing 2024"
        
        # Focus on reputable jewelry industry domains
        jewelry_domains = [
            "gia.edu",
            "diamonds.pro",
            "nationaljeweler.com",
            "jewelryconnoisseur.com",
            "rapaport.com",
            "jckonline.com"
        ]
        
        return self.search(
            query=enhanced_query,
            search_depth="advanced",
            include_answer=True,
            max_results=8,
            include_domains=jewelry_domains
        )

    def product_research(self, product_type: str, specifications: str = "") -> SearchResponse:
        """
        Research specific jewelry products and specifications
        
        Args:
            product_type: Type of jewelry (ring, necklace, etc.)
            specifications: Additional specifications (diamond cut, metal type, etc.)
            
        Returns:
            SearchResponse with product information
        """
        query = f"{product_type} jewelry {specifications} specifications features quality"
        
        return self.search(
            query=query,
            search_depth="advanced",
            include_answer=True,
            max_results=6
        )

    def price_comparison(self, item: str, budget_range: str = "") -> SearchResponse:
        """
        Search for jewelry pricing information
        
        Args:
            item: Jewelry item to research
            budget_range: Optional budget context
            
        Returns:
            SearchResponse with pricing information
        """
        query = f"{item} jewelry price {budget_range} cost comparison market value"
        
        # Exclude unreliable pricing sources
        exclude_domains = [
            "alibaba.com",
            "aliexpress.com", 
            "wish.com",
            "ebay.com"
        ]
        
        return self.search(
            query=query,
            search_depth="basic",
            include_answer=True,
            max_results=5,
            exclude_domains=exclude_domains
        )

    def trend_analysis(self, category: str = "engagement rings") -> SearchResponse:
        """
        Analyze current jewelry trends
        
        Args:
            category: Jewelry category to analyze
            
        Returns:
            SearchResponse with trend information
        """
        query = f"2024 {category} jewelry trends popular styles fashion designer"
        
        return self.search(
            query=query,
            search_depth="advanced", 
            include_answer=True,
            max_results=7
        )

    def test_connection(self) -> SearchResponse:
        """
        Test Tavily API connection with simple query
        
        Returns:
            SearchResponse indicating connection status
        """
        return self.search(
            query="jewelry industry news",
            max_results=1
        )


def create_tavily_client() -> Optional[TavilySearchClient]:
    """
    Factory function to create Tavily client from environment variables
    
    Returns:
        TavilySearchClient instance if properly configured, None otherwise
    """
    api_key = os.getenv("TAVILY_API_KEY")
    
    if not api_key:
        logger.warning("Tavily Search client not configured - missing TAVILY_API_KEY")
        return None
    
    if api_key == "your-tavily-api-key":
        logger.warning("Tavily API key not updated from placeholder value")
        return None
    
    try:
        client = TavilySearchClient(api_key=api_key)
        logger.info("Tavily Search client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to create Tavily client: {e}")
        return None


def format_search_results(response: SearchResponse, max_length: int = 2000) -> str:
    """
    Format search results for display or LLM consumption
    
    Args:
        response: SearchResponse to format
        max_length: Maximum length of formatted output
        
    Returns:
        Formatted string with search results
    """
    if not response.success:
        return f"Search failed: {response.error}"
    
    output = [f"Search Results for: {response.query}\n"]
    
    if response.answer:
        output.append(f"Summary: {response.answer}\n")
    
    for i, result in enumerate(response.results[:5], 1):
        output.append(f"{i}. {result.title}")
        output.append(f"   {result.url}")
        output.append(f"   {result.content[:200]}...")
        output.append("")
    
    if response.follow_up_questions:
        output.append("Related Questions:")
        for question in response.follow_up_questions[:3]:
            output.append(f"  • {question}")
    
    formatted_text = "\n".join(output)
    
    # Truncate if too long
    if len(formatted_text) > max_length:
        formatted_text = formatted_text[:max_length - 3] + "..."
    
    return formatted_text