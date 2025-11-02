"""Agent nodes for email processing."""
import logging
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import re
from .state import AgentState, EmailClassification

logger = logging.getLogger(__name__)


class EmailAgentNodes:
    """Nodes for the email agent graph."""
    
    def __init__(self, config: Dict[str, Any], knowledge_base, conversation_history):
        """Initialize agent nodes.
        
        Args:
            config: Configuration dictionary
            knowledge_base: KnowledgeBase instance
            conversation_history: ConversationHistory instance
        """
        self.config = config
        self.knowledge_base = knowledge_base
        self.conversation_history = conversation_history
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=config['agent']['model'],
            temperature=config['agent']['temperature'],
            max_tokens=config['agent']['max_tokens']
        )
    
    def classify_email(self, state: AgentState) -> AgentState:
        """Classify the email."""
        logger.info(f"Classifying email {state['email_id']}")
        
        classification_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an email classifier. Analyze the email and classify it based on:
1. Category: {categories}
2. Urgency: {urgency_levels}
3. Complexity score (0-1): How complex is this query?
4. Sensitive topics: Identify any sensitive topics like {sensitive_topics}

Return a JSON object with: category, urgency, complexity_score, sensitive_topics (list), and reasoning."""),
            ("user", "Subject: {subject}\n\nBody: {body}")
        ])
        
        try:
            response = self.llm.invoke(
                classification_prompt.format_messages(
                    categories=", ".join(self.config['classification']['categories']),
                    urgency_levels=", ".join(self.config['classification']['urgency_levels']),
                    sensitive_topics=", ".join(self.config['human_in_loop']['triggers'][2]['sensitive_topics']),
                    subject=state['subject'],
                    body=state['body']
                )
            )
            
            # Parse response (simplified - in production, use structured output)
            import json
            import re
            
            # Extract JSON from response
            content = response.content
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # Fallback classification
                result = {
                    "category": "general",
                    "urgency": "medium",
                    "complexity_score": 0.5,
                    "sensitive_topics": [],
                    "reasoning": "Unable to parse classification"
                }
            
            # Determine if human review is required
            requires_human = self._check_human_review_required(result)
            
            classification = EmailClassification(
                category=result.get('category', 'general'),
                urgency=result.get('urgency', 'medium'),
                complexity_score=result.get('complexity_score', 0.5),
                requires_human_review=requires_human,
                reasoning=result.get('reasoning', ''),
                sensitive_topics=result.get('sensitive_topics', [])
            )
            
            state['classification'] = classification
            state['human_review_required'] = requires_human
            
            logger.info(f"Classified as {classification.category} with {classification.urgency} urgency")
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            state['error'] = f"Classification failed: {str(e)}"
        
        return state
    
    def _check_human_review_required(self, classification: Dict[str, Any]) -> bool:
        """Check if human review is required based on triggers.
        
        IMPORTANT: Only escalate to human if:
        - Urgency is HIGH or CRITICAL (not low/medium)
        - Complexity score is >= 0.7
        - Contains sensitive topics that can't be auto-resolved
        """
        if not self.config['human_in_loop']['enabled']:
            return False
        
        triggers = self.config['human_in_loop']['triggers']
        
        # Check urgency - only escalate HIGH and CRITICAL
        urgency = classification.get('urgency', '').lower()
        if urgency in ['high', 'critical']:
            logger.info(f"Escalating: urgency is {urgency}")
            return True
        
        # Check complexity - only escalate if very complex (>= 0.7)
        complexity = classification.get('complexity_score', 0)
        if complexity >= triggers[1]['complexity_score']:
            logger.info(f"Escalating: complexity score {complexity} >= {triggers[1]['complexity_score']}")
            return True
        
        # Check sensitive topics ONLY if they're also complex or high urgency
        # Simple questions about sensitive topics can be auto-answered from knowledge base
        sensitive_topics = classification.get('sensitive_topics', [])
        has_sensitive = any(topic in triggers[2]['sensitive_topics'] for topic in sensitive_topics)
        if has_sensitive and (urgency in ['high', 'critical'] or complexity >= 0.5):
            logger.info(f"Escalating: sensitive topics {sensitive_topics} with urgency {urgency}")
            return True
        
        logger.info(f"Not escalating: urgency={urgency}, complexity={complexity}, low priority or simple query")
        return False
    
    def retrieve_context(self, state: AgentState) -> AgentState:
        """Retrieve relevant context from knowledge base."""
        logger.info(f"Retrieving context for email {state['email_id']}")
        
        try:
            # Create query from email
            query = f"{state['subject']} {state['body']}"
            logger.info(f"Search query: {query}")
            
            # Search knowledge base
            top_k = self.config['vector_db']['top_k']
            results = self.knowledge_base.search(query, top_k=top_k)
            
            # Extract context
            context = [doc.page_content for doc in results]
            state['retrieved_context'] = context
            
            logger.info(f"Retrieved {len(context)} context chunks")
            
            # Debug: Log retrieved content
            if context:
                for i, chunk in enumerate(context):
                    logger.info(f"Context chunk {i+1}: {chunk[:200]}...")  # First 200 chars
            else:
                logger.warning("No context retrieved from knowledge base!")
            
        except Exception as e:
            logger.error(f"Context retrieval failed: {e}", exc_info=True)
            state['retrieved_context'] = []
        
        return state
    
    def generate_response(self, state: AgentState) -> AgentState:
        """Generate email response."""
        logger.info(f"Generating response for email {state['email_id']}")
        
        # Extract customer name
        customer_name = self._extract_name(state['from_email'])
        logger.info(f"Customer name extracted: {customer_name}")
        
        response_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are FRIDAY, an AI Support Assistant.

Your Identity:
- Name: FRIDAY
- Role: Support Assistant
- Email: support@thalathai.pro

Knowledge Base Context (USE THIS INFORMATION):
{context}

Email Classification: {category} ({urgency} urgency)

IMPORTANT RULES:
1. Start your response with: "Dear {customer_name},"
2. Use the Knowledge Base Context above to answer the customer's question
3. If the Knowledge Base has specific information (like refund policy, business hours, etc.), USE IT EXACTLY as provided
4. Be specific and detailed - quote policies, procedures, and timeframes from the knowledge base
5. DO NOT include any signature, "Best regards", or closing - it will be added automatically
6. DO NOT use ANY placeholders like [Your Name], [User's Name], etc.
7. DO NOT ask for more information if the knowledge base already has the answer
8. End with your last helpful sentence - no closing remarks
9. Use the EXACT customer name provided: {customer_name}

If the knowledge base doesn't have the information, then you may ask for clarification."""),
            ("user", "Subject: {subject}\nBody: {body}\n\nGenerate response using the knowledge base context:")
        ])
        
        try:
            context = "\n\n".join(state['retrieved_context']) if state['retrieved_context'] else "No specific context available."
            
            response = self.llm.invoke(
                response_prompt.format_messages(
                    context=context,
                    category=state['classification'].category if state['classification'] else 'general',
                    urgency=state['classification'].urgency if state['classification'] else 'medium',
                    customer_name=customer_name,
                    subject=state['subject'],
                    body=state['body']
                )
            )
            
            # Clean and add signature
            cleaned = self._clean_response(response.content)
            signature = "\n\nBest regards,\n\nFRIDAY\nSupport Assistant\nsupport@thalathai.pro"
            state['draft_response'] = cleaned + signature
            logger.info("Response generated with FRIDAY signature")
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}", exc_info=True)
            state['error'] = f"Response generation failed: {str(e)}"
            
            # Fallback response
            fallback = f"""Dear {customer_name},

Thank you for contacting us. We have received your inquiry regarding: {state['subject']}

Our team is reviewing your request and will get back to you within 24 hours with a detailed response.

If this is urgent, please call us directly or reply to this email with additional details.

Best regards,

FRIDAY
Support Assistant
support@thalathai.pro"""
            state['draft_response'] = fallback
            logger.info("Using fallback response due to generation error")
        
        return state
    
    def _extract_name(self, from_email: str) -> str:
        """Extract customer name from email."""
        try:
            # Check if email has display name: "John Doe <john@example.com>"
            if '<' in from_email and '>' in from_email:
                name_part = from_email.split('<')[0].strip()
                # Remove quotes if present
                name_part = name_part.strip('"').strip("'")
                if name_part and len(name_part) > 1 and not name_part.isdigit():
                    logger.info(f"Extracted name from display: {name_part}")
                    return name_part
            
            # Extract from email username (before @)
            email_clean = from_email.replace('<', '').replace('>', '').strip()
            username = email_clean.split('@')[0]
            
            # Clean up common patterns
            username = username.replace('.', ' ').replace('_', ' ').replace('-', ' ')
            
            # Capitalize each word
            if username and not username.isdigit():
                name = username.title()
                # If it looks like a name (2-3 words, no numbers)
                words = name.split()
                if 1 <= len(words) <= 3 and not any(char.isdigit() for char in name):
                    logger.info(f"Extracted name from username: {name}")
                    return name
        except Exception as e:
            logger.error(f"Error extracting name: {e}")
        
        # Default greeting
        return "Valued Customer"
    
    def _clean_response(self, response: str) -> str:
        """Clean response from placeholders and unwanted patterns."""
        # Remove common placeholders
        placeholders = [
            r'\[Your Name\]',
            r'\[User\'s Name\]',
            r'\[Customer\'s Name\]',
            r'\[Your Position\]',
            r'\[Your Contact Information\]',
            r'\[Company Name\]',
            r'Best regards,.*?(?=\n\n|$)',
            r'Sincerely,.*?(?=\n\n|$)',
            r'Kind regards,.*?(?=\n\n|$)',
        ]
        
        cleaned = response
        for pattern in placeholders:
            cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove extra whitespace
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
    
    def finalize_response(self, state: AgentState) -> AgentState:
        """Finalize the response (auto-approve if no human review needed)."""
        if not state['human_review_required']:
            state['final_response'] = state['draft_response']
            state['human_approved'] = True
            logger.info("Response auto-approved (no human review required)")
        
        return state
