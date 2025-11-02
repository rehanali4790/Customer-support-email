"""LangGraph workflow for email agent."""
import logging
import os
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END

from .state import AgentState
from .nodes import EmailAgentNodes
logger = logging.getLogger(__name__)


class EmailAgentGraph:
    def __init__(self, config, knowledge_base, conversation_history, email_provider):
        self.config = config
        self.knowledge_base = knowledge_base
        self.conversation_history = conversation_history
        self.email_provider = email_provider
        self.admin_email = os.getenv('ADMIN_EMAIL', os.getenv('APPROVER_EMAIL', 'rehanalikhan4790@gmail.com'))
        self.nodes = EmailAgentNodes(config, knowledge_base, conversation_history)
        self.graph = self._build_graph()
    
    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("classify", self.nodes.classify_email)
        workflow.add_node("retrieve_context", self.nodes.retrieve_context)
        workflow.add_node("generate_response", self.nodes.generate_response)
        workflow.add_node("escalate_to_human", self._escalate_to_human_node)
        workflow.add_node("finalize", self.nodes.finalize_response)
        workflow.add_node("send_email", self._send_email_node)
        
        workflow.set_entry_point("classify")
        workflow.add_edge("classify", "retrieve_context")
        workflow.add_edge("retrieve_context", "generate_response")
        workflow.add_conditional_edges(
            "generate_response", 
            self._route_after_generation, 
            {"escalate": "escalate_to_human", "finalize": "finalize"}
        )
        workflow.add_edge("escalate_to_human", "send_email")
        workflow.add_edge("finalize", "send_email")
        workflow.add_edge("send_email", END)
        return workflow.compile()
    
    def _route_after_generation(self, state):
        """Route based on whether human review is needed."""
        if state.get('human_review_required', False):
            return "escalate"
        return "finalize"
    
    async def _escalate_to_human_node(self, state):
        """Escalate to human - send holding response to customer and notify admin.
        
        This should ONLY be called for:
        - HIGH or CRITICAL urgency emails
        - Complex queries (complexity >= 0.7)
        - Sensitive issues that require human judgment
        """
        logger.info(f"Escalating email {state['email_id']} to human specialist")
        
        try:
            # Extract customer name for personalization
            customer_name = self.nodes._extract_name(state['from_email'])
            
            # Create holding response for customer
            classification = state.get('classification')
            urgency = classification.urgency if classification else 'high'
            
            # Determine timeframe based on urgency
            timeframe = "2 hours" if urgency == 'critical' else "24 hours"
            
            holding_response = f"""Dear {customer_name},

Thank you for contacting us regarding: {state['subject']}

Your inquiry has been escalated to our specialist team due to the nature of your request.

One of our specialists will personally review your case and get back to you within {timeframe}.

If this matter is extremely urgent, please call us directly at our support hotline.

Best regards,

FRIDAY
Support Assistant
support@thalathai.pro"""
            
            state['final_response'] = holding_response
            state['human_approved'] = False  # Indicates it needs human follow-up
            
            # Forward original email to admin
            await self._notify_admin(state)
            
            logger.info(f"Escalation complete for {state['email_id']}")
            
        except Exception as e:
            logger.error(f"Error in escalation: {e}")
            state['error'] = f"Escalation error: {str(e)}"
        
        return state
    
    async def _notify_admin(self, state):
        """Send notification email to admin about escalated case."""
        try:
            from ..email_providers import EmailMessage
            
            classification = state.get('classification')
            
            admin_subject = f"[ESCALATED] {state['subject']}"
            admin_body = f"""ESCALATED CUSTOMER EMAIL
{'='*60}

Email ID: {state['email_id']}
From: {state['from_email']}
Subject: {state['subject']}
Received: {state['received_at']}

Classification:
- Category: {classification.category if classification else 'N/A'}
- Urgency: {classification.urgency if classification else 'N/A'}
- Complexity: {classification.complexity_score if classification else 'N/A'}
- Reasoning: {classification.reasoning if classification else 'N/A'}

{'='*60}
ORIGINAL EMAIL:
{'='*60}
{state['body']}

{'='*60}
AI GENERATED DRAFT (Not Sent):
{'='*60}
{state.get('draft_response', 'N/A')}

{'='*60}
ACTION REQUIRED:
Please respond to this customer directly at: {state['from_email']}
A holding response has been sent informing them a specialist will contact them.
{'='*60}
"""
            
            message = EmailMessage(
                to=[self.admin_email],
                subject=admin_subject,
                body=admin_body,
                from_email=self.email_provider.username if hasattr(self.email_provider, 'username') else 'noreply@example.com'
            )
            
            success = await self.email_provider.send_email(message)
            
            if success:
                logger.info(f"Admin notification sent to {self.admin_email}")
            else:
                logger.error(f"Failed to send admin notification")
                
        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")
    
    async def _send_email_node(self, state):
        logger.info(f"Sending email response for {state['email_id']}")
        logger.info(f"  To: {state['from_email']}")
        logger.info(f"  Subject: Re: {state['subject']}")
        logger.info(f"  Body preview: {state['final_response'][:200]}...")
        
        try:
            from ..email_providers import EmailMessage
            message = EmailMessage(
                to=[state['from_email']],
                subject=f"Re: {state['subject']}",
                body=state['final_response'],
                from_email=state['to_email'][0] if state['to_email'] else "noreply@example.com",
                reply_to=state['to_email'][0] if state['to_email'] else None
            )
            
            logger.info(f"  Calling email_provider.send_email()...")
            success = await self.email_provider.send_email(message)
            logger.info(f"  Send result: {success}")
            state['sent'] = success
            if success:
                logger.info("Email sent successfully")
                self.conversation_history.add_message(conversation_id=state['email_id'], role="user", content=state['body'], metadata={"subject": state['subject'], "from": state['from_email']})
                self.conversation_history.add_message(conversation_id=state['email_id'], role="assistant", content=state['final_response'], metadata={"classification": state['classification'].dict() if state['classification'] else {}})
                self.conversation_history.save_conversation(state['email_id'])
            else:
                logger.error("Failed to send email")
                state['error'] = "Failed to send email"
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            state['error'] = f"Error sending email: {str(e)}"
            state['sent'] = False
        return state
    
    async def process_email(self, email_data):
        initial_state = AgentState(
            email_id=email_data['id'], from_email=email_data['from_email'], to_email=email_data.get('to', []),
            subject=email_data['subject'], body=email_data['body'], received_at=email_data['received_at'],
            classification=None, retrieved_context=[], draft_response=None, human_review_required=False,
            human_approved=None, human_feedback=None, final_response=None, sent=False,
            conversation_history=[], error=None
        )
        try:
            final_state = await self.graph.ainvoke(initial_state)
            return final_state
        except Exception as e:
            logger.error(f"Error processing email: {e}")
            return {**initial_state, "error": str(e)}
