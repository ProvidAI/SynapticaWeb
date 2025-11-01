"""Test script for Research Verifier agent."""

import asyncio
from agents.verifier.tools.research_verification_tools import (
    verify_research_output,
    check_citation_quality,
    validate_statistical_significance,
)


async def test_literature_miner_verification():
    """Test verification of Literature Miner output."""
    print("\n" + "="*80)
    print("TEST 1: Literature Miner - GOOD OUTPUT")
    print("="*80)

    # Simulate a good Literature Miner output
    good_output = {
        "papers": [
            {
                "title": "Deep Learning for Natural Language Processing",
                "authors": ["Smith, J.", "Doe, A."],
                "year": 2023,
                "doi": "10.1234/example.2023.001",
                "journal": "Journal of AI Research",
                "citation": "Smith et al. (2023)"
            },
            {
                "title": "Transformer Models in NLP",
                "authors": ["Johnson, B."],
                "year": 2022,
                "doi": "10.1234/example.2022.002",
                "journal": "ACL Proceedings",
                "citation": "Johnson (2022)"
            },
            {
                "title": "BERT and Beyond",
                "authors": ["Williams, C."],
                "year": 2021,
                "doi": "10.1234/example.2021.003",
                "journal": "Nature Machine Intelligence",
                "citation": "Williams (2021)"
            },
            {
                "title": "GPT Models Evolution",
                "authors": ["Brown, T."],
                "year": 2024,
                "doi": "10.1234/example.2024.004",
                "journal": "AI Magazine",
                "citation": "Brown (2024)"
            },
            {
                "title": "Large Language Models Survey",
                "authors": ["Davis, R."],
                "year": 2023,
                "doi": "10.1234/example.2023.005",
                "journal": "Neural Computation",
                "citation": "Davis (2023)"
            },
            {
                "title": "Fine-tuning Strategies",
                "authors": ["Miller, K."],
                "year": 2022,
                "doi": "10.1234/example.2022.006",
                "journal": "EMNLP Proceedings",
                "citation": "Miller (2022)"
            },
            {
                "title": "Transfer Learning in NLP",
                "authors": ["Wilson, M."],
                "year": 2023,
                "doi": "10.1234/example.2023.007",
                "journal": "Computational Linguistics",
                "citation": "Wilson (2023)"
            },
            {
                "title": "Attention Mechanisms",
                "authors": ["Taylor, S."],
                "year": 2021,
                "doi": "10.1234/example.2021.008",
                "journal": "ICML Proceedings",
                "citation": "Taylor (2021)"
            },
            {
                "title": "Neural Language Models",
                "authors": ["Anderson, P."],
                "year": 2024,
                "doi": "10.1234/example.2024.009",
                "journal": "IEEE Transactions on AI",
                "citation": "Anderson (2024)"
            },
            {
                "title": "Context Understanding in LLMs",
                "authors": ["Thomas, L."],
                "year": 2023,
                "doi": "10.1234/example.2023.010",
                "journal": "NAACL Proceedings",
                "citation": "Thomas (2023)"
            },
            {
                "title": "Prompt Engineering Best Practices",
                "authors": ["Garcia, H."],
                "year": 2022,
                "doi": "10.1234/example.2022.011",
                "journal": "AI Conference 2022",
                "citation": "Garcia (2022)"
            },
        ],
        "search_query": "large language models natural language processing",
        "total_retrieved": 11,
        "date_range": "2020-2024"
    }

    result = await verify_research_output(
        task_id=1,
        phase="knowledge",
        agent_role="literature_miner",
        output=good_output,
        expected_schema={
            "required": ["papers", "search_query", "total_retrieved"]
        }
    )

    print(f"\nVerification Result:")
    print(f"  Passed: {result['passed']}")
    print(f"  Quality Score: {result['quality_score']}/100")
    print(f"  Decision: {result['decision']}")
    print(f"  Verification Time: {result['verification_time']:.2f}s")
    print(f"\nDimension Scores:")
    for dimension, score in result['dimension_scores'].items():
        print(f"  {dimension}: {score}/100")
    print(f"\nFeedback:\n{result['feedback']}")


async def test_bad_literature_miner():
    """Test verification of poor Literature Miner output."""
    print("\n" + "="*80)
    print("TEST 2: Literature Miner - BAD OUTPUT (insufficient papers)")
    print("="*80)

    # Simulate a bad Literature Miner output (too few papers)
    bad_output = {
        "papers": [
            {
                "title": "Old Paper",
                "authors": ["Smith, J."],
                "year": 2015,  # Too old
                "journal": "Some Journal"
                # Missing DOI
            },
            {
                "title": "Another Old Paper",
                "authors": ["Doe, A."],
                "year": 2016,
                "journal": "Some Journal"
            },
        ],
        "search_query": "machine learning",
        "total_retrieved": 2
    }

    result = await verify_research_output(
        task_id=2,
        phase="knowledge",
        agent_role="literature_miner",
        output=bad_output,
        expected_schema={
            "required": ["papers", "search_query", "total_retrieved"]
        }
    )

    print(f"\nVerification Result:")
    print(f"  Passed: {result['passed']}")
    print(f"  Quality Score: {result['quality_score']}/100")
    print(f"  Decision: {result['decision']}")
    print(f"  Verification Time: {result['verification_time']:.2f}s")
    print(f"\nFeedback:\n{result['feedback']}")


