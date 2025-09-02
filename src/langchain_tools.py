"""
LangChain Tools Integration for Brax Jewelers AI Assistant

This module provides LangChain tools that integrate with Tavily Search
and other external services to enhance the AI agent's capabilities.
"""

import logging
from typing import Optional, Type, Dict, Any, List

from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field

from .tavily_client import TavilySearchClient, format_search_results

logger = logging.getLogger("brax_jeweler.langchain_tools")


class JewelrySearchInput(BaseModel):
    """Input schema for jewelry search tool"""
    query: str = Field(description="Search query about jewelry, diamonds, or market trends")
    search_type: str = Field(
        default="general",
        description="Type of search: 'general', 'market', 'product', 'price', or 'trends'"
    )


class JewelrySearchTool(BaseTool):
    """LangChain tool for searching jewelry-related information using Tavily"""
    
    name: str = "jewelry_search"
    description: str = """Search for current information about jewelry, diamonds, market trends, and pricing.
    Use this tool when you need up-to-date information about:
    - Current jewelry trends and styles
    - Diamond and gemstone market pricing
    - New jewelry technologies and techniques
    - Industry news and developments
    - Comparison of jewelry products
    
    Search types:
    - 'general': General jewelry information search
    - 'market': Market trends and pricing information
    - 'product': Specific product research and specifications
    - 'price': Pricing comparisons and value information
    - 'trends': Latest fashion and style trends
    """
    
    args_schema: Type[BaseModel] = JewelrySearchInput
    tavily_client: Optional[TavilySearchClient] = None

    def __init__(self, tavily_client: Optional[TavilySearchClient] = None):
        super().__init__()
        self.tavily_client = tavily_client

    def _run(
        self,
        query: str,
        search_type: str = "general",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute the jewelry search tool"""
        
        if not self.tavily_client:
            return "Web search is currently unavailable. Please try again later or contact support."
        
        try:
            logger.info(f"Performing jewelry search: {query} (type: {search_type})")
            
            # Route to appropriate search method
            if search_type == "market":
                response = self.tavily_client.jewelry_market_search(query)
            elif search_type == "product":
                response = self.tavily_client.product_research(query)
            elif search_type == "price":
                response = self.tavily_client.price_comparison(query)
            elif search_type == "trends":
                response = self.tavily_client.trend_analysis(query)
            else:
                response = self.tavily_client.search(
                    query=query,
                    max_results=5,
                    include_answer=True
                )
            
            if response.success:
                formatted_results = format_search_results(response, max_length=1500)
                logger.info(f"Jewelry search completed successfully: {len(response.results)} results")
                return formatted_results
            else:
                error_msg = f"Search failed: {response.error}"
                logger.warning(error_msg)
                return f"I'm sorry, I couldn't find current information about {query}. Please try rephrasing your question or ask about something else."
                
        except Exception as e:
            error_msg = f"Error during jewelry search: {str(e)}"
            logger.error(error_msg)
            return "I encountered an issue while searching for that information. Please try again or ask about something else."


class MarketTrendsInput(BaseModel):
    """Input schema for market trends tool"""
    category: str = Field(
        default="engagement rings",
        description="Jewelry category to analyze trends for (e.g., 'engagement rings', 'necklaces', 'watches')"
    )


class MarketTrendsTool(BaseTool):
    """LangChain tool for getting current jewelry market trends"""
    
    name: str = "jewelry_market_trends"
    description: str = """Get current jewelry market trends and popular styles for specific categories.
    Use this tool when customers ask about:
    - What's trending in engagement rings, wedding bands, or other jewelry
    - Popular styles and designs for the current season
    - Fashion jewelry trends
    - What celebrities or influencers are wearing
    - Upcoming jewelry trends for the year
    """
    
    args_schema: Type[BaseModel] = MarketTrendsInput
    tavily_client: Optional[TavilySearchClient] = None

    def __init__(self, tavily_client: Optional[TavilySearchClient] = None):
        super().__init__()
        self.tavily_client = tavily_client

    def _run(
        self,
        category: str = "engagement rings",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute the market trends tool"""
        
        if not self.tavily_client:
            return "Trend information is currently unavailable. I can still help you with general jewelry advice based on my training."
        
        try:
            logger.info(f"Fetching market trends for: {category}")
            
            response = self.tavily_client.trend_analysis(category)
            
            if response.success:
                # Format trends information specifically
                trends_info = []
                
                if response.answer:
                    trends_info.append(f"Current Trends for {category.title()}:")
                    trends_info.append(response.answer)
                    trends_info.append("")
                
                if response.results:
                    trends_info.append("Latest Industry Insights:")
                    for i, result in enumerate(response.results[:3], 1):
                        trends_info.append(f"{i}. {result.title}")
                        trends_info.append(f"   {result.content[:150]}...")
                        trends_info.append("")
                
                if response.follow_up_questions:
                    trends_info.append("Related Questions You Might Ask:")
                    for question in response.follow_up_questions[:2]:
                        trends_info.append(f"  • {question}")
                
                formatted_trends = "\n".join(trends_info)
                logger.info(f"Market trends retrieved successfully for {category}")
                return formatted_trends
            else:
                logger.warning(f"Trends search failed: {response.error}")
                return f"I'm having trouble accessing current trend data for {category}. However, I can share general knowledge about popular jewelry styles if you'd like."
                
        except Exception as e:
            error_msg = f"Error fetching market trends: {str(e)}"
            logger.error(error_msg)
            return f"I can't access current trend information right now, but I'd be happy to discuss classic and timeless {category} styles that are always popular."


class PricingResearchInput(BaseModel):
    """Input schema for pricing research tool"""
    item: str = Field(description="Jewelry item to research pricing for")
    specifications: str = Field(
        default="",
        description="Additional specifications like carat weight, metal type, brand, etc."
    )


class PricingResearchTool(BaseTool):
    """LangChain tool for researching jewelry pricing"""
    
    name: str = "jewelry_pricing_research"
    description: str = """Research current market pricing for jewelry items.
    Use this tool when customers ask about:
    - How much does a specific type of jewelry cost
    - Price ranges for different quality levels
    - Market value of jewelry items
    - Cost comparisons between different options
    - Investment value of jewelry pieces
    
    Note: Always remind customers that prices vary significantly based on quality,
    brand, and other factors, and encourage them to visit for accurate pricing.
    """
    
    args_schema: Type[BaseModel] = PricingResearchInput
    tavily_client: Optional[TavilySearchClient] = None

    def __init__(self, tavily_client: Optional[TavilySearchClient] = None):
        super().__init__()
        self.tavily_client = tavily_client

    def _run(
        self,
        item: str,
        specifications: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute the pricing research tool"""
        
        if not self.tavily_client:
            return f"Current pricing information for {item} is not available right now. I recommend visiting our showroom or calling (949) 250-9949 for accurate, personalized pricing based on your specific requirements."
        
        try:
            logger.info(f"Researching pricing for: {item} {specifications}")
            
            query = f"{item} {specifications}".strip()
            response = self.tavily_client.price_comparison(query)
            
            if response.success:
                pricing_info = []
                
                pricing_info.append(f"Market Pricing Information for {item.title()}:")
                
                if response.answer:
                    pricing_info.append(response.answer)
                    pricing_info.append("")
                
                if response.results:
                    pricing_info.append("Recent Market Data:")
                    for result in response.results[:3]:
                        pricing_info.append(f"• {result.title}")
                        pricing_info.append(f"  {result.content[:200]}...")
                        pricing_info.append("")
                
                pricing_info.append("Important Note:")
                pricing_info.append("Jewelry pricing varies significantly based on quality, craftsmanship, brand, and current market conditions. These are general market ranges only.")
                pricing_info.append("")
                pricing_info.append("For accurate pricing on specific pieces, I recommend:")
                pricing_info.append("• Visiting our Laguna Niguel or Newport Beach showroom")
                pricing_info.append("• Scheduling a consultation to discuss your needs")
                pricing_info.append("• Calling (949) 250-9949 to speak with our experts")
                
                formatted_pricing = "\n".join(pricing_info)
                logger.info(f"Pricing research completed for {item}")
                return formatted_pricing
            else:
                logger.warning(f"Pricing search failed: {response.error}")
                return f"I'm unable to access current pricing data for {item} right now. For the most accurate and up-to-date pricing information, please visit our showroom or call (949) 250-9949. Our jewelry experts can provide personalized quotes based on your specific requirements."
                
        except Exception as e:
            error_msg = f"Error during pricing research: {str(e)}"
            logger.error(error_msg)
            return f"I can't access current pricing information at the moment. For accurate pricing on {item}, please contact our showroom directly at (949) 250-9949 or visit us for a personal consultation."


def create_langchain_tools(tavily_client: Optional[TavilySearchClient] = None) -> List[BaseTool]:
    """
    Create list of LangChain tools for the Brax Jewelers AI agent
    
    Args:
        tavily_client: Optional Tavily search client
        
    Returns:
        List of configured LangChain tools
    """
    tools = []
    
    if tavily_client:
        # Add search-enabled tools
        tools.extend([
            JewelrySearchTool(tavily_client=tavily_client),
            MarketTrendsTool(tavily_client=tavily_client),
            PricingResearchTool(tavily_client=tavily_client)
        ])
        logger.info("Created LangChain tools with Tavily Search integration")
    else:
        logger.info("Tavily client not available - search tools disabled")
    
    return tools