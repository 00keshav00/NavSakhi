"""
AI Provider Placeholder Package.
Will implement BaseLLMProvider for connecting to Ollama, OpenAI, or local models.
"""

class AIPipelineProvider:
    """
    Handles interactions with LLMs.
    Crucially: This NEVER makes decisions. It only translates numerical metrics into human explanations.
    """
    
    async def explain_decision(self, metrics: dict) -> str:
        """
        Simulates an LLM API call (like OpenAI or Ollama).
        In production, this would format a prompt with the metrics and await the LLM's response.
        
        # [LLM MODEL BOUNDARY]
        # TODO: Integrate your real LLM provider here.
        # Example using LangChain or OpenAI:
        # prompt = f"Explain this safety decision to a user warmly. Metrics: {metrics}"
        # response = await openai_client.chat.completions.create(..., messages=[{"role": "user", "content": prompt}])
        # return response.choices[0].message.content
        """
        score = metrics.get("overall_score", 0) * 100
        
        if score > 80:
            return f"I selected this route because it has an optimal safety rating of {score:.0f}%. It features well-lit streets, verified safe zones, and strong historical security data."
        elif score > 50:
            return f"This route was chosen with a moderate safety score of {score:.0f}%. While generally secure, please remain aware of your surroundings in lower-density areas."
        else:
            return f"Caution advised. This route scored {score:.0f}%. We have minimized risks where possible, but alternative routes are severely limited."