async def test_hypothesis_designer():
    """Test verification of Hypothesis Designer output."""
    print("\n" + "="*80)
    print("TEST 3: Hypothesis Designer - GOOD OUTPUT")
    print("="*80)

    good_output = {
        "null_hypothesis": "There is no significant difference in user engagement between control and treatment groups",
        "alternative_hypothesis": "The treatment group shows significantly higher user engagement than the control group",
        "independent_variables": ["group_type (control/treatment)", "user_experience_level"],
        "dependent_variables": ["engagement_score", "time_on_platform"],
        "control_variables": ["age", "device_type", "time_of_day"],
        "expected_outcomes": "We expect the treatment group to show 15-20% higher engagement scores",
        "statistical_tests": ["t-test", "ANOVA", "regression analysis"],
        "sample_size": 500,
        "power_analysis": "Power = 0.8, Effect size = 0.3"
    }

    result = await verify_research_output(
        task_id=3,
        phase="experimentation",
        agent_role="hypothesis_designer",
        output=good_output
    )

    print(f"\nVerification Result:")
    print(f"  Passed: {result['passed']}")
    print(f"  Quality Score: {result['quality_score']}/100")
    print(f"  Decision: {result['decision']}")
    print(f"\nDimension Scores:")
    for dimension, score in result['dimension_scores'].items():
        print(f"  {dimension}: {score}/100")
    print(f"\nFeedback:\n{result['feedback']}")


async def test_experiment_runner():
    """Test verification of Experiment Runner output."""
    print("\n" + "="*80)
    print("TEST 4: Experiment Runner - GOOD OUTPUT")
    print("="*80)

    good_output = {
        "results": {
            "p_value": 0.023,
            "confidence_interval": [0.12, 0.28],
            "effect_size": 0.35,
            "statistical_test": "independent t-test"
        },
        "sample_size": 500,
        "n": 500,
        "summary_statistics": {
            "control_mean": 3.2,
            "treatment_mean": 3.9,
            "control_std": 0.8,
            "treatment_std": 0.9
        },
        "visualizations": ["histogram.png", "boxplot.png"],
        "raw_data_summary": "Available in results.csv"
    }

    result = await verify_research_output(
        task_id=4,
        phase="experimentation",
        agent_role="experiment_runner",
        output=good_output
    )

    print(f"\nVerification Result:")
    print(f"  Passed: {result['passed']}")
    print(f"  Quality Score: {result['quality_score']}/100")
    print(f"  Decision: {result['decision']}")
    print(f"\nFeedback:\n{result['feedback']}")


async def test_citation_quality():
    """Test citation quality checking."""
    print("\n" + "="*80)
    print("TEST 5: Citation Quality Check")
    print("="*80)

    citations = [
        {"doi": "10.1234/example.2023.001", "year": 2023, "journal": "Nature"},
        {"doi": "10.1234/example.2022.002", "year": 2022, "journal": "Science"},
        {"doi": "10.1234/example.2024.003", "year": 2024, "journal": "Cell"},
        {"doi": "10.1234/example.2021.004", "year": 2021, "journal": "PNAS"},
        {"doi": "10.1234/example.2023.005", "year": 2023, "journal": "Nature Methods"},
        {"doi": "10.1234/example.2022.006", "year": 2022, "journal": "Nature Biotech"},
        {"doi": "10.1234/example.2024.007", "year": 2024, "journal": "eLife"},
        {"doi": "10.1234/example.2023.008", "year": 2023, "journal": "PLOS ONE"},
        {"doi": "10.1234/example.2022.009", "year": 2022, "journal": "BMC Genomics"},
        {"doi": "10.1234/example.2021.010", "year": 2021, "journal": "Genome Biology"},
    ]

    result = await check_citation_quality(citations)

    print(f"\nCitation Quality Result:")
    print(f"  Valid: {result['valid']}")
    print(f"  Score: {result['score']}/100")
    print(f"  Issues: {result['issues']}")
    print(f"\nStatistics:")
    for key, value in result['statistics'].items():
        print(f"  {key}: {value}")


async def test_statistical_significance():
    """Test statistical significance validation."""
    print("\n" + "="*80)
    print("TEST 6: Statistical Significance Validation")
    print("="*80)

    # Good statistical results
    good_results = {
        "p_value": 0.012,
        "confidence_interval": [0.15, 0.45],
        "effect_size": 0.42,
        "sample_size": 250,
        "statistical_test": "two-sample t-test",
        "test_type": "independent t-test"
    }

    result = await validate_statistical_significance(good_results)

    print(f"\nStatistical Validation Result:")
    print(f"  Valid: {result['valid']}")
    print(f"  Significant: {result['significant']}")
    print(f"  Issues: {result['issues']}")

    # Bad statistical results (missing fields)
    print("\n" + "-"*80)
    print("TEST 6b: Statistical Significance - MISSING FIELDS")
    print("-"*80)

    bad_results = {
        "p_value": 0.045
        # Missing other required fields
    }

    result = await validate_statistical_significance(bad_results)

    print(f"\nStatistical Validation Result:")
    print(f"  Valid: {result['valid']}")
    print(f"  Issues: {result['issues']}")


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("RESEARCH VERIFIER TEST SUITE")
    print("="*80)

    await test_literature_miner_verification()
    await test_bad_literature_miner()
    await test_hypothesis_designer()
    await test_experiment_runner()
    await test_citation_quality()
    await test_statistical_significance()

    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
