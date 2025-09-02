#!/usr/bin/env python3
"""
Test script for Tavily Search integration

This script tests the Tavily Search client functionality
and LangChain tools integration.

Usage:
    python test_tavily_search.py
"""

import os
import sys
from dotenv import load_dotenv

# Add src to path for imports
sys.path.append('src')

def main():
    """Test Tavily Search integration"""
    print("[TESTING] Tavily Search Integration")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Check Tavily API key
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    print(f"[CONFIG] TAVILY_API_KEY: {'[OK] Set' if tavily_api_key and tavily_api_key != 'your-tavily-api-key' else '[ERROR] Not configured'}")
    
    if not tavily_api_key or tavily_api_key == "your-tavily-api-key":
        print("[ERROR] Tavily API key not configured properly")
        print("   Please set TAVILY_API_KEY in your .env file")
        return
    
    print(f"[INFO] API Key: {tavily_api_key[:10]}...")
    print()
    
    # Test Tavily client creation
    print("[TESTING] Creating Tavily Search client...")
    try:
        from src.tavily_client import create_tavily_client, format_search_results
        
        client = create_tavily_client()
        if not client:
            print("[ERROR] Failed to create Tavily client")
            return
        print("[SUCCESS] Tavily client created successfully")
    except ImportError as e:
        print(f"[ERROR] Failed to import Tavily client: {e}")
        return
    except Exception as e:
        print(f"[ERROR] Error creating Tavily client: {e}")
        return
    
    # Test connection
    print("\n[TESTING] Testing Tavily API connection...")
    try:
        response = client.test_connection()
        if response.success:
            print("[SUCCESS] Connection test passed!")
            if response.results:
                print(f"   Found {len(response.results)} test results")
        else:
            print(f"[ERROR] Connection test failed: {response.error}")
            return
    except Exception as e:
        print(f"[ERROR] Connection test error: {e}")
        return
    
    # Test jewelry search functionality
    print("\n[TESTING] Testing jewelry search functionality...")
    test_queries = [
        ("diamond engagement rings", "product"),
        ("jewelry market trends 2024", "market"),
        ("wedding band pricing", "price"),
    ]
    
    for query, search_type in test_queries:
        print(f"\n   Testing: {query} ({search_type})")
        try:
            if search_type == "product":
                response = client.product_research(query)
            elif search_type == "market":
                response = client.jewelry_market_search(query)
            elif search_type == "price":
                response = client.price_comparison(query)
            else:
                response = client.search(query, max_results=3)
            
            if response.success:
                print(f"   [SUCCESS] Found {len(response.results)} results")
                if response.answer:
                    print(f"   [ANSWER] {response.answer[:100]}...")
                if response.search_time:
                    print(f"   [TIMING] {response.search_time:.2f}s")
            else:
                print(f"   [ERROR] Search failed: {response.error}")
        except Exception as e:
            print(f"   [ERROR] Search error: {e}")
    
    # Test LangChain tools integration
    print("\n[TESTING] Testing LangChain tools integration...")
    try:
        from src.langchain_tools import create_langchain_tools
        
        tools = create_langchain_tools(client)
        print(f"[SUCCESS] Created {len(tools)} LangChain tools:")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description[:60]}...")
        
        # Test one tool
        if tools:
            print("\n   Testing jewelry search tool...")
            jewelry_search_tool = next((tool for tool in tools if tool.name == "jewelry_search"), None)
            if jewelry_search_tool:
                result = jewelry_search_tool._run("diamond clarity grades", "product")
                print(f"   [SUCCESS] Tool result: {result[:150]}...")
            else:
                print("   [WARNING] Jewelry search tool not found")
        
    except Exception as e:
        print(f"[ERROR] LangChain tools test failed: {e}")
    
    # Test main application integration
    print("\n[TESTING] Testing main application integration...")
    try:
        from src.app import tavily_client as app_tavily_client, langchain_tools as app_tools
        
        if app_tavily_client:
            print("[SUCCESS] Tavily client integrated in main app")
        else:
            print("[WARNING] Tavily client not initialized in main app")
        
        if app_tools:
            print(f"[SUCCESS] LangChain tools integrated: {len(app_tools)} tools")
        else:
            print("[WARNING] LangChain tools not available in main app")
        
    except Exception as e:
        print(f"[ERROR] Main app integration test failed: {e}")
    
    print("\n[COMPLETE] Tavily Search integration test completed!")
    print("\n[NEXT STEPS] Next Steps:")
    print("   1. Deploy the application with Tavily integration")
    print("   2. Test web search endpoints via API calls")
    print("   3. Test enhanced chat functionality with search capabilities")
    print("   4. Monitor search usage and costs")

if __name__ == "__main__":
    main()