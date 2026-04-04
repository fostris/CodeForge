"""Pipeline state definitions using TypedDict."""

from typing import TypedDict, Optional, List, Dict, Any, Literal


class TaskSpec(TypedDict, total=False):
    """Task from TASK_GRAPH.json."""
    id: str
    name: str
    module: str
    files: List[str]
    depends_on: List[str]
    size: Literal["S", "M", "L"]
    risk_level: Literal["low", "medium", "high"]
    model_tier: Literal["local_cheap", "local_strong", "cloud"]
    description: str
    done_criteria: List[str]
    test_file: Optional[str]


class StageCheckpoint(TypedDict, total=False):
    """Checkpoint data for a pipeline stage."""
    stage: str
    timestamp: str
    status: Literal["pending", "passed", "failed", "escalated"]
    input: Dict[str, Any]
    output: Dict[str, Any]
    error: Optional[str]


class IterationSnapshot(TypedDict, total=False):
    """Snapshot of an implementation iteration."""
    iteration: int
    timestamp: str
    model_used: str
    prompt_tokens: int
    response_tokens: int
    generated_code: str
    diff: str
    test_results: str
    passed: bool


class PipelineState(TypedDict, total=False):
    """Complete state for LangGraph pipeline."""
    
    # Execution context
    execution_id: str
    current_stage: Literal[
        "intake", "architecture", "decomposition", 
        "tdd_first", "impl_loop", "final_review", "done"
    ]
    status: Literal["pending", "in_progress", "succeeding", "failing", "escalating", "done"]
    
    # Project artifacts
    spec: Dict[str, Any]
    architecture: Dict[str, Any]
    task_graph: List[TaskSpec]
    codebase_rules: str
    
    # Current task execution
    current_task: Optional[TaskSpec]
    current_task_index: int
    iteration: int  # Within task implementation loop
    model_tier: Literal["local_cheap", "local_strong", "cloud"]
    
    # Generated content
    prompt: str
    response: str
    test_code: str
    implementation_code: str
    
    # Execution results
    test_results: str
    test_passed: bool
    diff_lines: int
    
    # Error tracking
    last_error: Optional[str]
    error_count: int
    escalation_count: int
    escalation_reasons: List[str]
    
    # Iteration history
    iterations: List[IterationSnapshot]
    
    # Stage checkpoints
    checkpoints: Dict[str, StageCheckpoint]
    human_approval_required: bool
    
    # Output artifacts
    generated_files: Dict[str, str]  # filename -> content
    diffs: List[Dict[str, str]]  # List of {file: path, diff: content}
    final_report: Optional[str]
    
    # Metadata
    project_root: str
    artifacts_dir: str
    start_time: str
    end_time: Optional[str]
    duration_seconds: Optional[int]
