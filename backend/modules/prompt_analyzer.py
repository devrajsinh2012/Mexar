"""
MEXAR Core Engine - System Prompt Configuration Module
Analyzes system prompts to extract domain, personality, and constraints.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from utils.groq_client import get_groq_client, GroqClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PromptAnalyzer:
    """
    Analyzes system prompts to extract metadata for agent configuration.
    Uses Groq LLM for intelligent prompt understanding.
    """
    
    def __init__(self, groq_client: Optional[GroqClient] = None):
        """
        Initialize the prompt analyzer.
        
        Args:
            groq_client: Optional pre-configured Groq client
        """
        self.client = groq_client or get_groq_client()
    
    def analyze_prompt(self, system_prompt: str) -> Dict[str, Any]:
        """
        Analyze a system prompt to extract metadata.
        
        Args:
            system_prompt: The user's system prompt for the agent
            
        Returns:
            Dict containing:
                - domain: Primary domain (e.g., 'medical', 'legal', 'cooking')
                - sub_domains: Related sub-domains
                - personality: Agent personality traits
                - constraints: Behavioral constraints
                - suggested_name: Auto-generated agent name
                - domain_keywords: Keywords for domain detection
                - tone: Communication tone
                - capabilities: What the agent can do
        """
        analysis_prompt = """You are a prompt analysis expert. Analyze the following system prompt and extract structured metadata.

SYSTEM PROMPT TO ANALYZE:
\"\"\"
{prompt}
\"\"\"

Respond with a JSON object containing:
{{
    "domain": "primary domain (e.g., medical, legal, cooking, technology, finance, education)",
    "sub_domains": ["list", "of", "related", "sub-domains"],
    "personality": "brief personality description (e.g., friendly, professional, empathetic)",
    "constraints": ["list", "of", "behavioral", "constraints"],
    "suggested_name": "creative agent name based on domain and personality",
    "domain_keywords": ["20", "keywords", "that", "define", "this", "domain"],
    "tone": "communication tone (formal/casual/empathetic/technical)",
    "capabilities": ["list", "of", "what", "agent", "can", "do"]
}}

Be thorough with domain_keywords - these are crucial for query filtering.
Make the suggested_name memorable and relevant.
"""
        
        try:
            response = self.client.analyze_with_system_prompt(
                system_prompt="You are a JSON extraction assistant. Return only valid JSON, no markdown or explanation.",
                user_message=analysis_prompt.format(prompt=system_prompt),
                model="chat",
                json_mode=True
            )
            
            result = json.loads(response)
            
            # Validate and ensure all fields exist
            result = self._ensure_fields(result)
            
            logger.info(f"Prompt analyzed: domain={result['domain']}, name={result['suggested_name']}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return self._create_fallback_analysis(system_prompt)
        except Exception as e:
            logger.error(f"Error analyzing prompt: {e}")
            return self._create_fallback_analysis(system_prompt)
    
    def _ensure_fields(self, result: Dict) -> Dict:
        """Ensure all required fields exist in the result."""
        defaults = {
            "domain": "general",
            "sub_domains": [],
            "personality": "helpful and professional",
            "constraints": [],
            "suggested_name": "MEXAR Agent",
            "domain_keywords": [],
            "tone": "professional",
            "capabilities": []
        }
        
        for key, default in defaults.items():
            if key not in result or result[key] is None:
                result[key] = default
        
        # Ensure domain_keywords has at least 10 items
        if len(result.get("domain_keywords", [])) < 10:
            result["domain_keywords"] = self._expand_keywords(
                result.get("domain_keywords", []),
                result.get("domain", "general")
            )
        
        return result
    
    def _expand_keywords(self, existing: List[str], domain: str) -> List[str]:
        """Expand keywords list if too short."""
        # Common domain-specific keywords
        domain_defaults = {
            "medical": ["health", "patient", "doctor", "treatment", "diagnosis", "symptoms", 
                       "medicine", "hospital", "disease", "therapy", "prescription", "clinic",
                       "medical", "healthcare", "wellness", "condition", "care", "physician",
                       "nurse", "medication"],
            "legal": ["law", "court", "legal", "attorney", "lawyer", "case", "contract",
                     "rights", "litigation", "judge", "verdict", "lawsuit", "compliance",
                     "regulation", "statute", "defendant", "plaintiff", "trial", "evidence",
                     "testimony"],
            "cooking": ["recipe", "cook", "ingredient", "food", "kitchen", "meal", "dish",
                       "flavor", "cuisine", "bake", "chef", "cooking", "taste", "serve",
                       "prepare", "dinner", "lunch", "breakfast", "snack", "dessert"],
            "technology": ["software", "code", "programming", "computer", "system", "data",
                          "network", "security", "cloud", "application", "development",
                          "algorithm", "database", "API", "server", "hardware", "digital",
                          "technology", "tech", "IT"],
            "finance": ["money", "investment", "bank", "finance", "budget", "tax", "stock",
                       "credit", "loan", "savings", "financial", "accounting", "capital",
                       "asset", "portfolio", "market", "trading", "insurance", "wealth",
                       "income"]
        }
        
        # Start with existing keywords
        keywords = list(existing)
        
        # Add domain defaults if available
        if domain.lower() in domain_defaults:
            for kw in domain_defaults[domain.lower()]:
                if kw not in keywords and len(keywords) < 20:
                    keywords.append(kw)
        
        # Add the domain itself if not present
        if domain.lower() not in [k.lower() for k in keywords]:
            keywords.append(domain)
        
        return keywords[:20]
    
    def _create_fallback_analysis(self, system_prompt: str) -> Dict[str, Any]:
        """Create a fallback analysis when LLM fails."""
        # Simple keyword extraction
        words = system_prompt.lower().split()
        
        # Try to detect domain from common words
        domain_indicators = {
            "medical": ["medical", "doctor", "patient", "health", "hospital", "treatment"],
            "legal": ["legal", "law", "attorney", "court", "contract", "rights"],
            "cooking": ["cook", "recipe", "food", "chef", "kitchen", "ingredient"],
            "technology": ["tech", "software", "code", "programming", "computer"],
            "finance": ["finance", "money", "bank", "investment", "budget"]
        }
        
        detected_domain = "general"
        for domain, indicators in domain_indicators.items():
            if any(ind in words for ind in indicators):
                detected_domain = domain
                break
        
        return {
            "domain": detected_domain,
            "sub_domains": [],
            "personality": "helpful assistant",
            "constraints": ["Stay within knowledge base", "Be accurate"],
            "suggested_name": f"MEXAR {detected_domain.title()} Agent",
            "domain_keywords": self._expand_keywords([], detected_domain),
            "tone": "professional",
            "capabilities": ["Answer questions", "Provide information"]
        }
    
    def generate_enhanced_system_prompt(
        self,
        original_prompt: str,
        analysis: Dict[str, Any],
        cag_context: str
    ) -> str:
        """
        Generate an enhanced system prompt with CAG context.
        
        Args:
            original_prompt: User's original system prompt
            analysis: Analysis result from analyze_prompt
            cag_context: Compiled knowledge context
            
        Returns:
            Enhanced system prompt for the agent
        """
        enhanced_prompt = f"""{original_prompt}

