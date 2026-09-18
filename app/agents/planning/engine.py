from app.agents.context import ExecutionContext
from app.agents.planning.models import ExecutionPlan
from app.agents.planning.intent import IntentAnalyzer
from app.agents.planning.goal import GoalExtractor
from app.agents.planning.constraints import ConstraintDetector
from app.agents.planning.requirements import InformationRequirementAnalyzer
from app.agents.planning.decomposition import TaskDecomposer
from app.agents.planning.dependencies import DependencyAnalyzer
from app.agents.planning.execution import ExecutionPlanner
from app.agents.planning.validation import PlanValidator

class PlanningEngine:
    """
    The intelligence core of the SafeShe Agent Runtime.
    Transforms a user's high-level objective into a structured, executable plan.
    """
    def __init__(self):
        self.intent_analyzer = IntentAnalyzer()
        self.goal_extractor = GoalExtractor()
        self.constraint_detector = ConstraintDetector()
        self.req_analyzer = InformationRequirementAnalyzer()
        self.task_decomposer = TaskDecomposer()
        self.dependency_analyzer = DependencyAnalyzer()
        self.execution_planner = ExecutionPlanner()
        self.plan_validator = PlanValidator()

    def create_plan(self, context: ExecutionContext) -> ExecutionPlan:
        # 1. Intent Analysis
        intent = self.intent_analyzer.analyze(context)
        
        # 2. Goal Extraction
        goals = self.goal_extractor.extract(context, intent)
        
        # 3. Constraint Detection
        constraints = self.constraint_detector.detect(context)
        
        # 4. Information Requirement Analysis
        requirements = self.req_analyzer.analyze(context, goals)
        
        # 5. Task Decomposition
        tasks = self.task_decomposer.decompose(context, requirements)
        
        # 6. Dependency Analysis
        tasks_with_deps = self.dependency_analyzer.analyze(tasks)
        
        # 7. Execution Planning (Graph construction)
        graph = self.execution_planner.generate_graph(tasks_with_deps)
        
        # Assemble preliminary plan
        plan = ExecutionPlan(
            intent=intent,
            goals=goals,
            constraints=constraints,
            required_information=requirements,
            graph=graph
        )
        
        # 8. Plan Validation
        is_valid = self.plan_validator.validate(plan)
        if not is_valid:
            raise ValueError("Planning Engine produced an invalid execution plan.")
            
        return plan
