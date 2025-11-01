"""Research-specific verification tools for academic research pipeline."""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from shared.database import SessionLocal
from shared.database.models import Task, Agent


async def verify_research_output(
    task_id: int,
    phase: str,
    agent_role: str,
    output: Dict[str, Any],
    expected_schema: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Verify research output against phase-specific criteria.

    Args:
        task_id: ID of the task being verified
        phase: Research phase (ideation, knowledge, experimentation, interpretation, publication)
        agent_role: Specific agent role (e.g., "literature_miner", "hypothesis_designer")
        output: The agent's output to verify
        expected_schema: Optional schema to validate against

    Returns:
        Dict with verification results including:
        - passed: bool
        - quality_score: float (0-100)
        - dimension_scores: Dict[str, float]
        - feedback: str
        - decision: str (accept/revision/reject)
    """
    # Step 1: Fast initial check (< 5 seconds)
    fast_check = _fast_initial_check(output, expected_schema)
    if not fast_check["passed"]:
        return {
            "passed": False,
            "quality_score": 0,
            "dimension_scores": {},
            "feedback": fast_check["feedback"],
            "decision": "reject",
            "verification_time": fast_check["time"]
        }

    # Step 2: Phase-specific validation (5-15 seconds)
    phase_validation = await _validate_by_phase(phase, agent_role, output)

    # Step 3: Quality scoring (10-20 seconds)
    scores = await calculate_quality_score(output, phase, agent_role, phase_validation)

    # Step 4: Decision & action (< 5 seconds)
    decision = _make_decision(scores)
    feedback = await generate_feedback_report(scores, decision, phase_validation)

    return {
        "passed": decision["decision"] == "accept",
        "quality_score": scores["overall_score"],
        "dimension_scores": scores["dimension_scores"],
        "feedback": feedback,
        "decision": decision["decision"],
        "requires_revision": decision["decision"] == "revision",
        "verification_time": fast_check["time"] + phase_validation["time"] + scores["time"] + decision["time"]
    }


def _fast_initial_check(output: Dict[str, Any], expected_schema: Optional[Dict[str, Any]]) -> Dict[str, bool]:
    """
    Fast initial validation (< 5 seconds).
    Check basic requirements before deeper validation.
    """
    start_time = datetime.now()

    # Check if output is empty or None
    if not output:
        return {
            "passed": False,
            "feedback": "Output is empty or None",
            "time": (datetime.now() - start_time).total_seconds()
        }

    # Check if output is a dict
    if not isinstance(output, dict):
        return {
            "passed": False,
            "feedback": "Output must be a dictionary",
            "time": (datetime.now() - start_time).total_seconds()
        }

    # Schema validation if provided
    if expected_schema:
        required_fields = expected_schema.get("required", [])
        missing_fields = [field for field in required_fields if field not in output]
        if missing_fields:
            return {
                "passed": False,
                "feedback": f"Missing required fields: {', '.join(missing_fields)}",
                "time": (datetime.now() - start_time).total_seconds()
            }

    # Check reasonable data size (< 100MB)
    import sys
    output_size = sys.getsizeof(str(output))
    if output_size > 100 * 1024 * 1024:  # 100MB
        return {
            "passed": False,
            "feedback": f"Output size too large: {output_size / (1024*1024):.2f}MB",
            "time": (datetime.now() - start_time).total_seconds()
        }

    return {
        "passed": True,
        "feedback": "Fast checks passed",
        "time": (datetime.now() - start_time).total_seconds()
    }


async def _validate_by_phase(phase: str, agent_role: str, output: Dict[str, Any]) -> Dict[str, Any]:
    """Phase-specific validation (5-15 seconds)."""
    start_time = datetime.now()

    validation_result = {
        "passed": True,
        "issues": [],
        "time": 0
    }

    phase_lower = phase.lower()

    # PHASE 1: IDEATION
    if phase_lower == "ideation":
        if agent_role == "problem_framer":
            validation_result = _validate_problem_framer(output)
        elif agent_role == "feasibility_analyst":
            validation_result = _validate_feasibility_analyst(output)
        elif agent_role == "goal_planner":
            validation_result = _validate_goal_planner(output)

    # PHASE 2: KNOWLEDGE
    elif phase_lower == "knowledge":
        if agent_role == "literature_miner":
            validation_result = _validate_literature_miner(output)
        elif agent_role == "knowledge_synthesizer":
            validation_result = _validate_knowledge_synthesizer(output)

    # PHASE 3: EXPERIMENTATION
    elif phase_lower == "experimentation":
        if agent_role == "hypothesis_designer":
            validation_result = _validate_hypothesis_designer(output)
        elif agent_role == "code_generator":
            validation_result = await _validate_code_generator(output)
        elif agent_role == "experiment_runner":
            validation_result = _validate_experiment_runner(output)

    # PHASE 4: INTERPRETATION
    elif phase_lower == "interpretation":
        if agent_role == "insight_generator":
            validation_result = _validate_insight_generator(output)
        elif agent_role == "bias_detector":
            validation_result = _validate_bias_detector(output)
        elif agent_role == "compliance_checker":
            validation_result = _validate_compliance_checker(output)

    # PHASE 5: PUBLICATION
    elif phase_lower == "publication":
        if agent_role == "paper_writer":
            validation_result = _validate_paper_writer(output)
        elif agent_role == "peer_reviewer":
            validation_result = _validate_peer_reviewer(output)

    validation_result["time"] = (datetime.now() - start_time).total_seconds()
    return validation_result


# ============================================================================
# PHASE-SPECIFIC VALIDATORS
# ============================================================================

def _validate_problem_framer(output: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Problem Framer output."""
    issues = []

    # Check for clear research question
    if "research_question" not in output or len(output.get("research_question", "")) < 20:
        issues.append("Research question missing or too short (min 20 chars)")

    # Check for scope definition
    if "scope" not in output:
        issues.append("Research scope not defined")

    # Check for measurable objectives
    if "objectives" not in output or not isinstance(output.get("objectives"), list):
        issues.append("Measurable objectives missing or not a list")
    elif len(output["objectives"]) == 0:
        issues.append("No objectives provided")

    # Check for domain keywords
    if "keywords" not in output or len(output.get("keywords", [])) < 3:
        issues.append("Insufficient domain keywords (min 3)")

    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


def _validate_feasibility_analyst(output: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Feasibility Analyst output."""
    issues = []

    # Check for timeline estimate
    if "timeline" not in output:
        issues.append("Timeline estimate missing")

    # Check for data availability assessment
    if "data_availability" not in output:
        issues.append("Data availability assessment missing")

    # Check for resource requirements
    if "resources" not in output:
        issues.append("Resource requirements not identified")

    # Check for risk factors
    if "risks" not in output or len(output.get("risks", [])) == 0:
        issues.append("Risk factors not acknowledged")

    # Check for alternative approaches
    if "alternatives" not in output:
        issues.append("Alternative approaches not considered")

    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


def _validate_goal_planner(output: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Goal Planner output."""
    issues = []

    # Check for SMART objectives
    if "objectives" not in output or not isinstance(output.get("objectives"), list):
        issues.append("SMART objectives missing")

    # Check for milestones
    if "milestones" not in output or len(output.get("milestones", [])) == 0:
        issues.append("Milestones not defined")

    # Check for deliverables
    if "deliverables" not in output:
        issues.append("Deliverables not defined")

    # Check for success criteria
    if "success_criteria" not in output:
        issues.append("Success criteria not specified")

    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


def _validate_literature_miner(output: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Literature Miner output."""
    issues = []

    # Check minimum paper count
    papers = output.get("papers", [])
    if len(papers) < 10:
        issues.append(f"Insufficient papers retrieved: {len(papers)} (min 10)")

    # Check recency (70%+ from last 5 years)
    if papers:
        recent_count = 0
        current_year = datetime.now().year
        for paper in papers:
            year = paper.get("year", 0)
            if year >= current_year - 5:
                recent_count += 1

        recency_percentage = (recent_count / len(papers)) * 100
        if recency_percentage < 70:
            issues.append(f"Insufficient recent papers: {recency_percentage:.1f}% (need 70%+ from last 5 years)")

    # Check for valid citations
    if papers:
        missing_citations = [i for i, p in enumerate(papers) if not p.get("doi") and not p.get("citation")]
        if len(missing_citations) > len(papers) * 0.2:  # More than 20% missing
            issues.append(f"{len(missing_citations)} papers missing DOI/citation information")

    # Check source diversity
    if papers:
        journals = set()
        for paper in papers:
            journal = paper.get("journal") or paper.get("venue")
            if journal:
                journals.add(journal)

        if len(journals) < min(5, len(papers) // 3):
            issues.append(f"Insufficient source diversity: {len(journals)} journals (need at least {min(5, len(papers) // 3)})")

    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


def _validate_knowledge_synthesizer(output: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Knowledge Synthesizer output."""
    issues = []

    # Check for literature summary
    if "summary" not in output or len(output.get("summary", "")) < 200:
        issues.append("Literature summary missing or too short (min 200 chars)")

    # Check for research gaps
    if "research_gaps" not in output or len(output.get("research_gaps", [])) == 0:
        issues.append("Research gaps not clearly identified")

    # Check for conflicting findings
    if "conflicting_findings" not in output:
        issues.append("Conflicting findings not addressed")

    # Check for methodological trends
    if "methodological_trends" not in output:
        issues.append("Methodological trends not noted")

    # Check connection to research question
    if "connection_to_question" not in output:
        issues.append("Connection to research question not clear")

    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


def _validate_hypothesis_designer(output: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Hypothesis Designer output."""
    issues = []

    # Check for null and alternative hypotheses
    if "null_hypothesis" not in output:
        issues.append("Null hypothesis not stated")
    if "alternative_hypothesis" not in output:
        issues.append("Alternative hypothesis not stated")

    # Check for variable definitions
    if "independent_variables" not in output:
        issues.append("Independent variables not defined")
    if "dependent_variables" not in output:
        issues.append("Dependent variables not defined")

    # Check for expected outcomes
    if "expected_outcomes" not in output:
        issues.append("Expected outcomes not specified")

    # Check for statistical tests
    if "statistical_tests" not in output or len(output.get("statistical_tests", [])) == 0:
        issues.append("Statistical tests not identified")

    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


async def _validate_code_generator(output: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Code Generator output."""
    issues = []

    # Check for code presence
    if "code" not in output or not output.get("code"):
        issues.append("Code not provided")
        return {"passed": False, "issues": issues}

    code = output["code"]

    # Check for basic Python syntax (simple check)
    try:
        compile(code, "<string>", "exec")
    except SyntaxError as e:
        issues.append(f"Code has syntax errors: {str(e)}")

    # Check for comments
    if "# " not in code and '"""' not in code and "'''" not in code:
        issues.append("Code lacks comments to explain key logic")

    # Check for dependencies
    if "dependencies" not in output:
        issues.append("Dependencies not clearly stated")

    # Check for error handling
    if "try:" not in code and "except:" not in code:
        issues.append("Code lacks proper error handling")

    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


def _validate_experiment_runner(output: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Experiment Runner output."""
    issues = []

    # Check for results
    if "results" not in output:
        issues.append("Results not provided")

    # Check for statistical tests
    results = output.get("results", {})
    if "p_value" not in results and "statistical_test" not in results:
        issues.append("Statistical tests not reported")

    # Check for confidence intervals or effect sizes
    if "confidence_interval" not in results and "effect_size" not in results:
        issues.append("Confidence intervals or effect sizes not reported")

    # Check for sample size
    if "sample_size" not in output and "n" not in output:
        issues.append("Sample size not reported")

    # Check for visualizations or summary statistics
    if "visualizations" not in output and "summary_statistics" not in output:
        issues.append("Visualizations or summary statistics not provided")

    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


def _validate_insight_generator(output: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Insight Generator output."""
    issues = []

    # Check for insights
    if "insights" not in output or len(output.get("insights", [])) == 0:
        issues.append("No insights provided")

    # Check for data support
    if "data_support" not in output:
        issues.append("Insights not clearly supported by data")

    # Check for practical implications
    if "implications" not in output:
        issues.append("Practical implications not discussed")

    # Check for limitations
    if "limitations" not in output:
        issues.append("Limitations not acknowledged")

    # Check for future directions
    if "future_research" not in output:
        issues.append("Future research directions not suggested")

    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


def _validate_bias_detector(output: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Bias Detector output."""
    issues = []

    # Check for bias scan
    if "biases_identified" not in output:
        issues.append("Systematic bias scan not performed")

    # Check for mitigation strategies
    biases = output.get("biases_identified", [])
    if biases and "mitigation_strategies" not in output:
        issues.append("Mitigation strategies not proposed for identified biases")

    # Check for transparency
    if "limitations" not in output:
        issues.append("Transparency about limitations lacking")

    # Check for alternative interpretations
    if "alternative_interpretations" not in output:
        issues.append("Alternative interpretations not considered")

    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


def _validate_compliance_checker(output: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Compliance Checker output."""
    issues = []

    # Check for ethical review
    if "ethical_review" not in output:
        issues.append("Ethical review checklist not completed")

    # Check for ethical violations
    if output.get("ethical_violations"):
        issues.append("Ethical violations detected")

    # Check for data privacy
    if "data_privacy" not in output:
        issues.append("Data privacy requirements not addressed")

    # Check for IRB considerations
    if "irb_considerations" not in output:
        issues.append("IRB considerations not addressed")

    # Check for conflicts of interest
    if "conflict_of_interest" not in output:
        issues.append("Conflict of interest disclosure missing")

    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


def _validate_paper_writer(output: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Paper Writer output."""
    issues = []

    # Check for standard sections
    required_sections = ["abstract", "introduction", "methods", "results", "discussion"]
    for section in required_sections:
        if section not in output and section.title() not in output:
            issues.append(f"Missing {section} section")

    # Check for citations
    text = str(output)
    if not re.search(r'\[\d+\]|\(\w+,?\s*\d{4}\)', text):
        issues.append("Proper citations not found throughout text")

    # Check minimum length (abstract should be substantial)
    abstract = output.get("abstract", "")
    if len(abstract) < 100:
        issues.append("Abstract too short (min 100 chars)")

    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


def _validate_peer_reviewer(output: Dict[str, Any]) -> Dict[str, Any]:
    """Validate Peer Reviewer output."""
    issues = []

    # Check for feedback
    if "feedback" not in output or not output.get("feedback"):
        issues.append("Feedback not provided")

    # Check for major/minor issues separation
    if "major_issues" not in output and "minor_issues" not in output:
        issues.append("Major and minor issues not separated")

    # Check for actionable suggestions
    if "suggestions" not in output:
        issues.append("Improvement suggestions not actionable")

    # Check for overall recommendation
    if "recommendation" not in output:
        issues.append("Overall recommendation not justified")

    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


# ============================================================================
# QUALITY SCORING
# ============================================================================

async def calculate_quality_score(
    output: Dict[str, Any],
    phase: str,
    agent_role: str,
    phase_validation: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate quality score using 6-dimensional weighted system.

    Overall Score = Completeness*0.2 + Correctness*0.25 + Academic_Rigor*0.2 +
                    Clarity*0.15 + Innovation*0.1 + Ethics*0.1
    """
    start_time = datetime.now()

    # Calculate individual dimension scores
    completeness = _score_completeness(output, phase_validation)
    correctness = _score_correctness(output, phase, agent_role)
    academic_rigor = _score_academic_rigor(output, phase, agent_role)
    clarity = _score_clarity(output)
    innovation = _score_innovation(output, phase)
    ethics = _score_ethics(output, phase_validation)

    # Calculate weighted overall score
    overall_score = (
        completeness * 0.20 +
        correctness * 0.25 +
        academic_rigor * 0.20 +
        clarity * 0.15 +
        innovation * 0.10 +
        ethics * 0.10
    )

    dimension_scores = {
        "completeness": completeness,
        "correctness": correctness,
        "academic_rigor": academic_rigor,
        "clarity": clarity,
        "innovation": innovation,
        "ethics": ethics
    }

    # Check thresholds
    thresholds_met = {
        "completeness": completeness >= 80,
        "correctness": correctness >= 85,
        "academic_rigor": academic_rigor >= 75,
        "clarity": clarity >= 70,
        "innovation": innovation >= 60,
        "ethics": ethics >= 90
    }

    return {
        "overall_score": round(overall_score, 2),
        "dimension_scores": {k: round(v, 2) for k, v in dimension_scores.items()},
        "thresholds_met": thresholds_met,
        "all_thresholds_met": all(thresholds_met.values()),
        "time": (datetime.now() - start_time).total_seconds()
    }


def _score_completeness(output: Dict[str, Any], phase_validation: Dict[str, Any]) -> float:
    """Score completeness (0-100). Threshold: >= 80"""
    score = 100.0

    # Deduct for missing fields from phase validation
    issues = phase_validation.get("issues", [])
    missing_field_issues = [i for i in issues if "missing" in i.lower() or "not provided" in i.lower()]
    score -= len(missing_field_issues) * 15  # 15 points per missing field

    # Check for placeholder values
    text = str(output).lower()
    placeholders = ["todo", "tbd", "fixme", "placeholder", "xxx"]
    for placeholder in placeholders:
        if placeholder in text:
            score -= 10

    # Check depth - penalize very short outputs
    total_text_length = sum(len(str(v)) for v in output.values() if isinstance(v, (str, list, dict)))
    if total_text_length < 200:
        score -= 20
    elif total_text_length < 500:
        score -= 10

    return max(0, min(100, score))


def _score_correctness(output: Dict[str, Any], phase: str, agent_role: str) -> float:
    """Score correctness (0-100). Threshold: >= 85"""
    score = 100.0

    # For literature miner, check citation validity
    if agent_role == "literature_miner":
        papers = output.get("papers", [])
        if papers:
            invalid_citations = sum(1 for p in papers if not p.get("doi") and not p.get("citation"))
            score -= (invalid_citations / len(papers)) * 30

    # For code generator, check for syntax errors (already checked in validation)
    if agent_role == "code_generator":
        code = output.get("code", "")
        if code:
            try:
                compile(code, "<string>", "exec")
            except SyntaxError:
                score -= 40

    # For experiment runner, check for statistical validity
    if agent_role == "experiment_runner":
        results = output.get("results", {})
        if isinstance(results, dict):
            p_value = results.get("p_value")
            if p_value is not None:
                try:
                    p_val = float(p_value)
                    if p_val < 0 or p_val > 1:
                        score -= 30  # Invalid p-value
                except (ValueError, TypeError):
                    score -= 20

    # General factual checks - look for obvious errors
    text = str(output).lower()
    error_indicators = ["error:", "exception:", "failed:", "invalid:"]
    for indicator in error_indicators:
        if indicator in text:
            score -= 15

    return max(0, min(100, score))


def _score_academic_rigor(output: Dict[str, Any], phase: str, agent_role: str) -> float:
    """Score academic rigor (0-100). Threshold: >= 75"""
    score = 100.0

    # Check for scientific method adherence
    if phase.lower() == "experimentation":
        if "hypothesis" not in str(output).lower():
            score -= 20
        if "control" not in str(output).lower() and agent_role in ["hypothesis_designer", "experiment_runner"]:
            score -= 15

    # Check for statistical rigor
    if agent_role == "experiment_runner":
        results = output.get("results", {})
        if "p_value" not in results and "statistical_test" not in results:
            score -= 25
        if "confidence_interval" not in results and "effect_size" not in results:
            score -= 15

    # Check for evidence-based claims
    text = str(output).lower()
    if "based on" in text or "according to" in text or "evidence" in text:
        score += 5  # Bonus for evidence-based language

    # Check for reproducibility considerations
    if "reproducib" in text or "replicat" in text:
        score += 5
    else:
        score -= 10

    return max(0, min(100, score))


def _score_clarity(output: Dict[str, Any]) -> float:
    """Score clarity and quality (0-100). Threshold: >= 70"""
    score = 100.0

    # Check for clear structure
    if not isinstance(output, dict) or len(output) == 0:
        return 0

    # Check for logical organization (presence of key sections)
    if len(output.keys()) < 3:
        score -= 15  # Too few sections

    # Check for professional presentation
    text = str(output)

    # Penalize excessive capitalization
    if sum(1 for c in text if c.isupper()) > len(text) * 0.3:
        score -= 10

    # Check for proper terminology (domain-specific words)
    research_terms = ["hypothesis", "methodology", "analysis", "results", "conclusion",
                     "data", "experiment", "research", "study", "findings"]
    term_count = sum(1 for term in research_terms if term in text.lower())
    if term_count < 2:
        score -= 15

    # Bonus for well-formatted output
    if any(isinstance(v, list) for v in output.values()):
        score += 5  # Bonus for using lists

    return max(0, min(100, score))


def _score_innovation(output: Dict[str, Any], phase: str) -> float:
    """Score innovation (0-100). Threshold: >= 60"""
    score = 70.0  # Start at 70 (neutral)

    text = str(output).lower()

    # Look for innovative language
    innovative_terms = ["novel", "innovative", "unique", "original", "creative",
                       "breakthrough", "new approach", "alternative"]
    innovation_count = sum(1 for term in innovative_terms if term in text)
    score += innovation_count * 5

    # Penalize overly generic approaches
    generic_terms = ["standard", "conventional", "traditional", "typical", "common"]
    generic_count = sum(1 for term in generic_terms if term in text)
    score -= generic_count * 3

    # Bonus for alternative approaches or multiple solutions
    if "alternative" in text or "alternatives" in output:
        score += 10

    # Phase-specific innovation checks
    if phase.lower() == "ideation" and "interdisciplinary" in text:
        score += 10

    if phase.lower() == "experimentation" and ("new method" in text or "novel approach" in text):
        score += 15

    return max(0, min(100, score))


def _score_ethics(output: Dict[str, Any], phase_validation: Dict[str, Any]) -> float:
    """Score ethical compliance (0-100). Threshold: >= 90 (strict)"""
    score = 100.0

    # Check for ethical violations from validation
    issues = phase_validation.get("issues", [])
    ethical_issues = [i for i in issues if "ethic" in i.lower() or "violation" in i.lower()]
    if ethical_issues:
        score = 0  # Immediate fail on ethical violations
        return score

    text = str(output).lower()

    # Check for bias awareness
    if "bias" not in text and "limitation" not in text:
        score -= 15

    # Check for transparency
    transparency_terms = ["limitation", "caveat", "assumption", "constraint"]
    if not any(term in text for term in transparency_terms):
        score -= 10

    # Check for privacy considerations (if applicable)
    if "data" in text:
        if "privacy" not in text and "anonymous" not in text and "confidential" not in text:
            score -= 10

    # Check for conflict of interest disclosure
    if "conflict" in text or "disclosure" in text:
        score += 5  # Bonus for transparency

    return max(0, min(100, score))


def _make_decision(scores: Dict[str, Any]) -> Dict[str, str]:
    """Make accept/revision/reject decision based on scores."""
    start_time = datetime.now()

    overall_score = scores["overall_score"]
    all_thresholds_met = scores["all_thresholds_met"]

    # Decision logic
    if overall_score >= 75 and all_thresholds_met:
        decision = "accept"
    elif overall_score >= 60 and not scores["dimension_scores"]["ethics"] < 90:
        decision = "revision"
    else:
        decision = "reject"

    # Strict ethics check - always reject on ethics violations
    if scores["dimension_scores"]["ethics"] < 90:
        decision = "reject"

    return {
        "decision": decision,
        "time": (datetime.now() - start_time).total_seconds()
    }


async def generate_feedback_report(
    scores: Dict[str, Any],
    decision: Dict[str, str],
    phase_validation: Dict[str, Any]
) -> str:
    """Generate detailed feedback report based on scores and decision."""
    feedback_parts = []

    overall_score = scores["overall_score"]
    dimension_scores = scores["dimension_scores"]
    decision_type = decision["decision"]

    # Header
    if decision_type == "accept":
        feedback_parts.append(f"✅ ACCEPTED - Overall Quality Score: {overall_score}/100\n")
    elif decision_type == "revision":
        feedback_parts.append(f"⚠️ REVISION NEEDED - Overall Quality Score: {overall_score}/100\n")
    else:
        feedback_parts.append(f"❌ REJECTED - Overall Quality Score: {overall_score}/100\n")

    # Dimension breakdown
    feedback_parts.append("\n**Dimension Scores:**")
    thresholds = {
        "completeness": 80,
        "correctness": 85,
        "academic_rigor": 75,
        "clarity": 70,
        "innovation": 60,
        "ethics": 90
    }

    for dimension, score in dimension_scores.items():
        threshold = thresholds[dimension]
        status = "✓" if score >= threshold else "✗"
        feedback_parts.append(f"  {status} {dimension.replace('_', ' ').title()}: {score}/100 (threshold: {threshold})")

    # Specific issues from validation
    if phase_validation.get("issues"):
        feedback_parts.append("\n**Specific Issues:**")
        for issue in phase_validation["issues"]:
            feedback_parts.append(f"  - {issue}")

    # Recommendations
    if decision_type == "revision":
        feedback_parts.append("\n**Recommendations for Improvement:**")
        for dimension, score in dimension_scores.items():
            threshold = thresholds[dimension]
            if score < threshold:
                gap = threshold - score
                feedback_parts.append(f"  - Improve {dimension.replace('_', ' ')} by {gap:.1f} points to meet threshold")

    elif decision_type == "reject":
        feedback_parts.append("\n**Critical Failures:**")
        feedback_parts.append("  - Work does not meet minimum quality standards")
        feedback_parts.append("  - Consider alternative approaches or seek additional resources")

    else:  # accept
        feedback_parts.append("\n**Strengths:**")
        top_dimensions = sorted(dimension_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        for dimension, score in top_dimensions:
            feedback_parts.append(f"  - Excellent {dimension.replace('_', ' ')}: {score}/100")

    return "\n".join(feedback_parts)


async def check_citation_quality(citations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Verify citations are valid, recent, and relevant.

    Args:
        citations: List of citation dictionaries with fields like doi, year, title, etc.

    Returns:
        Dict with validation results
    """
    if not citations:
        return {
            "valid": False,
            "reason": "No citations provided",
            "score": 0
        }

    issues = []
    score = 100.0

    # Check minimum count
    if len(citations) < 10:
        issues.append(f"Insufficient citations: {len(citations)} (recommended: 10+)")
        score -= 20

    # Check validity
    valid_count = sum(1 for c in citations if c.get("doi") or c.get("citation"))
    validity_rate = valid_count / len(citations)
    if validity_rate < 0.8:
        issues.append(f"Low citation validity: {validity_rate*100:.1f}% (need 80%+)")
        score -= 30

    # Check recency
    current_year = datetime.now().year
    recent_count = sum(1 for c in citations if c.get("year", 0) >= current_year - 5)
    recency_rate = recent_count / len(citations)
    if recency_rate < 0.7:
        issues.append(f"Citations not recent enough: {recency_rate*100:.1f}% from last 5 years (need 70%+)")
        score -= 25

    # Check diversity
    journals = set()
    for citation in citations:
        journal = citation.get("journal") or citation.get("venue")
        if journal:
            journals.add(journal)

    diversity_rate = len(journals) / len(citations)
    if diversity_rate < 0.3:
        issues.append(f"Low source diversity: {len(journals)} unique sources")
        score -= 15

    return {
        "valid": score >= 70,
        "score": max(0, min(100, score)),
        "issues": issues,
        "statistics": {
            "total_citations": len(citations),
            "valid_citations": valid_count,
            "recent_citations": recent_count,
            "unique_sources": len(journals)
        }
    }


async def validate_statistical_significance(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate statistical significance of experimental results.

    Args:
        results: Dictionary with statistical test results (p_value, confidence_interval, etc.)

    Returns:
        Dict with validation results
    """
    issues = []

    # Check for p-value
    p_value = results.get("p_value")
    if p_value is None:
        issues.append("P-value not reported")
    else:
        try:
            p_val = float(p_value)
            if p_val < 0 or p_val > 1:
                issues.append(f"Invalid p-value: {p_val} (must be between 0 and 1)")
        except (ValueError, TypeError):
            issues.append(f"Invalid p-value format: {p_value}")

    # Check for confidence intervals
    if "confidence_interval" not in results and "ci" not in results:
        issues.append("Confidence interval not reported")

    # Check for effect size
    if "effect_size" not in results:
        issues.append("Effect size not reported (recommended for completeness)")

    # Check for sample size
    if "sample_size" not in results and "n" not in results:
        issues.append("Sample size not reported")

    # Check for statistical test type
    if "test_type" not in results and "statistical_test" not in results:
        issues.append("Statistical test type not specified")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "significant": p_value is not None and float(p_value) < 0.05 if p_value else None
    }
