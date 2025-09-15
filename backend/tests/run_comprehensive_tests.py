"""
Comprehensive test runner for API documentation and integration testing.
"""

import asyncio
import subprocess
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import pytest


class ComprehensiveTestRunner:
    """Runner for comprehensive API and integration tests"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
    
    def run_test_suite(self, test_file: str, description: str) -> Dict[str, Any]:
        """Run a specific test suite and capture results"""
        print(f"\n{'='*60}")
        print(f"Running {description}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        # Run pytest with detailed output
        cmd = [
            sys.executable, "-m", "pytest",
            test_file,
            "-v",
            "--tb=short",
            "--json-report",
            f"--json-report-file=test_results_{test_file.replace('/', '_').replace('.py', '')}.json",
            "--durations=10"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Parse JSON report if available
            json_file = f"test_results_{test_file.replace('/', '_').replace('.py', '')}.json"
            json_path = Path(__file__).parent.parent / json_file
            
            test_data = {}
            if json_path.exists():
                try:
                    with open(json_path, 'r') as f:
                        test_data = json.load(f)
                except Exception as e:
                    print(f"Warning: Could not parse JSON report: {e}")
            
            return {
                "description": description,
                "file": test_file,
                "return_code": result.returncode,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "test_data": test_data,
                "success": result.returncode == 0
            }
            
        except Exception as e:
            return {
                "description": description,
                "file": test_file,
                "return_code": -1,
                "duration": 0,
                "stdout": "",
                "stderr": str(e),
                "test_data": {},
                "success": False,
                "error": str(e)
            }
    
    def generate_api_documentation(self) -> Dict[str, Any]:
        """Generate API documentation using FastAPI's built-in docs"""
        print(f"\n{'='*60}")
        print("Generating API Documentation")
        print(f"{'='*60}")
        
        try:
            # Start the FastAPI server temporarily to generate docs
            from app.main import app
            from fastapi.openapi.utils import get_openapi
            
            # Generate OpenAPI schema
            openapi_schema = app.openapi()
            
            # Save OpenAPI schema to file
            docs_path = Path(__file__).parent.parent / "api_documentation.json"
            with open(docs_path, 'w') as f:
                json.dump(openapi_schema, f, indent=2)
            
            # Count endpoints
            paths = openapi_schema.get("paths", {})
            endpoint_count = sum(len(methods) for methods in paths.values())
            
            return {
                "success": True,
                "schema_file": str(docs_path),
                "endpoint_count": endpoint_count,
                "paths_count": len(paths),
                "tags": [tag["name"] for tag in openapi_schema.get("tags", [])],
                "version": openapi_schema.get("info", {}).get("version", "unknown")
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all comprehensive tests"""
        self.start_time = time.time()
        
        print("Starting Comprehensive API Testing Suite")
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Generate API documentation first
        doc_results = self.generate_api_documentation()
        self.test_results["api_documentation"] = doc_results
        
        # Define test suites to run
        test_suites = [
            {
                "file": "tests/test_api_comprehensive.py",
                "description": "Comprehensive API Integration Tests"
            },
            {
                "file": "tests/test_integration_auth.py", 
                "description": "Authentication Integration Tests"
            },
            {
                "file": "tests/test_integration_projects.py",
                "description": "Project Management Integration Tests"
            },
            {
                "file": "tests/test_integration_deployments.py",
                "description": "Deployment Pipeline Integration Tests"
            },
            {
                "file": "tests/test_database_migrations_comprehensive.py",
                "description": "Database Migration and Rollback Tests"
            },
            {
                "file": "tests/test_security_comprehensive.py",
                "description": "Security and Authentication Tests"
            },
            {
                "file": "tests/test_performance_api.py",
                "description": "API Performance Tests"
            },
            {
                "file": "tests/test_performance_database.py",
                "description": "Database Performance Tests"
            }
        ]
        
        # Run each test suite
        for suite in test_suites:
            suite_key = suite["file"].replace("tests/", "").replace(".py", "")
            self.test_results[suite_key] = self.run_test_suite(
                suite["file"], 
                suite["description"]
            )
        
        self.end_time = time.time()
        
        # Generate summary report
        return self.generate_summary_report()
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive summary report"""
        total_duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        # Count successes and failures
        test_suites = [k for k in self.test_results.keys() if k != "api_documentation"]
        successful_suites = [
            k for k in test_suites 
            if self.test_results[k].get("success", False)
        ]
        failed_suites = [
            k for k in test_suites 
            if not self.test_results[k].get("success", False)
        ]
        
        # Extract test counts from JSON reports
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        
        for suite_key in test_suites:
            suite_data = self.test_results[suite_key]
            test_data = suite_data.get("test_data", {})
            
            if "summary" in test_data:
                summary = test_data["summary"]
                total_tests += summary.get("total", 0)
                passed_tests += summary.get("passed", 0)
                failed_tests += summary.get("failed", 0)
                skipped_tests += summary.get("skipped", 0)
        
        summary = {
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "total_duration": round(total_duration, 2),
            "api_documentation": self.test_results.get("api_documentation", {}),
            "test_suites": {
                "total": len(test_suites),
                "successful": len(successful_suites),
                "failed": len(failed_suites),
                "success_rate": len(successful_suites) / len(test_suites) * 100 if test_suites else 0
            },
            "test_cases": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests,
                "pass_rate": passed_tests / total_tests * 100 if total_tests > 0 else 0
            },
            "suite_details": {
                suite_key: {
                    "success": suite_data.get("success", False),
                    "duration": suite_data.get("duration", 0),
                    "description": suite_data.get("description", ""),
                    "test_count": suite_data.get("test_data", {}).get("summary", {}).get("total", 0)
                }
                for suite_key, suite_data in self.test_results.items()
                if suite_key != "api_documentation"
            },
            "failed_suites": failed_suites,
            "recommendations": self.generate_recommendations()
        }
        
        return summary
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check API documentation
        api_doc = self.test_results.get("api_documentation", {})
        if not api_doc.get("success", False):
            recommendations.append("Fix API documentation generation issues")
        
        # Check test suite failures
        failed_suites = [
            k for k in self.test_results.keys() 
            if k != "api_documentation" and not self.test_results[k].get("success", False)
        ]
        
        if failed_suites:
            recommendations.append(f"Address failures in test suites: {', '.join(failed_suites)}")
        
        # Check security tests specifically
        if "test_security_comprehensive" in failed_suites:
            recommendations.append("Critical: Address security test failures immediately")
        
        # Check performance
        perf_suites = [k for k in self.test_results.keys() if "performance" in k]
        failed_perf = [k for k in perf_suites if not self.test_results[k].get("success", False)]
        
        if failed_perf:
            recommendations.append("Investigate performance issues and optimize slow endpoints")
        
        # Check migration tests
        if "test_database_migrations_comprehensive" in failed_suites:
            recommendations.append("Fix database migration issues before deployment")
        
        if not recommendations:
            recommendations.append("All tests passed! Consider adding more edge case tests.")
        
        return recommendations
    
    def save_report(self, summary: Dict[str, Any]) -> str:
        """Save comprehensive report to file"""
        report_path = Path(__file__).parent.parent / "comprehensive_test_report.json"
        
        with open(report_path, 'w') as f:
            json.dump({
                "summary": summary,
                "detailed_results": self.test_results
            }, f, indent=2)
        
        return str(report_path)
    
    def print_summary(self, summary: Dict[str, Any]):
        """Print formatted summary to console"""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE TEST REPORT SUMMARY")
        print(f"{'='*80}")
        
        print(f"Timestamp: {summary['timestamp']}")
        print(f"Total Duration: {summary['total_duration']} seconds")
        
        print(f"\nAPI Documentation:")
        api_doc = summary['api_documentation']
        if api_doc.get('success'):
            print(f"  ✓ Generated successfully")
            print(f"  ✓ {api_doc.get('endpoint_count', 0)} endpoints documented")
            print(f"  ✓ {api_doc.get('paths_count', 0)} API paths")
        else:
            print(f"  ✗ Generation failed: {api_doc.get('error', 'Unknown error')}")
        
        print(f"\nTest Suites:")
        suites = summary['test_suites']
        print(f"  Total: {suites['total']}")
        print(f"  Successful: {suites['successful']}")
        print(f"  Failed: {suites['failed']}")
        print(f"  Success Rate: {suites['success_rate']:.1f}%")
        
        print(f"\nTest Cases:")
        cases = summary['test_cases']
        print(f"  Total: {cases['total']}")
        print(f"  Passed: {cases['passed']}")
        print(f"  Failed: {cases['failed']}")
        print(f"  Skipped: {cases['skipped']}")
        print(f"  Pass Rate: {cases['pass_rate']:.1f}%")
        
        if summary['failed_suites']:
            print(f"\nFailed Suites:")
            for suite in summary['failed_suites']:
                print(f"  ✗ {suite}")
        
        print(f"\nRecommendations:")
        for rec in summary['recommendations']:
            print(f"  • {rec}")
        
        print(f"\n{'='*80}")


def main():
    """Main entry point for comprehensive testing"""
    runner = ComprehensiveTestRunner()
    
    try:
        summary = runner.run_all_tests()
        report_path = runner.save_report(summary)
        
        runner.print_summary(summary)
        
        print(f"\nDetailed report saved to: {report_path}")
        
        # Exit with appropriate code
        if summary['test_suites']['failed'] > 0:
            print("\nSome tests failed. Please review the results.")
            sys.exit(1)
        else:
            print("\nAll tests passed successfully!")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\nTest run interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\nError running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()