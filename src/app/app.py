"""
Main application module for the Agile Project Insights Dashboard.
"""

from flask import Flask, render_template, request, jsonify, session
import pandas as pd
import os
import json
from io import StringIO
import uuid
import datetime
from werkzeug.utils import secure_filename

from src.data import JiraDataProcessor
from src.data.storage import ReportStorage
from src.visualization import generate_dashboard

# Get the absolute path to the parent directory (project root)
app_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__, 
            template_folder=os.path.join(app_root, 'templates'),
            static_folder=os.path.join(app_root, 'static'))

# Use a fixed secret key to ensure sessions persist after server restart
app.secret_key = 'beNovelty_report_optimization_fixed_key_2025'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max file size

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Store uploaded data temporarily in memory
data_store = {}
# Store archived sprint data
sprint_archives = {}
# Initialize persistent report storage
reports_storage = ReportStorage()


@app.route('/')
def index():
    """
    Render the main dashboard page.
    """
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Handle CSV file upload and validation.
    """
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'})
    
    if file and file.filename.endswith('.csv'):
        try:
            # Create a unique session ID
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
            
            # Save file temporarily
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
            file.save(filepath)
            
            # Process the data
            processor = JiraDataProcessor(file_path=filepath)
            
            # Store processor in data_store
            data_store[session_id] = processor
            
            # Get available sprints - now returns dicts instead of strings
            sprints = processor.get_all_sprints()
            
            # Convert the sprints to a format suitable for the frontend dropdown
            formatted_sprints = []
            for i, sprint in enumerate(sprints):
                # Handle both string sprints (old format) and dictionary sprints (new format)
                if isinstance(sprint, dict):
                    name = sprint.get('name', f"Sprint {i+1}")
                    formatted_sprints.append({
                        'name': name,
                        'index': i,
                        'total_points': sprint.get('total_points', 0),
                        'completed_points': sprint.get('completed_points', 0),
                        'utilization': sprint.get('utilization', 0)
                    })
                else:
                    # Fallback for old string format
                    formatted_sprints.append({'name': sprint, 'index': i})
            
            return jsonify({
                'status': 'success',
                'message': 'File uploaded successfully',
                'sprints': formatted_sprints
            })
        
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Error processing file: {str(e)}'})
    
    return jsonify({'status': 'error', 'message': 'Invalid file format. Please upload a CSV file.'})


@app.route('/get-dashboard', methods=['POST'])
def get_dashboard():
    """
    Generate and return dashboard data for a specific sprint.
    """
    data = request.json
    session_id = session.get('session_id')
    
    if not session_id or session_id not in data_store:
        return jsonify({'status': 'error', 'message': 'No data available. Please upload a file first.'})
    
    processor = data_store[session_id]
    
    # Get parameters
    sprint_index = data.get('sprint_index', -1)  # Default to most recent sprint
    # Convert sprint_index to integer if it's a string
    if isinstance(sprint_index, str) and sprint_index.isdigit():
        sprint_index = int(sprint_index)
    team_capacity = float(data.get('team_capacity', 0))
    
    # Get sprint data
    sprint_data = processor.get_sprint_data(sprint_index)
    
    # Calculate metrics
    metrics = processor.calculate_sprint_metrics(sprint_data)
    velocity_data = processor.calculate_velocity_trend()
    scope_change = processor.calculate_scope_change(sprint_data)

    # Calculate projected capacity using the enhanced method with moving average
    # Pass team_capacity to the projection if it's available
    projected_capacity = processor.project_future_capacity(
        sprints_to_consider=4,  # Consider 4 sprints for moving average calculation
        team_capacity_hours=team_capacity if team_capacity > 0 else None,
        sprint_index=sprint_index  # Pass the sprint index for context
    )
    
    # Get all sprints for additional context in the response
    all_sprints = processor.get_all_sprints()
    current_sprint_details = None
    
    # Find the details of the currently selected sprint
    if isinstance(sprint_index, int) and sprint_index >= 0 and sprint_index < len(all_sprints):
        current_sprint_details = all_sprints[sprint_index]
    elif sprint_index == -1 and all_sprints:  # Most recent sprint
        current_sprint_details = all_sprints[-1]
    
    # Generate dashboard
    dashboard = generate_dashboard(
        metrics=metrics,
        team_capacity=team_capacity,
        velocity_data=velocity_data,
        scope_change=scope_change,
        projected_capacity=projected_capacity
    )
    
    # Add sprint details to the response
    if current_sprint_details:
        dashboard['current_sprint_details'] = current_sprint_details
    
    return jsonify({
        'status': 'success',
        'dashboard': dashboard
    })


@app.route('/archive-sprint', methods=['POST'])
def archive_sprint():
    """
    Archive the current sprint data for historical reference.
    """
    data = request.json
    session_id = session.get('session_id')
    
    if not session_id or session_id not in data_store:
        return jsonify({'status': 'error', 'message': 'No data available. Please upload a file first.'})
    
    processor = data_store[session_id]
    
    # Get parameters
    sprint_index = data.get('sprint_index', -1)  # Default to most recent sprint
    # Convert sprint_index to integer if it's a string
    if isinstance(sprint_index, str) and sprint_index.isdigit():
        sprint_index = int(sprint_index)
    
    # Get sprint data
    sprint_data = processor.get_sprint_data(sprint_index)
    
    # Calculate metrics and supporting data for archive
    metrics = processor.calculate_sprint_metrics(sprint_data)
    velocity_data = processor.calculate_velocity_trend()
    scope_change = processor.calculate_scope_change(sprint_data)
    projected_capacity = processor.project_future_capacity(
        sprints_to_consider=4,
        team_capacity_hours=None,
        sprint_index=sprint_index
    )
    assignees = processor.get_assignee_data(sprint_index)
    projects = processor.get_project_data(sprint_index)

    # Get all sprints for additional context
    all_sprints = processor.get_all_sprints()
    current_sprint_details = None
    
    # Find the details of the currently selected sprint
    if isinstance(sprint_index, int) and sprint_index >= 0 and sprint_index < len(all_sprints):
        current_sprint_details = all_sprints[sprint_index]
    elif sprint_index == -1 and all_sprints:  # Most recent sprint
        current_sprint_details = all_sprints[-1]
    
    # Add sprint details to the metrics if available
    if current_sprint_details:
        metrics['sprint_details'] = current_sprint_details

    # Build dashboard data so archived reports can be reloaded later
    dashboard = generate_dashboard(
        metrics=metrics,
        team_capacity=0,
        velocity_data=velocity_data,
        scope_change=scope_change,
        projected_capacity=projected_capacity
    )
    
    # Generate a unique ID for the archived sprint
    archive_id = str(uuid.uuid4())
    
    # Create report data
    report_data = {
        'archive_id': archive_id,
        'date_archived': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'metrics': metrics,
        'dashboard': dashboard,
        'assignees': assignees,
        'projects': projects
    }
    
    # Save to persistent storage
    reports_storage.save_sprint_report(session_id, report_data)
    
    # Also keep in memory for backwards compatibility
    if session_id not in sprint_archives:
        sprint_archives[session_id] = {}
    
    sprint_archives[session_id][archive_id] = report_data
    
    return jsonify({
        'status': 'success',
        'message': 'Sprint archived successfully',
        'archive_id': archive_id
    })


@app.route('/get-archived-sprints', methods=['GET'])
def get_archived_sprints():
    """
    Get a list of archived sprints.
    """
    session_id = session.get('session_id')
    
    if not session_id:
        # Look for any report folders in the storage directory
        # This helps when the page is reloaded and the session is lost
        existing_folders = os.listdir(reports_storage.storage_dir)
        if existing_folders:
            # Use the first available folder as the session_id
            session_id = existing_folders[0]
            # Store it in the session for future requests
            session['session_id'] = session_id
            print(f"Restored session from existing folder: {session_id}")
        else:
            return jsonify({'status': 'error', 'message': 'No session available.'})
    
    # Get reports from persistent storage
    reports = reports_storage.list_reports(session_id)
    
    if not reports:
        return jsonify({'status': 'error', 'message': 'No archived sprints available.'})
    
    return jsonify({
        'status': 'success',
        'archived_sprints': reports
    })


@app.route('/get-archived-sprint/<archive_id>', methods=['GET'])
def get_archived_sprint(archive_id):
    """
    Get data for a specific archived sprint.
    """
    session_id = session.get('session_id')
    
    # Try to get the report using current session
    report = None
    
    if session_id:
        report = reports_storage.get_report(session_id, archive_id)
    
    # If no session or report not found with current session, search all folders
    if not report:
        # Check all directories in the storage directory
        for folder in os.listdir(reports_storage.storage_dir):
            folder_path = os.path.join(reports_storage.storage_dir, folder)
            if os.path.isdir(folder_path):
                potential_report = reports_storage.get_report(folder, archive_id)
                if potential_report:
                    # We found the report in a different session folder
                    report = potential_report
                    # Update the session with the folder that contains this report
                    session['session_id'] = folder
                    session_id = folder
                    break
    
    if not report:
        return jsonify({'status': 'error', 'message': 'Archived sprint not found.'})
    
    return jsonify({
        'status': 'success',
        'archived_sprint': report
    })


@app.route('/get-issue-types', methods=['GET'])
def get_issue_types():
    """
    Get a list of all issue types from the current data.
    """
    session_id = session.get('session_id')
    
    if not session_id or session_id not in data_store:
        return jsonify({'status': 'error', 'message': 'No data available. Please upload a file first.'})
    
    processor = data_store[session_id]
    
    if processor.data is None:
        return jsonify({'status': 'error', 'message': 'No data available.'})
    
    issue_types = processor.data['Issue Type'].unique().tolist()
    
    return jsonify({
        'status': 'success',
        'issue_types': issue_types
    })


@app.route('/delete-archived-sprint/<archive_id>', methods=['DELETE'])
def delete_archived_sprint(archive_id):
    """
    Delete a specific archived sprint report.
    """
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'status': 'error', 'message': 'No session available.'})
    
    # Delete from persistent storage
    success = reports_storage.delete_report(session_id, archive_id)
    
    # Also delete from memory if it exists
    if session_id in sprint_archives and archive_id in sprint_archives[session_id]:
        del sprint_archives[session_id][archive_id]
    
    if success:
        return jsonify({'status': 'success', 'message': 'Report deleted successfully'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to delete report'})


@app.route('/get-assignee-data', methods=['POST'])
def get_assignee_data():
    """
    Get data for all assignees in a specific sprint.
    Used for the assignee filter functionality.
    """
    data = request.json
    session_id = session.get('session_id')
    
    if not session_id or session_id not in data_store:
        return jsonify({'status': 'error', 'message': 'No data available. Please upload a file first.'})
    
    processor = data_store[session_id]
    
    # Get parameters
    sprint_index = data.get('sprint_index', -1)  # Default to most recent sprint
    # Convert sprint_index to integer if it's a string
    if isinstance(sprint_index, str) and sprint_index.isdigit():
        sprint_index = int(sprint_index)
        
    # Get assignee data
    assignees = processor.get_assignee_data(sprint_index)
    
    return jsonify({
        'status': 'success',
        'assignees': assignees
    })


@app.route('/get-project-data', methods=['POST'])
def get_project_data():
    """
    Get data for all projects in a specific sprint.
    Used for the project filter functionality.
    """
    data = request.json
    session_id = session.get('session_id')
    
    if not session_id or session_id not in data_store:
        return jsonify({'status': 'error', 'message': 'No data available. Please upload a file first.'})
    
    processor = data_store[session_id]
    
    # Get parameters
    sprint_index = data.get('sprint_index', -1)  # Default to most recent sprint
    # Convert sprint_index to integer if it's a string
    if isinstance(sprint_index, str) and sprint_index.isdigit():
        sprint_index = int(sprint_index)
        
    # Get project data
    projects = processor.get_project_data(sprint_index)
    
    return jsonify({
        'status': 'success',
        'projects': projects
    })


if __name__ == '__main__':
    app.run(debug=True)
