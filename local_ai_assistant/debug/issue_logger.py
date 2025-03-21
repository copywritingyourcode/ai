"""
Issue logger module for tracking and logging AI response issues.

This module provides functions to record and analyze issues found
during response analysis and code execution.
"""

import logging
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import yaml

# Logger for this module
logger = logging.getLogger(__name__)


class IssueLogger:
    """
    Records and analyzes issues found in AI responses.
    
    Provides methods to log issues, generate reports, and track
    patterns over time to identify recurring problems.
    """
    
    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize the issue logger.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        
        # Load configuration
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Extract debug settings
        debug_config = self.config['debug']
        
        # Log file path
        log_file = debug_config.get('log_file', 'debug_issues.log')
        self.log_dir = Path(self.config['system']['log_dir'])
        self.log_file_path = self.log_dir / log_file
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Track issues in memory (recent issues)
        self.recent_issues: List[Dict[str, Any]] = []
        self.max_recent_issues = 100  # Keep only the 100 most recent issues
        
        # Issue categories from config
        self.issue_categories = debug_config.get('issue_categories', [])
        
        # Load existing issues if log file exists
        self._load_existing_issues()
        
        logger.info(f"Issue logger initialized with log file: {self.log_file_path}")
    
    def _load_existing_issues(self):
        """Load existing issues from log file."""
        if not self.log_file_path.exists():
            return
        
        try:
            with open(self.log_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        issue = json.loads(line)
                        self.recent_issues.append(issue)
                        
                        # Keep only the most recent issues
                        if len(self.recent_issues) > self.max_recent_issues:
                            self.recent_issues.pop(0)
                    except json.JSONDecodeError:
                        # Skip invalid lines
                        continue
            
            logger.debug(f"Loaded {len(self.recent_issues)} recent issues from log file")
            
        except Exception as e:
            logger.error(f"Error loading existing issues: {str(e)}")
    
    def log_issue(
        self,
        category: str,
        message: str,
        severity: str = "info",
        details: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log an issue with details.
        
        Args:
            category: Issue category
            message: Issue description
            severity: Issue severity (info, warning, error)
            details: Additional issue details
            context: Context information (user query, response, etc.)
            
        Returns:
            Issue ID
        """
        # Generate timestamp and issue ID
        timestamp = time.time()
        issue_id = f"issue_{int(timestamp)}_{hash(message) % 10000}"
        
        # Create issue record
        issue = {
            'id': issue_id,
            'timestamp': timestamp,
            'category': category,
            'message': message,
            'severity': severity
        }
        
        # Add optional fields
        if details:
            issue['details'] = details
        
        if context:
            issue['context'] = context
        
        # Add to recent issues
        self.recent_issues.append(issue)
        
        # Keep only the most recent issues
        if len(self.recent_issues) > self.max_recent_issues:
            self.recent_issues.pop(0)
        
        # Log to file
        try:
            with open(self.log_file_path, 'a') as f:
                f.write(json.dumps(issue) + '\n')
        except Exception as e:
            logger.error(f"Error writing issue to log file: {str(e)}")
        
        # Log to application log
        log_level = {
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR
        }.get(severity.lower(), logging.INFO)
        
        logger.log(log_level, f"Issue logged - {category}: {message} (ID: {issue_id})")
        
        return issue_id
    
    def log_analysis_results(
        self, 
        analysis_results: Dict[str, Any],
        user_query: str,
        assistant_response: str
    ) -> List[str]:
        """
        Log results from response analysis.
        
        Args:
            analysis_results: Analysis results
            user_query: User query
            assistant_response: Assistant response
            
        Returns:
            List of issue IDs
        """
        if not analysis_results.get('enabled', False) or not analysis_results.get('issues_found', False):
            return []
        
        issues = analysis_results.get('issues', [])
        issue_ids = []
        
        for issue in issues:
            category = issue.get('category', 'unknown')
            message = issue.get('message', 'No message')
            severity = issue.get('severity', 'info')
            
            # Create context with minimal information
            context = {
                'user_query': user_query[:100] + '...' if len(user_query) > 100 else user_query,
                'response_excerpt': assistant_response[:100] + '...' if len(assistant_response) > 100 else assistant_response
            }
            
            # Log the issue
            issue_id = self.log_issue(
                category=category,
                message=message,
                severity=severity,
                details=issue,
                context=context
            )
            
            issue_ids.append(issue_id)
        
        return issue_ids
    
    def log_code_execution(
        self, 
        execution_results: Dict[str, Any],
        code: str,
        language: str
    ) -> Optional[str]:
        """
        Log code execution results.
        
        Args:
            execution_results: Code execution results
            code: Executed code
            language: Code language
            
        Returns:
            Issue ID if execution failed, None otherwise
        """
        if execution_results.get('success', False):
            return None
        
        # Extract error information
        error = execution_results.get('error', 'Unknown error')
        output = execution_results.get('output', '')
        execution_time = execution_results.get('execution_time', 0)
        
        # Create issue details
        details = {
            'language': language,
            'error': error,
            'output': output,
            'execution_time': execution_time
        }
        
        # Create context with code
        context = {
            'code_excerpt': code[:100] + '...' if len(code) > 100 else code
        }
        
        # Log the issue
        issue_id = self.log_issue(
            category='code_execution_error',
            message=f"Code execution failed: {error[:100]}",
            severity='warning',
            details=details,
            context=context
        )
        
        return issue_id
    
    def get_recent_issues(
        self, 
        limit: int = 10,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent issues from memory.
        
        Args:
            limit: Maximum number of issues to return
            category: Filter by category
            
        Returns:
            List of recent issues
        """
        # Filter by category if specified
        if category:
            filtered_issues = [issue for issue in self.recent_issues if issue.get('category') == category]
        else:
            filtered_issues = self.recent_issues
        
        # Return most recent issues (already sorted by timestamp)
        return filtered_issues[-limit:]
    
    def get_issue_by_id(self, issue_id: str) -> Optional[Dict[str, Any]]:
        """
        Get issue by ID from memory.
        
        Args:
            issue_id: Issue ID
            
        Returns:
            Issue dict if found, None otherwise
        """
        for issue in self.recent_issues:
            if issue.get('id') == issue_id:
                return issue
        
        return None
    
    def get_issue_stats(self) -> Dict[str, Any]:
        """
        Get issue statistics.
        
        Returns:
            Dictionary of issue statistics
        """
        stats = {
            'total_issues': len(self.recent_issues),
            'by_category': {},
            'by_severity': {
                'info': 0,
                'warning': 0,
                'error': 0
            }
        }
        
        # Count issues by category and severity
        for issue in self.recent_issues:
            category = issue.get('category', 'unknown')
            severity = issue.get('severity', 'info')
            
            # Count by category
            if category not in stats['by_category']:
                stats['by_category'][category] = 0
            stats['by_category'][category] += 1
            
            # Count by severity
            if severity in stats['by_severity']:
                stats['by_severity'][severity] += 1
        
        return stats
    
    def get_recurring_issues(self) -> List[Dict[str, Any]]:
        """
        Identify recurring issue patterns.
        
        Returns:
            List of recurring issue patterns with counts
        """
        # Group similar issues by comparing messages
        issue_groups = {}
        
        for issue in self.recent_issues:
            category = issue.get('category', 'unknown')
            message = issue.get('message', '')
            
            # Create a group key based on category and simplified message
            # This is a simple approach - for production you might want more sophisticated grouping
            simplified_message = ' '.join(message.split()[:5])  # First 5 words
            group_key = f"{category}:{simplified_message}"
            
            if group_key not in issue_groups:
                issue_groups[group_key] = {
                    'category': category,
                    'pattern': simplified_message,
                    'count': 0,
                    'examples': []
                }
            
            # Increment count and add example
            issue_groups[group_key]['count'] += 1
            
            # Add example if we have fewer than 3
            if len(issue_groups[group_key]['examples']) < 3:
                issue_groups[group_key]['examples'].append({
                    'id': issue.get('id', ''),
                    'message': message,
                    'timestamp': issue.get('timestamp', 0)
                })
        
        # Convert to list and sort by count (highest first)
        recurring_issues = list(issue_groups.values())
        recurring_issues.sort(key=lambda x: x['count'], reverse=True)
        
        # Only return issues that occur more than once
        return [issue for issue in recurring_issues if issue['count'] > 1]
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive issue report.
        
        Returns:
            Report dictionary
        """
        report = {
            'timestamp': time.time(),
            'stats': self.get_issue_stats(),
            'recurring_issues': self.get_recurring_issues(),
            'recent_issues': self.get_recent_issues(limit=10),
            'categories': self.issue_categories
        }
        
        return report 