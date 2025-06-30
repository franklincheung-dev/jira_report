"""
Persistent storage for sprint reports and other application data.
"""

import os
import json
from pathlib import Path
import datetime
from typing import Dict, Any, List

class ReportStorage:
    """
    Handles persistent storage for sprint reports and other data.
    """
    
    def __init__(self, storage_dir: str = None):
        """
        Initialize the storage with a directory path.
        
        Args:
            storage_dir: Directory path for storing report data. If None, 
                         uses a default 'reports' directory in the app folder.
        """
        if storage_dir is None:
            # Use default path
            self.storage_dir = Path(__file__).parent.parent / 'app' / 'reports'
        else:
            self.storage_dir = Path(storage_dir)
        
        # Create directory if it doesn't exist
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Cache for in-memory access
        self.reports_cache = {}
    
    def save_sprint_report(self, session_id: str, report_data: Dict[str, Any]) -> str:
        """
        Save a sprint report to persistent storage.
        
        Args:
            session_id: Unique identifier for the user session
            report_data: Report data to be saved
            
        Returns:
            The unique ID for the saved report
        """
        # Generate a report ID
        report_id = report_data.get('archive_id', f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
        
        # Create session directory if it doesn't exist
        session_dir = self.storage_dir / session_id
        os.makedirs(session_dir, exist_ok=True)
        
        # Save report to file
        report_path = session_dir / f"{report_id}.json"
        
        # Add timestamp if not present
        if 'date_archived' not in report_data:
            report_data['date_archived'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        # Update cache
        if session_id not in self.reports_cache:
            self.reports_cache[session_id] = {}
        self.reports_cache[session_id][report_id] = report_data
        
        return report_id
    
    def get_report(self, session_id: str, report_id: str) -> Dict[str, Any]:
        """
        Retrieve a specific report.
        
        Args:
            session_id: Unique identifier for the user session
            report_id: Unique identifier for the report
            
        Returns:
            The report data or empty dict if not found
        """
        # Check cache first
        if session_id in self.reports_cache and report_id in self.reports_cache[session_id]:
            return self.reports_cache[session_id][report_id]
        
        # Look for file
        report_path = self.storage_dir / session_id / f"{report_id}.json"
        
        if report_path.exists():
            with open(report_path, 'r') as f:
                report_data = json.load(f)
                
            # Update cache
            if session_id not in self.reports_cache:
                self.reports_cache[session_id] = {}
            self.reports_cache[session_id][report_id] = report_data
            
            return report_data
        
        return {}
    
    def list_reports(self, session_id: str) -> List[Dict[str, Any]]:
        """
        List all reports for a session.
        
        Args:
            session_id: Unique identifier for the user session
            
        Returns:
            List of report summaries
        """
        session_dir = self.storage_dir / session_id
        
        if not session_dir.exists():
            return []
        
        reports = []
        
        # Process all JSON files in the session directory
        for report_file in session_dir.glob("*.json"):
            try:
                with open(report_file, 'r') as f:
                    report_data = json.load(f)
                
                # Extract summary information
                report_id = report_file.stem
                reports.append({
                    'id': report_id,
                    'sprint_name': report_data.get('metrics', {}).get('sprint_name', 'Unknown Sprint'),
                    'date_archived': report_data.get('date_archived', 'Unknown Date')
                })
                
                # Update cache
                if session_id not in self.reports_cache:
                    self.reports_cache[session_id] = {}
                self.reports_cache[session_id][report_id] = report_data
            
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error reading report {report_file}: {e}")
        
        # Sort by date (newest first)
        reports.sort(key=lambda x: x['date_archived'], reverse=True)
        
        return reports
    
    def delete_report(self, session_id: str, report_id: str) -> bool:
        """
        Delete a specific report.
        
        Args:
            session_id: Unique identifier for the user session
            report_id: Unique identifier for the report
            
        Returns:
            True if successful, False otherwise
        """
        report_path = self.storage_dir / session_id / f"{report_id}.json"
        
        # Remove from cache
        if session_id in self.reports_cache and report_id in self.reports_cache[session_id]:
            del self.reports_cache[session_id][report_id]
        
        # Delete file
        if report_path.exists():
            try:
                os.remove(report_path)
                return True
            except IOError:
                return False
        
        return False
