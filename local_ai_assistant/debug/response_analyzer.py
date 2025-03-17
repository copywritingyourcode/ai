"""
Response analyzer module for debugging and analyzing responses.

This module provides functions to analyze and validate AI responses,
identify potential issues, and provide debugging information.
"""

import logging
import re
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import yaml

# Local imports
from local_ai_assistant.models.model_manager import ModelManager


# Logger for this module
logger = logging.getLogger(__name__)


class ResponseAnalyzer:
    """
    Analyzes AI responses for issues and provides debugging information.
    """
    
    def __init__(self, config_path: Union[str, Path], model_manager=None):
        """
        Initialize the response analyzer.
        
        Args:
            config_path: Path to the configuration file
            model_manager: Optional model manager for advanced analysis
        """
        self.config_path = Path(config_path)
        self.model_manager = model_manager
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Get debug configuration
        self.debug_config = self.config.get('debug', {})
        self.enabled = self.debug_config.get('enabled', True)
        self.issue_categories = self.debug_config.get('issue_categories', [])
        
        # Response analysis settings
        analysis_config = self.debug_config.get('response_analysis', {})
        self.max_issues = analysis_config.get('max_issues', 5)
        self.severity_threshold = analysis_config.get('severity_threshold', 'warning')
        
        logger.info(f"Response analyzer initialized, enabled: {self.enabled}")
    
    def analyze_response(self, query: str, response: str) -> List[Dict[str, Any]]:
        """
        Analyze an AI response for issues.
        
        Args:
            query: User query
            response: AI response
            
        Returns:
            List of issues found in the response, each issue is a dictionary
        """
        if not self.enabled:
            return []
        
        try:
            issues = []
            
            # Check for empty response
            if not response or response.strip() == "":
                issues.append({
                    'category': 'response_quality',
                    'severity': 'error',
                    'message': 'Empty response'
                })
                return issues
            
            # Check for very short response
            if len(response.split()) < 3:
                issues.append({
                    'category': 'response_quality',
                    'severity': 'warning',
                    'message': 'Very short response'
                })
            
            # Check for response that just repeats the question
            if query.lower() in response.lower():
                issues.append({
                    'category': 'response_quality',
                    'severity': 'info',
                    'message': 'Response contains the question'
                })
            
            # Check for incomplete code blocks
            code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', response, re.DOTALL)
            if '```' in response and len(code_blocks) == 0:
                issues.append({
                    'category': 'formatting_issue',
                    'severity': 'warning',
                    'message': 'Incomplete code block'
                })
            
            # Check for Python syntax errors in code blocks
            for block in code_blocks:
                if self._has_python_syntax_error(block):
                    issues.append({
                        'category': 'syntax_error',
                        'severity': 'error',
                        'message': 'Python syntax error in code block'
                    })
            
            # Check for contradictions or inconsistencies
            # This is a simplified version and could be improved
            if "but actually" in response.lower() or "however, that's not correct" in response.lower():
                issues.append({
                    'category': 'factual_accuracy',
                    'severity': 'warning',
                    'message': 'Possible self-contradiction in response'
                })
            
            # Limit the number of issues returned
            return issues[:self.max_issues]
            
        except Exception as e:
            # In case of errors, return them as issues
            logger.error(f"Error analyzing response: {str(e)}")
            return [{
                'category': 'analyzer_error',
                'severity': 'error',
                'message': f"Error analyzing response: {str(e)}"
            }]
    
    def _has_python_syntax_error(self, code: str) -> bool:
        """
        Check if Python code has syntax errors.
        
        Args:
            code: Python code to check
            
        Returns:
            True if the code has syntax errors, False otherwise
        """
        try:
            compile(code, '<string>', 'exec')
            return False
        except SyntaxError:
            return True
        except Exception:
            # Other exceptions aren't syntax errors
            return False
    
    def analyze_code_execution(self, code: str, output: str, error: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze the execution of code.
        
        Args:
            code: Code that was executed
            output: Output of the execution
            error: Error message, if any
            
        Returns:
            Analysis dictionary with issues and suggestions
        """
        analysis = {
            'issues': [],
            'suggestions': []
        }
        
        # Check for execution errors
        if error:
            analysis['issues'].append({
                'category': 'execution_error',
                'severity': 'error',
                'message': f"Execution error: {error}"
            })
            
            # Add suggestions based on error type
            if "NameError" in error:
                var_match = re.search(r"name '(\w+)' is not defined", error)
                if var_match:
                    var_name = var_match.group(1)
                    analysis['suggestions'].append({
                        'category': 'fix_suggestion',
                        'message': f"Define the variable '{var_name}' before using it"
                    })
            elif "ImportError" in error or "ModuleNotFoundError" in error:
                module_match = re.search(r"No module named '(\w+)'", error)
                if module_match:
                    module_name = module_match.group(1)
                    analysis['suggestions'].append({
                        'category': 'fix_suggestion',
                        'message': f"Make sure the module '{module_name}' is installed"
                    })
        
        # Check for potential performance issues
        if "Warning:" in output and ("slow" in output.lower() or "performance" in output.lower()):
            analysis['issues'].append({
                'category': 'performance_warning',
                'severity': 'warning',
                'message': "Performance warning detected in output"
            })
        
        return analysis
    
    def _extract_code_blocks(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract code blocks from markdown text.
        
        Args:
            text: Text to extract code blocks from
            
        Returns:
            List of code blocks with language and content
        """
        # Regex for markdown code blocks
        pattern = r'```([a-zA-Z0-9_]*)\n([\s\S]*?)```'
        
        code_blocks = []
        for match in re.finditer(pattern, text):
            lang = match.group(1).strip().lower() or "unknown"
            code = match.group(2)
            
            code_blocks.append({
                "language": lang,
                "code": code,
                "start_index": match.start(),
                "end_index": match.end()
            })
        
        return code_blocks
    
    def _analyze_code_blocks(self, code_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze code blocks for issues.
        
        Args:
            code_blocks: Code blocks to analyze
            
        Returns:
            List of issues found
        """
        issues = []
        
        for block in code_blocks:
            lang = block["language"]
            code = block["code"]
            
            # Skip analysis for unknown languages
            if lang == "unknown":
                continue
            
            # Analyze Python code
            if lang == "python":
                python_issues = self._analyze_python_code(code)
                if python_issues:
                    for issue in python_issues:
                        issue["code_block"] = block
                    issues.extend(python_issues)
            
            # Check for JavaScript code
            elif lang in ["javascript", "js"]:
                js_issues = self._analyze_javascript_code(code)
                if js_issues:
                    for issue in js_issues:
                        issue["code_block"] = block
                    issues.extend(js_issues)
            
            # Add more language analyzers as needed
        
        return issues
    
    def _analyze_python_code(self, code: str) -> List[Dict[str, Any]]:
        """
        Analyze Python code for issues.
        
        Args:
            code: Python code to analyze
            
        Returns:
            List of issues found
        """
        issues = []
        
        # Check for syntax errors
        try:
            # Static compile check
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            issues.append({
                "category": "syntax_error",
                "language": "python",
                "message": f"Syntax error: {str(e)}",
                "line": e.lineno,
                "severity": "error"
            })
        except Exception as e:
            issues.append({
                "category": "syntax_error",
                "language": "python",
                "message": f"Compilation error: {str(e)}",
                "severity": "error"
            })
        
        # Check for potential errors by scanning for patterns
        patterns = [
            {
                "regex": r'except\s*:',
                "message": "Bare except clause found. Consider catching specific exceptions.",
                "category": "code_quality",
                "severity": "warning"
            },
            {
                "regex": r'import\s+\*',
                "message": "Wildcard import (*) found. Consider importing specific names.",
                "category": "code_quality",
                "severity": "warning"
            },
            {
                "regex": r'^\s*print\s*\((?!\))',
                "message": "Python 3 style print function used. Ensure Python 3 compatibility.",
                "category": "compatibility",
                "severity": "info"
            },
            {
                "regex": r'os\.system\(|subprocess\.call\(',
                "message": "Executing shell commands. Ensure inputs are sanitized to prevent injection.",
                "category": "security",
                "severity": "warning"
            }
        ]
        
        for pattern in patterns:
            if re.search(pattern["regex"], code, re.MULTILINE):
                issues.append({
                    "category": pattern["category"],
                    "language": "python",
                    "message": pattern["message"],
                    "severity": pattern["severity"]
                })
        
        return issues
    
    def _analyze_javascript_code(self, code: str) -> List[Dict[str, Any]]:
        """
        Analyze JavaScript code for issues.
        
        Args:
            code: JavaScript code to analyze
            
        Returns:
            List of issues found
        """
        issues = []
        
        # Check for basic syntax markers
        patterns = [
            {
                "regex": r'var\s+',
                "message": "Using 'var' which has function scope. Consider using 'let' or 'const' for block scope.",
                "category": "code_quality",
                "severity": "warning"
            },
            {
                "regex": r'==(?!=)',
                "message": "Using loose equality (==) which performs type coercion. Consider using strict equality (===).",
                "category": "code_quality",
                "severity": "warning"
            },
            {
                "regex": r'eval\(',
                "message": "Using eval() which can be dangerous. Avoid if possible.",
                "category": "security",
                "severity": "error"
            },
            {
                "regex": r'setTimeout\(\s*"',
                "message": "Using setTimeout with a string argument is similar to eval(). Use a function instead.",
                "category": "security",
                "severity": "warning"
            }
        ]
        
        for pattern in patterns:
            if re.search(pattern["regex"], code):
                issues.append({
                    "category": pattern["category"],
                    "language": "javascript",
                    "message": pattern["message"],
                    "severity": pattern["severity"]
                })
        
        return issues
    
    def _might_contain_facts(self, text: str) -> bool:
        """
        Check if text likely contains factual claims worth verifying.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if text might contain facts, False otherwise
        """
        # Patterns that might indicate factual claims
        patterns = [
            r'\bin \d{4}\b',  # Years (e.g., "in 1989")
            r'\b\d+%\b',      # Percentages
            r'according to',  # Attribution
            r'studies show',  # Research claims
            r'research',      # Research mentions
            r'statistics',    # Statistics mentions
            r'data',          # Data mentions
            r'evidence',      # Evidence mentions
            r'facts?',        # Explicit fact mentions
            r'discovered',    # Discoveries
            r'invented',      # Inventions
            r'created by',    # Attributions of creation
            r'developed by',  # Attributions of development
            r'founded'        # Founding events
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _analyze_factual_claims(
        self, 
        user_query: str, 
        assistant_response: str
    ) -> List[Dict[str, Any]]:
        """
        Analyze factual claims in the response.
        
        This requires inference from an LLM to evaluate factuality.
        
        Args:
            user_query: Original user query
            assistant_response: Assistant's response
            
        Returns:
            List of potential factual issues
        """
        issues = []
        
        # Use LLM to analyze factual claims
        # The process here is not to verify every fact, but to look for
        # statements that seem potentially problematic
        
        factuality_prompt = f"""
Your job is to analyze this AI assistant response for factual errors or unsupported claims.
Only identify clear problems such as:
1. Incorrect dates, names, or statistics
2. Claims contradicted by the query
3. Statements that seem far-fetched or unlikely

USER QUERY: {user_query}

ASSISTANT RESPONSE: {assistant_response}

Format your response as a JSON array of issues. For each issue:
1. Identify the specific claim with a clear quote
2. Explain why it might be incorrect or needs verification
3. Rate your confidence from 0.5 (somewhat unsure) to 1.0 (very sure)

Only include claims you are at least somewhat confident are problematic. 
If no clear issues are found, return an empty array.

JSON RESULT:
"""
        
        try:
            # Use the model manager to check the response
            result = self.model_manager.generate_text(factuality_prompt)
            logger.debug("Generated factual analysis")
            
            # Parse JSON result
            try:
                # Ensure proper JSON format (fix common issues)
                result = result.strip()
                if not result.startswith('['):
                    # Find the start of JSON array
                    array_start = result.find('[')
                    if array_start >= 0:
                        result = result[array_start:]
                if not result.endswith(']'):
                    # Find the end of JSON array
                    array_end = result.rfind(']')
                    if array_end >= 0:
                        result = result[:array_end+1]
                
                # Parse JSON
                fact_issues = json.loads(result)
                
                # Process issues
                for issue in fact_issues:
                    if issue.get('confidence', 0) < 0.6:
                        continue  # Skip low confidence issues
                    
                    issues.append({
                        "category": "factual_accuracy",
                        "claim": issue.get('claim', ''),
                        "explanation": issue.get('explanation', ''),
                        "confidence": issue.get('confidence', 0.6),
                        "severity": "warning"
                    })
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse factual analysis result: {result}")
        except Exception as e:
            logger.error(f"Error analyzing factual claims: {str(e)}")
        
        return issues
    
    def _check_formatting(self, text: str) -> List[Dict[str, Any]]:
        """
        Check for formatting issues in the response.
        
        Args:
            text: Text to check
            
        Returns:
            List of formatting issues
        """
        issues = []
        
        # Check for unclosed code blocks
        code_block_starts = len(re.findall(r'```\w*\n', text))
        code_block_ends = len(re.findall(r'```', text)) - code_block_starts
        if code_block_starts > code_block_ends:
            issues.append({
                "category": "formatting_issue",
                "message": f"Unclosed code block(s) detected. Found {code_block_starts} opening blocks but only {code_block_ends} closing blocks.",
                "severity": "warning"
            })
        
        # Check for very long lines
        lines = text.split('\n')
        long_lines = []
        for i, line in enumerate(lines):
            if len(line) > 100:
                long_lines.append(i + 1)
        
        if long_lines and len(long_lines) > 5:
            issues.append({
                "category": "formatting_issue",
                "message": f"Multiple very long lines detected ({len(long_lines)} lines > 100 chars). This might affect readability.",
                "severity": "info",
                "lines": long_lines[:5]  # Include first few line numbers
            })
        
        # Check for mismatched parentheses, braces, brackets
        opening = sum(text.count(c) for c in '([{')
        closing = sum(text.count(c) for c in ')]}')
        if opening != closing:
            issues.append({
                "category": "formatting_issue",
                "message": f"Mismatched parentheses/braces/brackets. Found {opening} opening symbols and {closing} closing symbols.",
                "severity": "warning"
            })
        
        return issues
    
    def _generate_recommendations(
        self, 
        issues: List[Dict[str, Any]], 
        user_query: str, 
        assistant_response: str
    ) -> List[str]:
        """
        Generate recommendations to fix identified issues.
        
        Args:
            issues: List of identified issues
            user_query: Original user query
            assistant_response: Assistant's response
            
        Returns:
            List of recommendations
        """
        # Group issues by category
        grouped_issues = {}
        for issue in issues:
            category = issue.get("category", "unknown")
            if category not in grouped_issues:
                grouped_issues[category] = []
            grouped_issues[category].append(issue)
        
        # Generate recommendations
        recommendations = []
        
        # Handle syntax errors
        if "syntax_error" in grouped_issues:
            for issue in grouped_issues["syntax_error"]:
                if issue.get("language") == "python":
                    recommendations.append(
                        f"Fix Python syntax error: {issue.get('message', '')}"
                    )
                else:
                    recommendations.append(
                        f"Fix syntax error in {issue.get('language', 'code')}: {issue.get('message', '')}"
                    )
        
        # Handle code quality issues
        if "code_quality" in grouped_issues:
            quality_issues = grouped_issues["code_quality"]
            if len(quality_issues) <= 3:
                # For a few issues, be specific
                for issue in quality_issues:
                    recommendations.append(
                        f"Improve code quality: {issue.get('message', '')}"
                    )
            else:
                # For many issues, group the recommendation
                recommendations.append(
                    f"Review code for quality issues: found {len(quality_issues)} potential improvements"
                )
        
        # Handle security issues
        if "security" in grouped_issues:
            for issue in grouped_issues["security"]:
                recommendations.append(
                    f"Fix security issue: {issue.get('message', '')}"
                )
        
        # Handle factual accuracy
        if "factual_accuracy" in grouped_issues:
            fact_issues = grouped_issues["factual_accuracy"]
            if len(fact_issues) == 1:
                issue = fact_issues[0]
                recommendations.append(
                    f"Verify factual claim: \"{issue.get('claim', '')}\" - {issue.get('explanation', '')}"
                )
            else:
                # Summarize multiple factual issues
                recommendations.append(
                    f"Review response for factual accuracy: found {len(fact_issues)} questionable claims"
                )
        
        # Handle formatting issues
        if "formatting_issue" in grouped_issues:
            format_issues = grouped_issues["formatting_issue"]
            for issue in format_issues:
                if "code block" in issue.get("message", ""):
                    recommendations.append("Ensure all code blocks are properly closed with ```")
                else:
                    recommendations.append(
                        f"Fix formatting: {issue.get('message', '')}"
                    )
        
        # Use LLM to enhance recommendations if we have very few
        if len(recommendations) <= 2:
            try:
                # Use a more compact summary of issues
                issue_summary = "\n".join([
                    f"- {issue.get('category', 'issue')}: {issue.get('message', '')}"
                    for issue in issues
                ])
                
                improvement_prompt = f"""
I need to improve this AI assistant response. These issues were detected:

{issue_summary}

Please provide 2-3 specific suggestions to fix these issues. Be precise and actionable.

USER QUERY: {user_query}

ASSISTANT RESPONSE: {assistant_response}

IMPROVEMENT SUGGESTIONS:
"""
                
                result = self.model_manager.generate_text(improvement_prompt)
                
                # Extract suggestions (assuming line-by-line format)
                additional_suggestions = [
                    line.strip() for line in result.split('\n')
                    if line.strip() and not line.strip().startswith('-')
                ]
                
                # Add non-duplicate suggestions
                for suggestion in additional_suggestions:
                    if not any(self._is_similar_recommendation(suggestion, rec) for rec in recommendations):
                        recommendations.append(suggestion)
                
            except Exception as e:
                logger.error(f"Error generating additional recommendations: {str(e)}")
        
        return recommendations
    
    def _is_similar_recommendation(self, rec1: str, rec2: str) -> bool:
        """
        Check if two recommendations are similar.
        
        Args:
            rec1: First recommendation
            rec2: Second recommendation
            
        Returns:
            True if recommendations are similar, False otherwise
        """
        # Simple check for significant word overlap
        words1 = set(re.findall(r'\b\w+\b', rec1.lower()))
        words2 = set(re.findall(r'\b\w+\b', rec2.lower()))
        
        if not words1 or not words2:
            return False
        
        # If one is a subset of the other, or there's significant overlap
        overlap = len(words1.intersection(words2))
        smaller_set_size = min(len(words1), len(words2))
        
        return overlap / smaller_set_size > 0.7 