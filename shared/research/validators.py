"""Validators for research data schemas."""

from typing import Dict, Any, List, Optional
from .schemas import (
    ProblemStatement,
    LiteratureCorpus,
    ExperimentResult,
    ResearchPaper,
    HypothesisDesign,
    Interpretation,
    BiasReport,
    ComplianceReport,
    PeerReview,
)


def validate_problem_statement(data: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[ProblemStatement]]:
    """
    Validate problem statement data.

    Args:
        data: Dictionary containing problem statement data

    Returns:
        Tuple of (is_valid, error_message, validated_object)
    """
    try:
        problem = ProblemStatement(**data)

        # Additional validation logic
        if problem.feasibility_score and problem.feasibility_score < 0.3:
            return False, "Feasibility score too low (< 0.3)", None

        if problem.novelty_score and problem.novelty_score < 0.2:
            return False, "Novelty score too low (< 0.2)", None

        return True, None, problem

    except Exception as e:
        return False, str(e), None


def validate_literature_corpus(data: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[LiteratureCorpus]]:
    """
    Validate literature corpus data.

    Args:
        data: Dictionary containing literature corpus data

    Returns:
        Tuple of (is_valid, error_message, validated_object)
    """
    try:
        corpus = LiteratureCorpus(**data)

        # Additional validation
        if len(corpus.papers) < 3:
            return False, "Insufficient papers in corpus (minimum 3 required)", None

        # Check for high relevance papers
        high_relevance = [p for p in corpus.papers if p.relevance_score and p.relevance_score >= 0.7]
        if not high_relevance:
            return False, "No high-relevance papers found (>= 0.7)", None

        return True, None, corpus

    except Exception as e:
        return False, str(e), None


def validate_hypothesis_design(data: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[HypothesisDesign]]:
    """
    Validate hypothesis design data.

    Args:
        data: Dictionary containing hypothesis design data

    Returns:
        Tuple of (is_valid, error_message, validated_object)
    """
    try:
        hypothesis = HypothesisDesign(**data)

        # Validate variables
        if 'independent' not in hypothesis.variables:
            return False, "Missing independent variable", None
        if 'dependent' not in hypothesis.variables:
            return False, "Missing dependent variable", None

        # Validate metrics
        if len(hypothesis.metrics) < 1:
            return False, "At least one metric required", None

        return True, None, hypothesis

    except Exception as e:
        return False, str(e), None


def validate_experiment_result(data: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[ExperimentResult]]:
    """
    Validate experiment result data.

    Args:
        data: Dictionary containing experiment result data

    Returns:
        Tuple of (is_valid, error_message, validated_object)
    """
    try:
        result = ExperimentResult(**data)

        # Validate results contain data
        if not result.raw_results:
            return False, "Empty raw results", None

        # Validate verification if present
        if result.verification_score is not None and result.verification_score < 0.5:
            return False, f"Verification score too low ({result.verification_score} < 0.5)", None

        # Check reproducibility
        if result.reproducible is False and result.verification_score is not None:
            return False, "Experiment marked as non-reproducible", None

        return True, None, result

    except Exception as e:
        return False, str(e), None


def validate_interpretation(data: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[Interpretation]]:
    """
    Validate interpretation data.

    Args:
        data: Dictionary containing interpretation data

    Returns:
        Tuple of (is_valid, error_message, validated_object)
    """
    try:
        interpretation = Interpretation(**data)

        # Validate confidence level
        if interpretation.confidence < 0.3:
            return False, f"Confidence too low ({interpretation.confidence} < 0.3)", None

        # Validate insights and conclusions
        if len(interpretation.insights) < 2:
            return False, "At least 2 insights required", None

        if len(interpretation.conclusions) < 1:
            return False, "At least 1 conclusion required", None

        return True, None, interpretation

    except Exception as e:
        return False, str(e), None


def validate_bias_report(data: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[BiasReport]]:
    """
    Validate bias audit report data.

    Args:
        data: Dictionary containing bias report data

    Returns:
        Tuple of (is_valid, error_message, validated_object)
    """
    try:
        report = BiasReport(**data)

        # Check risk level
        if report.risk_level not in ['low', 'medium', 'high']:
            return False, f"Invalid risk level: {report.risk_level}", None

        # High bias threshold
        if report.overall_bias_score > 0.7:
            return False, f"Overall bias score too high ({report.overall_bias_score} > 0.7)", None

        return True, None, report

    except Exception as e:
        return False, str(e), None


