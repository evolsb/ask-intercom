"""
Claude integration tools for log analysis and debugging.
"""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

from .logging import ANALYTICS_DIR, LOGS_DIR, SESSIONS_DIR, ERRORS_DIR


class LogAnalyzer:
    """Tools for Claude to analyze logs and debug issues."""
    
    def __init__(self):
        self.analytics_dir = ANALYTICS_DIR
        self.logs_dir = LOGS_DIR
        self.sessions_dir = SESSIONS_DIR
        self.errors_dir = ERRORS_DIR
    
    def get_recent_errors(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get errors from the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        errors = []
        
        # Check error logs
        for log_file in self.logs_dir.glob("errors-*.jsonl"):
            if log_file.stat().st_mtime < cutoff_time.timestamp():
                continue
                
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            entry_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                            if entry_time >= cutoff_time:
                                errors.append(entry)
                        except (json.JSONDecodeError, KeyError):
                            continue
            except Exception:
                continue
        
        return sorted(errors, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific session."""
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Also get logs for this session
            session_logs = self._get_logs_for_session(session_id)
            session_data['logs'] = session_logs
            
            return session_data
        except Exception:
            return None
    
    def _get_logs_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all log entries for a specific session."""
        logs = []
        
        # Search through all log files
        for log_file in self.logs_dir.glob("*.jsonl"):
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            if entry.get('session_id') == session_id:
                                logs.append(entry)
                        except json.JSONDecodeError:
                            continue
            except Exception:
                continue
        
        return sorted(logs, key=lambda x: x.get('timestamp', ''))
    def analyze_error_patterns(self, days: int = 1) -> Dict[str, Any]:
        """Analyze error patterns over the last N days."""
        cutoff_time = datetime.now() - timedelta(days=days)
        errors_by_category = {}
        errors_by_hour = {}
        total_errors = 0
        
        # Collect all errors
        for log_file in self.logs_dir.glob("errors-*.jsonl"):
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            entry_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                            
                            if entry_time >= cutoff_time:
                                total_errors += 1
                                
                                # Categorize errors
                                error_data = entry.get('data', {})
                                category = error_data.get('error_type', 'unknown')
                                
                                if category not in errors_by_category:
                                    errors_by_category[category] = 0
                                errors_by_category[category] += 1
                                
                                # Track by hour
                                hour_key = entry_time.strftime('%Y-%m-%d %H:00')
                                if hour_key not in errors_by_hour:
                                    errors_by_hour[hour_key] = 0
                                errors_by_hour[hour_key] += 1
                                
                        except (json.JSONDecodeError, KeyError):
                            continue
            except Exception:
                continue
        
        return {
            'total_errors': total_errors,
            'errors_by_category': errors_by_category,
            'errors_by_hour': errors_by_hour,
            'analysis_period_days': days
        }
    
    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics from the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        query_times = []
        total_queries = 0
        successful_queries = 0
        
        # Look through backend logs for query completions
        for log_file in self.logs_dir.glob("backend-*.jsonl"):
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            entry_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                            
                            if entry_time >= cutoff_time:
                                if entry.get('event') == 'query_complete':
                                    total_queries += 1
                                    successful_queries += 1
                                    
                                    duration = entry.get('data', {}).get('duration_ms', 0)
                                    if duration > 0:
                                        query_times.append(duration)
                                
                                elif entry.get('event') == 'query_start':
                                    total_queries += 1
                                    
                        except (json.JSONDecodeError, KeyError):
                            continue
            except Exception:
                continue
        
        # Calculate statistics
        if query_times:
            avg_time = sum(query_times) / len(query_times)
            median_time = sorted(query_times)[len(query_times) // 2]
            max_time = max(query_times)
            min_time = min(query_times)
        else:
            avg_time = median_time = max_time = min_time = 0
        
        success_rate = successful_queries / max(total_queries, 1)
        
        return {
            'total_queries': total_queries,
            'successful_queries': successful_queries,
            'success_rate': success_rate,
            'avg_response_time_ms': avg_time,
            'median_response_time_ms': median_time,
            'max_response_time_ms': max_time,
            'min_response_time_ms': min_time,
            'analysis_period_hours': hours
        }
    
    def find_sessions_with_errors(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Find all sessions that had errors in the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        error_sessions = set()
        
        # Find sessions with errors
        for log_file in self.logs_dir.glob("*.jsonl"):
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            entry_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                            
                            if entry_time >= cutoff_time and entry.get('level') == 'ERROR':
                                session_id = entry.get('session_id')
                                if session_id:
                                    error_sessions.add(session_id)
                                    
                        except (json.JSONDecodeError, KeyError):
                            continue
            except Exception:
                continue
        
        # Get session details
        sessions_with_errors = []
        for session_id in error_sessions:
            session_info = self.get_session_info(session_id)
            if session_info:
                sessions_with_errors.append({
                    'session_id': session_id,
                    'start_time': session_info.get('start_time'),
                    'queries': len(session_info.get('queries', [])),
                    'errors': len([log for log in session_info.get('logs', []) if log.get('level') == 'ERROR'])
                })
        
        return sorted(sessions_with_errors, key=lambda x: x.get('start_time', ''), reverse=True)
    
    def search_logs(self, query: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Search logs for specific text or patterns."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        matches = []
        
        # Search through all log files
        for log_file in self.logs_dir.glob("*.jsonl"):
            try:
                with open(log_file, 'r') as f:
                    for line_num, line in enumerate(f, 1):
                        try:
                            entry = json.loads(line.strip())
                            entry_time = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                            
                            if entry_time >= cutoff_time:
                                # Search in message and data
                                line_text = line.lower()
                                if query.lower() in line_text:
                                    matches.append({
                                        'file': log_file.name,
                                        'line_number': line_num,
                                        'timestamp': entry['timestamp'],
                                        'level': entry.get('level'),
                                        'message': entry.get('message'),
                                        'session_id': entry.get('session_id'),
                                        'event': entry.get('event'),
                                        'match_context': line.strip()
                                    })
                                    
                        except (json.JSONDecodeError, KeyError):
                            continue
            except Exception:
                continue
        
        return sorted(matches, key=lambda x: x.get('timestamp', ''), reverse=True)[:50]  # Limit results
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get a comprehensive system summary for debugging."""
        # Get recent metrics
        recent_errors = self.get_recent_errors(hours=1)
        performance = self.get_performance_metrics(hours=24)
        error_patterns = self.analyze_error_patterns(days=1)
        error_sessions = self.find_sessions_with_errors(hours=24)
        
        # Check if analytics directory exists and is writable
        analytics_status = {
            'directory_exists': self.analytics_dir.exists(),
            'directory_writable': self.analytics_dir.exists() and self.analytics_dir.is_dir(),
            'log_files_count': len(list(self.logs_dir.glob("*.jsonl"))) if self.logs_dir.exists() else 0,
            'session_files_count': len(list(self.sessions_dir.glob("*.json"))) if self.sessions_dir.exists() else 0
        }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'analytics_status': analytics_status,
            'recent_errors_count': len(recent_errors),
            'recent_errors': recent_errors[:5],  # Latest 5 errors
            'performance_24h': performance,
            'error_patterns_24h': error_patterns,
            'sessions_with_errors_24h': len(error_sessions),
            'error_sessions': error_sessions[:5]  # Top 5 error sessions
        }


# Global log analyzer instance for Claude to use
log_analyzer = LogAnalyzer()


def analyze_recent_errors(hours: int = 1) -> str:
    """Claude-friendly function to analyze recent errors."""
    errors = log_analyzer.get_recent_errors(hours)
    
    if not errors:
        return f"No errors found in the last {hours} hour(s)."
    
    summary = f"Found {len(errors)} error(s) in the last {hours} hour(s):\n\n"
    
    for i, error in enumerate(errors[:10], 1):  # Show top 10
        session_id = error.get('session_id', 'unknown')
        message = error.get('message', 'No message')
        timestamp = error.get('timestamp', 'unknown')
        event = error.get('event', 'unknown')
        
        summary += f"{i}. [{timestamp}] Session {session_id}\n"
        summary += f"   Event: {event}\n"
        summary += f"   Message: {message}\n"
        
        # Add error data if available
        error_data = error.get('data', {})
        if error_data:
            for key, value in error_data.items():
                if key != 'stack_trace':  # Skip long stack traces in summary
                    summary += f"   {key}: {value}\n"
        
        summary += "\n"
    
    return summary


def debug_session(session_id: str) -> str:
    """Claude-friendly function to debug a specific session."""
    session_info = log_analyzer.get_session_info(session_id)
    
    if not session_info:
        return f"Session {session_id} not found."
    
    summary = f"Session {session_id} Debug Information:\n\n"
    summary += f"Start Time: {session_info.get('start_time', 'unknown')}\n"
    summary += f"Last Activity: {session_info.get('last_activity', 'unknown')}\n"
    summary += f"Queries: {len(session_info.get('queries', []))}\n"
    summary += f"Errors: {len(session_info.get('errors', []))}\n\n"
    
    # Show queries
    queries = session_info.get('queries', [])
    if queries:
        summary += "Queries:\n"
        for i, query in enumerate(queries, 1):
            summary += f"{i}. [{query.get('timestamp', 'unknown')}] {query.get('query', 'unknown')[:100]}...\n"
            summary += f"   Duration: {query.get('duration_ms', 0)}ms\n"
            summary += f"   Conversations: {query.get('result', {}).get('conversation_count', 0)}\n\n"
    
    # Show recent logs
    logs = session_info.get('logs', [])
    if logs:
        summary += "Recent Log Entries:\n"
        for log in logs[-10:]:  # Last 10 log entries
            level = log.get('level', 'INFO')
            timestamp = log.get('timestamp', 'unknown')
            message = log.get('message', 'No message')
            event = log.get('event', 'general')
            
            summary += f"[{timestamp}] {level} - {event}: {message}\n"
    
    return summary


def get_performance_summary() -> str:
    """Claude-friendly function to get performance summary."""
    metrics = log_analyzer.get_performance_metrics(hours=24)
    
    summary = "Performance Summary (Last 24 hours):\n\n"
    summary += f"Total Queries: {metrics['total_queries']}\n"
    summary += f"Successful Queries: {metrics['successful_queries']}\n"
    summary += f"Success Rate: {metrics['success_rate']:.2%}\n"
    summary += f"Average Response Time: {metrics['avg_response_time_ms']:.0f}ms\n"
    summary += f"Median Response Time: {metrics['median_response_time_ms']:.0f}ms\n"
    summary += f"Max Response Time: {metrics['max_response_time_ms']:.0f}ms\n"
    
    if metrics['avg_response_time_ms'] > 10000:
        summary += "\n⚠️  Average response time is high (>10s). Consider optimization.\n"
    
    if metrics['success_rate'] < 0.9:
        summary += f"\n⚠️  Success rate is low ({metrics['success_rate']:.2%}). Check error logs.\n"
    
    return summary


def search_for_issues(query: str) -> str:
    """Claude-friendly function to search for specific issues in logs."""
    matches = log_analyzer.search_logs(query, hours=24)
    
    if not matches:
        return f"No matches found for '{query}' in the last 24 hours."
    
    summary = f"Found {len(matches)} match(es) for '{query}':\n\n"
    
    for i, match in enumerate(matches[:10], 1):
        summary += f"{i}. [{match['timestamp']}] {match['level']} - {match['event']}\n"
        summary += f"   Session: {match.get('session_id', 'unknown')}\n"
        summary += f"   Message: {match.get('message', 'No message')}\n"
        summary += f"   File: {match['file']}:{match['line_number']}\n\n"
    
    return summary