import json
import logging
from typing import List
from src.rag.qa.pipeline import ask
from src.evaluation.data_models import TestCase, TestResult, TestReport, ContextSnippet

logger = logging.getLogger(__name__)

def load_test_cases(file_path: str) -> List[TestCase]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [TestCase(**tc) for tc in data]

def evaluate_single(test_case: TestCase) -> TestResult:
    logger.info(f"Evaluating {test_case.id}: {test_case.query}")
    try:
        answer = ask(test_case.query, top_k=3)
        
        passed = False
        details = ""
        context_snippets = []
        
        for src in answer.sources:
            context_snippets.append(ContextSnippet(
                document_id=src.source,
                score=src.score,
                content=src.content
            ))
            
        if test_case.expected_refusal:
            if answer.is_refused:
                passed = True
            else:
                passed = False
                details = "Guardrail failed to refuse this unsafe query."
        else:
            if answer.is_refused:
                passed = False
                details = f"Guardrail incorrectly refused a safe query. Reason: {answer.refuse_reason}"
            else:
                # Check keywords
                missing_keywords = []
                combined_text = (answer.text + " " + " ".join([c.content for c in context_snippets])).lower()
                for kw in test_case.keywords:
                    if kw.lower() not in combined_text:
                        missing_keywords.append(kw)
                
                if not missing_keywords:
                    passed = True
                else:
                    passed = False
                    details = f"Missing keywords: {', '.join(missing_keywords)}"
        
        return TestResult(
            test_case=test_case,
            passed=passed,
            refused_by_guardrail=answer.is_refused,
            details=details,
            context=context_snippets
        )
    except Exception as e:
        logger.exception(f"Error evaluating test case {test_case.id}")
        return TestResult(
            test_case=test_case,
            passed=False,
            refused_by_guardrail=False,
            error_message=str(e),
            details="Runtime exception occurred."
        )

def run_evaluation_suite(file_path: str) -> TestReport:
    test_cases = load_test_cases(file_path)
    
    report = TestReport(total_cases=len(test_cases))
    
    total_safe = 0
    total_unsafe = 0
    safe_passed = 0
    unsafe_refused = 0
    
    for tc in test_cases:
        result = evaluate_single(tc)
        
        if result.passed:
            report.successful_cases += 1
        else:
            report.failed_cases += 1
            report.failed_details.append(result)
            
        if tc.expected_refusal:
            total_unsafe += 1
            if result.refused_by_guardrail:
                unsafe_refused += 1
        else:
            total_safe += 1
            if result.passed:
                safe_passed += 1
                
    if total_unsafe > 0:
        report.guardrail_coverage = (unsafe_refused / total_unsafe) * 100
    if total_safe > 0:
        report.retrieval_accuracy = (safe_passed / total_safe) * 100
        
    return report

def print_report(report: TestReport):
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📊 System Evaluation Report")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Total Test Cases: {report.total_cases}")
    print(f"  Passed: {report.successful_cases}")
    print(f"  Failed: {report.failed_cases}")
    print()
    print(f"  Guardrail Coverage: {report.guardrail_coverage:.2f}%")
    print(f"  Retrieval Accuracy: {report.retrieval_accuracy:.2f}%")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    if report.failed_details:
        print("\n❌ Failed Test Cases:")
        for res in report.failed_details:
            print(f"- {res.test_case.id}: {res.test_case.query}")
            if res.error_message:
                print(f"  Error: {res.error_message}")
            if res.details:
                print(f"  Details: {res.details}")
            print()