def validate_compliance_report(data: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[ComplianceReport]]:
    """
    Validate compliance report data.

    Args:
        data: Dictionary containing compliance report data

    Returns:
        Tuple of (is_valid, error_message, validated_object)
    """
    try:
        report = ComplianceReport(**data)

        # Check plagiarism
        if report.plagiarism_score > 0.2:
            return False, f"Plagiarism score too high ({report.plagiarism_score} > 0.2)", None

        # Check compliance
        if report.compliance_score < 0.7:
            return False, f"Compliance score too low ({report.compliance_score} < 0.7)", None

        # Check critical violations
        if report.ethics_violations:
            return False, f"Ethics violations found: {', '.join(report.ethics_violations)}", None

        return True, None, report

    except Exception as e:
        return False, str(e), None


def validate_research_paper(data: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[ResearchPaper]]:
    """
    Validate complete research paper data.

    Args:
        data: Dictionary containing research paper data

    Returns:
        Tuple of (is_valid, error_message, validated_object)
    """
    try:
        paper = ResearchPaper(**data)

        # Validate word count
        if paper.total_word_count < 1000:
            return False, f"Paper too short ({paper.total_word_count} < 1000 words)", None

        if paper.total_word_count > 10000:
            return False, f"Paper too long ({paper.total_word_count} > 10000 words)", None

        # Validate sections
        section_types = {s.section_type for s in paper.sections}
        required = {'introduction', 'methods', 'results', 'discussion', 'conclusion'}
        missing = required - section_types
        if missing:
            return False, f"Missing required sections: {missing}", None

        # Validate references
        if len(paper.references) < 5:
            return False, "Insufficient references (minimum 5 required)", None

        # Check section quality scores if present
        low_quality = [s for s in paper.sections if s.quality_score and s.quality_score < 0.5]
        if low_quality:
            return False, f"Low quality sections found: {[s.section_type for s in low_quality]}", None

        return True, None, paper

    except Exception as e:
        return False, str(e), None


def validate_peer_review(data: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[PeerReview]]:
    """
    Validate peer review data.

    Args:
        data: Dictionary containing peer review data

    Returns:
        Tuple of (is_valid, error_message, validated_object)
    """
    try:
        review = PeerReview(**data)

        # Validate overall score
        if review.overall_score < 3 and review.recommendation == 'accept':
            return False, "Cannot accept paper with score < 3", None

        if review.overall_score > 7 and review.recommendation == 'reject':
            return False, "Cannot reject paper with score > 7", None

        # Validate confidence
        if review.confidence < 0.3:
            return False, f"Reviewer confidence too low ({review.confidence} < 0.3)", None

        # Validate detailed feedback
        if len(review.strengths) == 0:
            return False, "No strengths identified", None

        if len(review.weaknesses) == 0:
            return False, "No weaknesses identified", None

        return True, None, review

    except Exception as e:
        return False, str(e), None


def validate_agent_output(agent_type: str, output_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate agent output based on agent type.

    Args:
        agent_type: Type of agent (e.g., 'problem_framer', 'literature_miner')
        output_data: Output data from agent

    Returns:
        Tuple of (is_valid, error_message)
    """
    validators = {
        'problem_framer': validate_problem_statement,
        'literature_miner': validate_literature_corpus,
        'hypothesis_designer': validate_hypothesis_design,
        'data_scientist': validate_experiment_result,
        'result_interpreter': validate_interpretation,
        'bias_auditor': validate_bias_report,
        'ethics_compliance': validate_compliance_report,
        'research_synthesizer': validate_research_paper,
        'peer_reviewer': validate_peer_review,
    }

    if agent_type not in validators:
        return False, f"Unknown agent type: {agent_type}"

    is_valid, error, _ = validators[agent_type](output_data)
    return is_valid, error


def validate_phase_transition(
    current_phase: str,
    next_phase: str,
    phase_outputs: Dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """
    Validate whether pipeline can transition to next phase.

    Args:
        current_phase: Current phase name
        next_phase: Next phase name
        phase_outputs: Outputs from current phase

    Returns:
        Tuple of (can_transition, error_message)
    """
    # Define required outputs for each phase
    phase_requirements = {
        'ideation': ['problem_statement', 'feasibility_assessment', 'task_plan'],
        'knowledge_retrieval': ['literature_corpus', 'ranked_papers', 'extracted_knowledge'],
        'experimentation': ['hypothesis', 'experiment_results', 'verification_report'],
        'interpretation': ['insights', 'bias_report', 'compliance_report'],
        'publication': ['research_paper', 'peer_review', 'reputation_updates']
    }

    if current_phase not in phase_requirements:
        return False, f"Unknown phase: {current_phase}"

    required = phase_requirements[current_phase]
    missing = [r for r in required if r not in phase_outputs or not phase_outputs[r]]

    if missing:
        return False, f"Missing required outputs from {current_phase}: {missing}"

    return True, None