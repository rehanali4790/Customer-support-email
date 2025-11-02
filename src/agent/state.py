"""Agent state definition."""
from typing import TypedDict, List, Optional, Dict, Any
from pydantic import BaseModel


class EmailClassification(BaseModel):
    """Email classification result."""
    category: str
    urgency: str
    complexity_score: float
    requires_human_review: bool
    reasoning: str
    sensitive_topics: List[str] = []


class AgentState(TypedDict):
    """State for the email agent."""
    # Input email
    email_id: str
    from_email: str
    to_email: List[str]
    subject: str
    body: str
    received_at: str
    
    # Classification
    classification: Optional[EmailClassification]
    
    # Retrieved context
    retrieved_context: List[str]
    
    # Generated response
    draft_response: Optional[str]
    
    # Human review
    human_review_required: bool
    human_approved: Optional[bool]
    human_feedback: Optional[str]
    
    # Final output
    final_response: Optional[str]
    sent: bool
    
    # Metadata
    conversation_history: List[Dict[str, Any]]
    error: Optional[str]