---
KNOWLEDGE BASE CONTEXT:
You have been provided with a comprehensive knowledge base containing domain-specific information.
Use this knowledge to answer questions accurately and cite sources when possible.

DOMAIN: {analysis['domain']}
DOMAIN KEYWORDS: {', '.join(analysis['domain_keywords'][:10])}

BEHAVIORAL GUIDELINES:
1. Only answer questions related to your domain and knowledge base
2. If a question is outside your domain, politely decline and explain your specialization
3. Always be {analysis['tone']} in your responses
4. When uncertain, acknowledge limitations rather than guessing

KNOWLEDGE CONTEXT:
{cag_context[:50000]}  # Limit to prevent token overflow
"""
        
        return enhanced_prompt
    
    def get_system_prompt_templates(self) -> List[Dict[str, str]]:
        """
        Return a list of system prompt templates for common domains.
        
        Returns:
            List of template dictionaries with name and content
        """
        return [
            {
                "name": "Medical Assistant",
                "domain": "medical",
                "template": """You are a knowledgeable medical information assistant. 
Your role is to provide accurate health information based on your knowledge base.
You should be empathetic, professional, and always recommend consulting healthcare professionals for personal medical advice.
Never provide diagnoses - only educational information."""
            },
            {
                "name": "Legal Advisor",
                "domain": "legal",
                "template": """You are a legal information assistant providing general legal knowledge.
Be professional and precise in your explanations.
Always clarify that you provide educational information, not legal advice.
Recommend consulting a licensed attorney for specific legal matters."""
            },
            {
                "name": "Recipe Chef",
                "domain": "cooking",
                "template": """You are a friendly culinary assistant with expertise in cooking and recipes.
Help users with cooking techniques, ingredient substitutions, and recipe adaptations.
Be enthusiastic about food and encourage culinary exploration.
Provide clear, step-by-step instructions when explaining recipes."""
            },
            {
                "name": "Tech Support",
                "domain": "technology",
                "template": """You are a technical support specialist helping users with technology questions.
Explain complex concepts in simple terms.
Provide step-by-step troubleshooting guidance.
Be patient and thorough in your explanations."""
            },
            {
                "name": "Financial Guide",
                "domain": "finance",
                "template": """You are a financial information assistant providing educational content about personal finance.
Be clear and professional when explaining financial concepts.
Always remind users that this is educational information, not financial advice.
Recommend consulting certified financial professionals for personal financial decisions."""
            }
        ]


# Factory function
def create_prompt_analyzer() -> PromptAnalyzer:
    """Create a new PromptAnalyzer instance."""
    return PromptAnalyzer()


def get_prompt_templates() -> List[Dict[str, str]]:
    """
    Get system prompt templates without initializing Groq client.
    
    Returns:
        List of template dictionaries with name and content
    """
    return [
        {
            "name": "Medical Assistant",
            "domain": "medical",
            "template": """You are a knowledgeable medical information assistant. 
Your role is to provide accurate health information based on your knowledge base.
You should be empathetic, professional, and always recommend consulting healthcare professionals for personal medical advice.
Never provide diagnoses - only educational information."""
        },
        {
            "name": "Legal Advisor",
            "domain": "legal",
            "template": """You are a legal information assistant providing general legal knowledge.
Be professional and precise in your explanations.
Always clarify that you provide educational information, not legal advice.
Recommend consulting a licensed attorney for specific legal matters."""
        },
        {
            "name": "Recipe Chef",
            "domain": "cooking",
            "template": """You are a friendly culinary assistant with expertise in cooking and recipes.
Help users with cooking techniques, ingredient substitutions, and recipe adaptations.
Be enthusiastic about food and encourage culinary exploration.
Provide clear, step-by-step instructions when explaining recipes."""
        },
        {
            "name": "Tech Support",
            "domain": "technology",
            "template": """You are a technical support specialist helping users with technology questions.
Explain complex concepts in simple terms.
Provide step-by-step troubleshooting guidance.
Be patient and thorough in your explanations."""
        },
        {
            "name": "Financial Guide",
            "domain": "finance",
            "template": """You are a financial information assistant providing educational content about personal finance.
Be clear and professional when explaining financial concepts.
Always remind users that this is educational information, not financial advice.
Recommend consulting certified financial professionals for personal financial decisions."""
        }
    ]
