"""
MEXAR Core Engine - Explainability Generator Module
Packages reasoning traces for UI display.
"""

import logging
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExplainabilityGenerator:
    """
    Generates structured explainability data for the UI.
    Prepares reasoning traces and source citations.
    """
    
    def __init__(self):
        """Initialize the explainability generator."""
        pass
    
    def generate(
        self,
        reasoning_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive explainability data.
        
        Args:
            reasoning_result: Output from ReasoningEngine.reason()
            
        Returns:
            Structured explainability data for UI
        """
        explainability = reasoning_result.get("explainability", {})
        
        # Enhance the existing explainability data
        enhanced = {
            "summary": self._generate_summary(reasoning_result),
            "inputs": self._format_inputs(explainability.get("inputs", {})),
            "retrieval": self._format_retrieval(explainability.get("retrieval", {})),
            "reasoning_steps": self._format_reasoning_steps(
                explainability.get("reasoning_trace", [])
            ),
            "confidence": self._format_confidence(
                explainability.get("confidence_breakdown", {})
            ),
            "sources": self._format_sources(explainability.get("sources_cited", []))
        }
        
        return enhanced
    
    def _generate_summary(self, reasoning_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a human-readable summary."""
        confidence = reasoning_result.get("confidence", 0)
        in_domain = reasoning_result.get("in_domain", True)
        sources = reasoning_result.get("sources", [])
        
        if not in_domain:
            status = "rejected"
            message = "Query was outside the agent's domain expertise"
            color = "red"
        elif confidence >= 0.8:
            status = "high_confidence"
            message = "Answer is well-supported by the knowledge base"
            color = "green"
        elif confidence >= 0.5:
            status = "moderate_confidence"
            message = "Answer is partially supported, some uncertainty exists"
            color = "yellow"
        else:
            status = "low_confidence"
            message = "Limited support in knowledge base, treat with caution"
            color = "orange"
        
        return {
            "status": status,
            "message": message,
            "color": color,
            "quick_stats": {
                "sources_found": len(sources),
                "confidence_percent": f"{confidence * 100:.0f}%"
            }
        }
    
    def _format_inputs(self, inputs: Dict) -> Dict[str, Any]:
        """Format input information."""
        return {
            "query": inputs.get("original_query", ""),
            "has_multimodal": inputs.get("has_multimodal", False),
            "multimodal_type": self._detect_multimodal_type(inputs),
            "multimodal_preview": inputs.get("multimodal_preview", "")
        }
    
    def _detect_multimodal_type(self, inputs: Dict) -> Optional[str]:
        """Detect the type of multimodal input."""
        preview = inputs.get("multimodal_preview", "")
        if not preview:
            return None
        
        if "[AUDIO" in preview:
            return "audio"
        elif "[IMAGE" in preview:
            return "image"
        elif "[VIDEO" in preview:
            return "video"
        return "text"
    
    def _format_retrieval(self, retrieval: Dict) -> Dict[str, Any]:
        """Format retrieval information."""
        return {
            "chunks_retrieved": retrieval.get("chunks_retrieved", 0),
            "previews": retrieval.get("chunk_previews", [])
        }
    
    def _format_reasoning_steps(self, trace: List[Dict]) -> List[Dict[str, Any]]:
        """Format reasoning trace into displayable steps."""
        steps = []
        
        for item in trace:
            step = {
                "step_number": item.get("step", len(steps) + 1),
                "action": item.get("action", "unknown"),
                "action_display": self._get_action_display(item.get("action", "unknown")),
                "explanation": item.get("explanation", ""),
                "icon": self._get_action_icon(item.get("action", "unknown"))
            }
            steps.append(step)
        
        return steps
    
    def _get_action_display(self, action: str) -> str:
        """Get display-friendly action name."""
        action_map = {
            "domain_check": "Domain Relevance Check",
            "vector_retrieval": "Semantic Search",
            "llm_generation": "Answer Generation",
            "guardrail_rejection": "Domain Guardrail"
        }
        return action_map.get(action, action.replace("_", " ").title())
    
    def _get_action_icon(self, action: str) -> str:
        """Get icon for reasoning action."""
        icon_map = {
            "domain_check": "✅",
            "vector_retrieval": "🔍",
            "llm_generation": "💬",
            "guardrail_rejection": "🚫"
        }
        return icon_map.get(action, "▶️")
    
    def _format_confidence(self, breakdown: Dict) -> Dict[str, Any]:
        """Format confidence breakdown for display."""
        overall = breakdown.get("overall", 0)
        
        # Determine confidence level
        if overall >= 0.8:
            level = "high"
            color = "#22c55e"  # Green
            message = "High confidence answer"
        elif overall >= 0.5:
            level = "moderate"
            color = "#eab308"  # Yellow
            message = "Moderate confidence"
        else:
            level = "low"
            color = "#f97316"  # Orange
            message = "Low confidence - verify independently"
        
        return {
            "overall_score": overall,
            "overall_percent": f"{overall * 100:.0f}%",
            "level": level,
            "color": color,
            "message": message,
            "factors": [
                {
                    "name": "Domain Relevance",
                    "score": breakdown.get("domain_relevance", 0),
                    "percent": f"{breakdown.get('domain_relevance', 0) * 100:.0f}%",
                    "description": "How well the query matches the agent's domain"
                },
                {
                    "name": "Retrieval Quality",
                    "score": breakdown.get("retrieval_quality", 0),
                    "percent": f"{breakdown.get('retrieval_quality', 0) * 100:.0f}%",
                    "description": "Quality of retrieved context chunks"
                }
            ]
        }
    
    def _format_sources(self, sources: List[str]) -> List[Dict[str, str]]:
        """Format source citations."""
        formatted = []
        
        for source in sources:
            source_type = self._detect_source_type(source)
            formatted.append({
                "citation": source,
                "type": source_type,
                "icon": self._get_source_icon(source_type)
            })
        
        return formatted
    
    def _detect_source_type(self, source: str) -> str:
        """Detect the type of source citation."""
        source_lower = source.lower()
        
        if ".csv" in source_lower:
            return "csv"
        elif ".pdf" in source_lower:
            return "pdf"
        elif ".json" in source_lower:
            return "json"
        elif ".docx" in source_lower or ".doc" in source_lower:
            return "docx"
        elif "entry" in source_lower or "row" in source_lower:
            return "entry"
        else:
            return "text"
    
    def _get_source_icon(self, source_type: str) -> str:
        """Get icon for source type."""
        icon_map = {
            "csv": "📊",
            "pdf": "📄",
            "json": "📋",
            "docx": "📝",
            "txt": "📃",
            "entry": "📌"
        }
        return icon_map.get(source_type, "📎")
    
    def format_for_display(
        self,
        explainability_data: Dict[str, Any],
        format_type: str = "full"
    ) -> Dict[str, Any]:
        """
        Format explainability data for specific display contexts.
        
        Args:
            explainability_data: Generated explainability data
            format_type: 'full', 'compact', or 'minimal'
            
        Returns:
            Formatted data appropriate for the display context
        """
        if format_type == "minimal":
            return {
                "summary": explainability_data.get("summary", {}),
                "confidence": {
                    "score": explainability_data.get("confidence", {}).get("overall_percent", "0%"),
                    "level": explainability_data.get("confidence", {}).get("level", "unknown")
                }
            }
        
        elif format_type == "compact":
            return {
                "summary": explainability_data.get("summary", {}),
                "retrieval": explainability_data.get("retrieval", {}),
                "confidence": explainability_data.get("confidence", {}),
                "sources": explainability_data.get("sources", [])[:3]
            }
        
        # Full format
        return explainability_data


# Factory function
def create_explainability_generator() -> ExplainabilityGenerator:
    """Create a new ExplainabilityGenerator instance."""
    return ExplainabilityGenerator()
