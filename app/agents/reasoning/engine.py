from typing import Dict, Any, List
from app.agents.context import ExecutionContext
from app.agents.reasoning.models import ReasoningState, DecisionNode
from app.agents.reasoning.evidence import EvidenceCollector
from app.agents.reasoning.context import ContextBuilder
from app.agents.reasoning.prompts import PromptBuilder
from app.agents.reasoning.evaluation import AlternativeEvaluation
from app.agents.reasoning.decision import DecisionGenerator
from app.agents.reasoning.confidence import ConfidenceCalculator
from app.agents.reasoning.validation import DecisionValidator
from app.agents.reasoning.formatting import StructuredOutputGenerator, ResponseFormatter

class ReasoningEngine:
    """
    The orchestrator for the Reasoning Pipeline.
    Consumes execution results and triggers evaluation steps sequentially.
    """
    def __init__(self):
        self.evidence_collector = EvidenceCollector()
        self.context_builder = ContextBuilder()
        self.prompt_builder = PromptBuilder()
        self.evaluator = AlternativeEvaluation()
        self.decision_generator = DecisionGenerator()
        self.confidence_calculator = ConfidenceCalculator()
        self.validator = DecisionValidator()
        self.output_generator = StructuredOutputGenerator()
        self.formatter = ResponseFormatter()

    def process(self, context: ExecutionContext, execution_results: List[Dict[str, Any]]) -> ReasoningState:
        """
        Runs the complete reasoning pipeline deterministically.
        """
        # 1. Collect Evidence
        evidence = self.evidence_collector.collect(execution_results, context)
        
        # 2. Build Reasoning Context
        built_context = self.context_builder.build(context, evidence)
        
        # 3. Build Prompt (For future LLM integration, we just store it in state for now)
        prompt_string = self.prompt_builder.build_prompt(built_context)
        
        # 4. Evaluate Alternatives
        alternatives = self.evaluator.evaluate(built_context)
        
        # 5. Generate Decision
        selected_decision = self.decision_generator.generate(alternatives)
        
        # 6. Calculate Confidence
        if selected_decision:
            selected_decision.confidence_score = self.confidence_calculator.calculate(selected_decision)
            
        # 7. Validate Decision
        is_valid = self.validator.validate(selected_decision)
        
        # 8. Create Reasoning State
        state = ReasoningState(
            execution_id=context.execution_id,
            context=built_context,
            evidence=evidence,
            alternatives=alternatives,
            selected_decision=selected_decision,
            is_validated=is_valid
        )
        
        return state
        
    def format_output(self, state: ReasoningState) -> Dict[str, Any]:
        """
        Formats the validated reasoning state into the final response payload.
        """
        if not state.is_validated or not state.selected_decision:
            return {"error": "Reasoning failed to produce a valid decision."}
            
        structured_data = self.output_generator.generate(state.selected_decision)
        final_response = self.formatter.format_response(state.selected_decision, structured_data)
        return final_response
