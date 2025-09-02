#!/usr/bin/env python3
"""
Test script for GHL MCP client connection

This script tests the GoHighLevel MCP client functionality
without starting the full FastAPI application.

Usage:
    python test_ghl_mcp.py
"""

import os
import sys
from dotenv import load_dotenv

# Add src to path for imports
sys.path.append('src')

try:
    from src.ghl_mcp_client import create_ghl_client, ContactModel
    print("[SUCCESS] Successfully imported GHL MCP client modules")
except ImportError as e:
    print(f"[ERROR] Failed to import GHL MCP client: {e}")
    sys.exit(1)

def main():
    """Test GHL MCP client functionality"""
    print("[TESTING] GHL MCP Client Connection")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Check required environment variables
    pit_token = os.getenv("GHL_PIT_TOKEN")
    location_id = os.getenv("GHL_LOCATION_ID")
    mcp_enabled = os.getenv("GHL_MCP_ENABLED", "false").lower() == "true"
    
    print(f"[CONFIG] Configuration Check:")
    print(f"   GHL_MCP_ENABLED: {mcp_enabled}")
    print(f"   GHL_PIT_TOKEN: {'[OK] Set' if pit_token and pit_token != 'your-private-integration-token-here' else '[ERROR] Not configured'}")
    print(f"   GHL_LOCATION_ID: {'[OK] Set' if location_id and location_id != 'your-location-id-here' else '[ERROR] Not configured'}")
    print()
    
    if not mcp_enabled:
        print("[WARNING] GHL MCP integration is disabled in environment variables")
        print("   Set GHL_MCP_ENABLED=true to enable integration")
        return
    
    if not pit_token or pit_token == "your-private-integration-token-here":
        print("[ERROR] GHL_PIT_TOKEN not configured")
        print("   Please set your Private Integration Token in .env file")
        return
        
    if not location_id or location_id == "your-location-id-here":
        print("[ERROR] GHL_LOCATION_ID not configured")
        print("   Please set your Location ID in .env file")
        return
    
    # Test client creation
    print("[TESTING] Creating GHL MCP client...")
    try:
        client = create_ghl_client()
        if not client:
            print("[ERROR] Failed to create GHL MCP client")
            return
        print("[SUCCESS] GHL MCP client created successfully")
    except Exception as e:
        print(f"[ERROR] Error creating GHL MCP client: {e}")
        return
    
    # Test connection
    print("\n[TESTING] Testing connection...")
    try:
        response = client.test_connection()
        if response.success:
            print("[SUCCESS] Connection test successful!")
            if response.data:
                location_name = response.data.get("name", "Unknown")
                print(f"   Connected to location: {location_name}")
        else:
            print(f"[ERROR] Connection test failed: {response.error}")
            return
    except Exception as e:
        print(f"[ERROR] Connection test error: {e}")
        return
    
    # Test available tools
    print("\n[INFO] Available MCP Tools:")
    tools = client.get_available_tools()
    for i, tool in enumerate(tools, 1):
        print(f"   {i:2d}. {tool}")
    
    print(f"\n[INFO] Total available tools: {len(tools)}")
    
    # Test basic functionality (non-destructive)
    print("\n[TESTING] Testing basic functionality...")
    
    # Test getting pipeline info
    try:
        pipeline_response = client._make_request("get_pipeline_info", {})
        if pipeline_response.success:
            print(f"[SUCCESS] Pipeline info retrieved successfully")
        else:
            print(f"[WARNING] Could not retrieve pipeline info: {pipeline_response.error}")
    except Exception as e:
        print(f"[WARNING] Error retrieving pipeline info: {e}")
    
    # Test searching contacts
    try:
        search_response = client._make_request("search_contacts", {"query": "", "limit": 1})
        if search_response.success:
            print(f"[SUCCESS] Contact search completed successfully")
        else:
            print(f"[WARNING] Could not search contacts: {search_response.error}")
    except Exception as e:
        print(f"[WARNING] Error searching contacts: {e}")
    
    # Test listing opportunities
    try:
        opps_response = client._make_request("list_opportunities", {"limit": 1})
        if opps_response.success:
            print(f"[SUCCESS] Opportunities listed successfully")
        else:
            print(f"[WARNING] Could not list opportunities: {opps_response.error}")
    except Exception as e:
        print(f"[WARNING] Error listing opportunities: {e}")
    
    print("\n[COMPLETE] GHL MCP Client test completed!")
    print("\n[NEXT STEPS] Next Steps:")
    print("   1. Configure your GHL Private Integration Token with all required scopes")
    print("   2. Set GHL_MCP_ENABLED=true in your .env file")
    print("   3. Start your FastAPI application to use CRM endpoints")
    print("   4. Test the /crm/create-contact and /crm/schedule-appointment endpoints")

if __name__ == "__main__":
    main()