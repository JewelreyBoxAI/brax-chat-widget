"""
GoHighLevel MCP (Model Context Protocol) Client

This module provides a client interface for connecting to GoHighLevel's MCP server
to access CRM, calendar, messaging, and opportunity management functionality.

Documentation: https://services.leadconnectorhq.com/mcp/
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

import requests
from pydantic import BaseModel, Field, validator

logger = logging.getLogger("brax_jeweler.ghl_mcp")


class MCPResponse(BaseModel):
    """Standard MCP response model"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tool: Optional[str] = None


class ContactModel(BaseModel):
    """Contact data model for GHL"""
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    tags: Optional[List[str]] = None
    customFields: Optional[Dict[str, Any]] = None


class OpportunityModel(BaseModel):
    """Opportunity data model for GHL"""
    name: str
    contactId: str
    pipelineId: str
    stageId: str
    monetaryValue: Optional[float] = None
    status: Optional[str] = None


class MessageModel(BaseModel):
    """Message data model for GHL conversations"""
    conversationId: str
    message: str
    type: str = "SMS"  # SMS, EMAIL, etc.


class GHLMCPClient:
    """
    GoHighLevel MCP Client for seamless CRM integration
    
    This client provides methods to interact with all 21 available GHL MCP tools
    through a unified interface with proper error handling and logging.
    """

    def __init__(self, pit_token: str, location_id: str, base_url: str = None):
        """
        Initialize GHL MCP Client
        
        Args:
            pit_token: Private Integration Token from GHL
            location_id: Sub-account ID (locationId)
            base_url: Optional custom MCP endpoint URL
        """
        self.pit_token = pit_token
        self.location_id = location_id
        self.base_url = base_url or "https://services.leadconnectorhq.com/mcp/"
        
        self.headers = {
            "Authorization": f"Bearer {pit_token}",
            "locationId": location_id,
            "Content-Type": "application/json",
            "User-Agent": "Brax-Jewelers-AI/2.0.0"
        }
        
        # Validate connection on initialization
        self._validate_connection()

    def _validate_connection(self) -> None:
        """Validate MCP connection and credentials"""
        try:
            # Test connection with a lightweight call
            response = self._make_request("list_calendars", {})
            if not response.success:
                logger.warning(f"GHL MCP connection validation failed: {response.error}")
        except Exception as e:
            logger.error(f"Failed to validate GHL MCP connection: {e}")

    def _make_request(self, tool: str, input_data: Dict[str, Any]) -> MCPResponse:
        """
        Make HTTP request to GHL MCP server
        
        Args:
            tool: MCP tool name
            input_data: Tool input parameters
            
        Returns:
            MCPResponse with success/error status and data
        """
        payload = {
            "tool_name": tool,
            "arguments": input_data
        }
        
        try:
            logger.debug(f"Making GHL MCP request: {tool} with input: {input_data}")
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result_data = response.json()
            
            logger.info(f"GHL MCP {tool} request successful")
            
            # Handle new MCP server response format
            if result_data.get("success"):
                return MCPResponse(
                    success=True,
                    data=result_data.get("result"),
                    tool=tool
                )
            else:
                error_msg = result_data.get("error", "Unknown error")
                return MCPResponse(
                    success=False,
                    error=error_msg,
                    tool=tool
                )
            
        except requests.exceptions.Timeout:
            error_msg = f"GHL MCP request timeout for tool: {tool}"
            logger.error(error_msg)
            return MCPResponse(success=False, error=error_msg, tool=tool)
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"GHL MCP HTTP error for {tool}: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            return MCPResponse(success=False, error=error_msg, tool=tool)
            
        except Exception as e:
            error_msg = f"GHL MCP request failed for {tool}: {str(e)}"
            logger.error(error_msg)
            return MCPResponse(success=False, error=error_msg, tool=tool)

    # ─── CALENDAR METHODS ────────────────────────────────────────────────────

    def get_calendar_events(self, user_id: str = None, group_id: str = None, 
                           calendar_id: str = None, start_date: str = None, 
                           end_date: str = None) -> MCPResponse:
        """Get calendar events using userId, groupId, or calendarId"""
        input_data = {}
        if user_id:
            input_data["userId"] = user_id
        if group_id:
            input_data["groupId"] = group_id
        if calendar_id:
            input_data["calendarId"] = calendar_id
        if start_date:
            input_data["startDate"] = start_date
        if end_date:
            input_data["endDate"] = end_date
            
        return self._make_request("calendars_get-calendar-events", input_data)

    def get_appointment_notes(self, appointment_id: str) -> MCPResponse:
        """Retrieve notes for a specific appointment"""
        return self._make_request("calendars_get-appointment-notes", {
            "appointmentId": appointment_id
        })

    # ─── CONTACT METHODS ─────────────────────────────────────────────────────

    def get_all_tasks(self, contact_id: str) -> MCPResponse:
        """Retrieve all tasks for a contact"""
        return self._make_request("contacts_get-all-tasks", {
            "contactId": contact_id
        })

    def add_tags(self, contact_id: str, tags: List[str]) -> MCPResponse:
        """Add tags to a contact"""
        return self._make_request("contacts_add-tags", {
            "contactId": contact_id,
            "tags": tags
        })

    def remove_tags(self, contact_id: str, tags: List[str]) -> MCPResponse:
        """Remove tags from a contact"""
        return self._make_request("contacts_remove-tags", {
            "contactId": contact_id,
            "tags": tags
        })

    def get_contact(self, contact_id: str) -> MCPResponse:
        """Fetch contact details"""
        return self._make_request("contacts_get-contact", {
            "contactId": contact_id
        })

    def update_contact(self, contact_id: str, contact_data: ContactModel) -> MCPResponse:
        """Update a contact"""
        input_data = {"contactId": contact_id}
        input_data.update(contact_data.dict(exclude_none=True))
        return self._make_request("contacts_update-contact", input_data)

    def upsert_contact(self, contact_data: ContactModel, email: str = None, 
                      phone: str = None) -> MCPResponse:
        """Update or create a contact"""
        input_data = contact_data.dict(exclude_none=True)
        if email:
            input_data["email"] = email
        if phone:
            input_data["phone"] = phone
        return self._make_request("contacts_upsert-contact", input_data)

    def create_contact(self, contact_data: ContactModel) -> MCPResponse:
        """Create a new contact"""
        return self._make_request("contacts_create-contact", 
                                contact_data.dict(exclude_none=True))

    def get_contacts(self, limit: int = 100, offset: int = 0, 
                    query: str = None) -> MCPResponse:
        """Fetch all contacts"""
        input_data = {"limit": limit, "offset": offset}
        if query:
            input_data["query"] = query
        return self._make_request("contacts_get-contacts", input_data)

    # ─── CONVERSATION METHODS ────────────────────────────────────────────────

    def search_conversation(self, query: str = None, contact_id: str = None,
                           limit: int = 20, offset: int = 0) -> MCPResponse:
        """Search/filter/sort conversations"""
        input_data = {"limit": limit, "offset": offset}
        if query:
            input_data["query"] = query
        if contact_id:
            input_data["contactId"] = contact_id
        return self._make_request("conversations_search-conversation", input_data)

    def get_messages(self, conversation_id: str, limit: int = 20, 
                    last_message_id: str = None) -> MCPResponse:
        """Retrieve messages by conversation ID"""
        input_data = {"conversationId": conversation_id, "limit": limit}
        if last_message_id:
            input_data["lastMessageId"] = last_message_id
        return self._make_request("conversations_get-messages", input_data)

    def send_message(self, message_data: MessageModel) -> MCPResponse:
        """Send a message to a conversation thread"""
        return self._make_request("conversations_send-a-new-message", 
                                message_data.dict(exclude_none=True))

    # ─── LOCATION METHODS ────────────────────────────────────────────────────

    def get_location(self, location_id: str = None) -> MCPResponse:
        """Get location details by ID"""
        input_data = {"locationId": location_id or self.location_id}
        return self._make_request("locations_get-location", input_data)

    def get_custom_fields(self, location_id: str = None) -> MCPResponse:
        """Retrieve custom field definitions for a location"""
        input_data = {"locationId": location_id or self.location_id}
        return self._make_request("locations_get-custom-fields", input_data)

    # ─── OPPORTUNITY METHODS ─────────────────────────────────────────────────

    def search_opportunity(self, pipeline_id: str = None, stage_id: str = None,
                          contact_id: str = None, query: str = None,
                          limit: int = 20, offset: int = 0) -> MCPResponse:
        """Search for opportunities by criteria"""
        input_data = {"limit": limit, "offset": offset}
        if pipeline_id:
            input_data["pipelineId"] = pipeline_id
        if stage_id:
            input_data["stageId"] = stage_id
        if contact_id:
            input_data["contactId"] = contact_id
        if query:
            input_data["query"] = query
        return self._make_request("opportunities_search-opportunity", input_data)

    def get_pipelines(self) -> MCPResponse:
        """Fetch all opportunity pipelines"""
        return self._make_request("opportunities_get-pipelines", {})

    def get_opportunity(self, opportunity_id: str) -> MCPResponse:
        """Fetch opportunity details by ID"""
        return self._make_request("opportunities_get-opportunity", {
            "opportunityId": opportunity_id
        })

    def update_opportunity(self, opportunity_id: str, 
                         opportunity_data: OpportunityModel) -> MCPResponse:
        """Update opportunity details"""
        input_data = {"opportunityId": opportunity_id}
        input_data.update(opportunity_data.dict(exclude_none=True))
        return self._make_request("opportunities_update-opportunity", input_data)

    # ─── PAYMENT METHODS ─────────────────────────────────────────────────────

    def get_order_by_id(self, order_id: str) -> MCPResponse:
        """Retrieve payment order details"""
        return self._make_request("payments_get-order-by-id", {
            "orderId": order_id
        })

    def list_transactions(self, limit: int = 20, offset: int = 0,
                         start_date: str = None, end_date: str = None) -> MCPResponse:
        """Fetch paginated list of transactions"""
        input_data = {"limit": limit, "offset": offset}
        if start_date:
            input_data["startDate"] = start_date
        if end_date:
            input_data["endDate"] = end_date
        return self._make_request("payments_list-transactions", input_data)

    # ─── UTILITY METHODS ─────────────────────────────────────────────────────

    def test_connection(self) -> MCPResponse:
        """Test MCP connection and return available tools"""
        return self._make_request("list_calendars", {})

    def get_available_tools(self) -> List[str]:
        """Return list of all available MCP tools"""
        return [
            "get_contact_info",
            "list_opportunities",
            "trigger_webhook",
            "get_pipeline_info",
            "create_note",
            "search_contacts",
            "get_contact_activities",
            "create_opportunity",
            "create_contact_add_notes_schedule_appointment",
            "list_calendars",
            "create_appointment",
            "get_available_slots",
            "create_contact",
            "update_contact",
            "send_sms",
            "list_conversations",
            "get_opportunity",
            "update_opportunity"
        ]


def create_ghl_client() -> Optional[GHLMCPClient]:
    """
    Factory function to create GHL MCP client from environment variables
    
    Returns:
        GHLMCPClient instance if properly configured, None otherwise
    """
    pit_token = os.getenv("GHL_PIT_TOKEN")
    location_id = os.getenv("GHL_LOCATION_ID")
    
    if not pit_token or not location_id:
        logger.warning("GHL MCP client not configured - missing PIT_TOKEN or LOCATION_ID")
        return None
    
    try:
        client = GHLMCPClient(
            pit_token=pit_token,
            location_id=location_id,
            base_url=os.getenv("GHL_MCP_URL", "https://services.leadconnectorhq.com/mcp/")
        )
        logger.info("GHL MCP client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to create GHL MCP client: {e}")
        return None