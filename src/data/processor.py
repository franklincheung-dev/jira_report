"""
Data processor for the Agile Project Insights Dashboard.

This module handles the processing of Jira CSV exports to extract key metrics and insights.
"""

import pandas as pd
import traceback
from datetime import datetime
import numpy as np
import re
from typing import Dict, List, Tuple, Optional, Any

class JiraDataProcessor:
    """
    Processes Jira CSV data to extract key metrics for the Agile Project Insights Dashboard.
    """
    
    REQUIRED_COLUMNS = [
        'Issue Type', 'Issue key', 'Issue id', 'Summary', 'Assignee', 
        'Assignee Id', 'Reporter', 'Reporter Id', 'Priority', 'Status', 
        'Resolution', 'Created', 'Updated', 'Due date', 'Original estimate',
        'Parent', 'Parent summary', 'Description', 'Sprint'
    ]
    
    def __init__(self, file_path: str = None, dataframe: pd.DataFrame = None):
        """
        Initialize the processor with either a file path or a pandas DataFrame.
        
        Args:
            file_path: Path to the Jira CSV export file
            dataframe: Pre-loaded pandas DataFrame
        """
        self.data = None
        self.sprints = []
        self.current_sprint = None
        
        if file_path:
            self.load_csv(file_path)
        elif dataframe is not None:
            self.data = dataframe.copy()
            self._validate_and_prepare_data()
        
    def load_csv(self, file_path: str) -> bool:
        """
        Load and validate a Jira CSV export.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.data = pd.read_csv(file_path)
            return self._validate_and_prepare_data()
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return False
    
    def _validate_and_prepare_data(self) -> bool:
        """
        Validate that the data has all required columns and prepare it for analysis.
        
        Returns:
            bool: True if validation passes, False otherwise
        """
        # Check if required columns exist
        missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in self.data.columns]
        if missing_columns:
            print(f"Missing required columns: {missing_columns}")
            return False
        
        # Convert date columns to datetime with common Jira export formats
        try:
            # Try to determine the date format from a sample, ordered by most likely to least likely
            date_formats = [
                '%d/%b/%y %I:%M %p',  # 03/Jul/25 12:00 AM
                '%d/%b/%y %H:%M',     # 03/Jul/25 00:00
                '%d/%b/%Y %I:%M %p',  # 03/Jul/2025 12:00 AM
                '%d/%b/%Y',           # 03/Jul/2025
                '%d/%m/%Y %H:%M:%S',  # DD/MM/YYYY HH:MM:SS
                '%d/%m/%Y',           # DD/MM/YYYY
                '%Y-%m-%d %H:%M:%S',  # YYYY-MM-DD HH:MM:SS
                '%Y-%m-%d'            # YYYY-MM-DD
            ]

            # Function to convert dates with different format attempts
            def convert_date_column(column):
                if column in self.data.columns and not self.data[column].isna().all():
                    # Try each date format until one works
                    for date_format in date_formats:
                        try:
                            # Try to parse with explicit format
                            converted = pd.to_datetime(self.data[column], format=date_format, errors='coerce')
                            # If we successfully converted some dates (not all NaT), return the result
                            if not converted.isna().all():
                                return converted
                        except:
                            continue
                    
                    # If no format works, fall back to flexible parsing
                    return pd.to_datetime(self.data[column], dayfirst=True, errors='coerce')
                return pd.Series(dtype='datetime64[ns]')
            
            # Apply conversion to each date column
            self.data['Created'] = convert_date_column('Created')
            self.data['Updated'] = convert_date_column('Updated')
            self.data['Due date'] = convert_date_column('Due date')
            
        except Exception as e:
            print(f"Error converting date columns: {e}")
            return False
        
        # Convert Original estimate to numeric, handling empty values
        self.data['Original estimate'] = pd.to_numeric(self.data['Original estimate'], errors='coerce').fillna(0)
        
        # Convert story points from seconds to hours
        self.data['Original estimate'] = self.data['Original estimate'] / 3600
        
        # Merge multiple Sprint columns into a single column
        self._merge_sprint_columns()
        
        # Identify sprints based on consolidated Sprint column
        self._identify_sprints()
        
        # Categorize tasks based on Parent Summary
        self.categorize_tasks()
        
        return True
    
    def _identify_sprints(self) -> None:
        """
        Identify sprints from the consolidated 'Sprints' column.
        Falls back to due dates if no sprint data is available.
        """
        self.sprints = []
        
        # Use the consolidated Sprints column if it has data
        if 'Sprints' in self.data.columns and not self.data['Sprints'].isna().all() and not all(self.data['Sprints'] == ''):
            # Get all unique sprint names by splitting the semicolon-separated values
            all_sprints = []
            for sprint_str in self.data['Sprints'].dropna():
                if sprint_str:  # Skip empty strings
                    all_sprints.extend(sprint_str.split(';'))
            
            # Remove duplicates
            unique_sprints = list(set(all_sprints))
            
            # Sort sprints with smart handling of numeric sprint names (like "2025 Sprint 9" vs "2025 Sprint 25")
            def smart_sprint_sort_key(sprint_name):
                """Custom sort key function to handle numeric sprint numbers correctly"""
                if not isinstance(sprint_name, str):
                    return (0, 0, sprint_name)  # Handle non-string values
                
                # Match pattern like "2025 Sprint 9"
                year_sprint_match = re.match(r"(\d{4})\s+Sprint\s+(\d+)", sprint_name)
                if year_sprint_match:
                    year = int(year_sprint_match.group(1))
                    sprint_num = int(year_sprint_match.group(2))
                    return (1, year, sprint_num)  # Sort first by year, then by sprint number
                
                # Match pattern like "Sprint 9"
                sprint_match = re.match(r"Sprint\s+(\d+)", sprint_name)
                if sprint_match:
                    sprint_num = int(sprint_match.group(1))
                    return (2, 0, sprint_num)  # Sort by sprint number
                
                # Default case: alphabetical sort
                return (3, 0, sprint_name)
                
            self.sprints = sorted(unique_sprints, key=smart_sprint_sort_key)
            
            # Set the current sprint (assuming the last one is current)
            if self.sprints:
                self.current_sprint = self.sprints[-1]
        # Fall back to the due date method
        elif 'Due date' in self.data.columns:
            # Remove NaT values and get unique due dates
            due_dates = self.data['Due date'].dropna().unique()
            # Sort due dates
            due_dates = sorted(due_dates)
            
            # Group into sprints (each unique due date represents end of a sprint)
            sprint_names = []
            for date in due_dates:
                sprint_name = f"Sprint ending {date.strftime('%d %b %Y')}"
                sprint_names.append(sprint_name)
            
            self.sprints = sprint_names
            
            # Set the current sprint (assuming the latest due date is the current sprint)
            if self.sprints:
                self.current_sprint = self.sprints[-1]
    
    # Removed set_billable_types since we now use categories instead
    
    def get_sprint_data(self, sprint_index: int = -1) -> pd.DataFrame:
        """
        Get data for a specific sprint.
        Default is the most recent sprint (-1).
        
        Args:
            sprint_index: Index of the sprint (negative for most recent)
            
        Returns:
            DataFrame containing sprint data
        """
        if not self.sprints:
            # If no sprints identified, return all data
            return self.data
        
        # Get the specified sprint
        try:
            sprint_name = self.sprints[sprint_index]
            # Update the current sprint with the selected sprint
            self.current_sprint = sprint_name
        except IndexError:
            # If the index is out of range, use the most recent sprint
            sprint_name = self.sprints[-1]
            self.current_sprint = sprint_name
        
        # Use the consolidated Sprints column if it exists
        if 'Sprints' in self.data.columns:
            # Check for tasks that have the specified sprint in any of their sprint associations
            sprint_data = self.data[self.data['Sprints'].str.contains(sprint_name, na=False)]
        else:
            # Find all Sprint columns (a task can be associated with multiple sprints)
            sprint_columns = [col for col in self.data.columns if col == 'Sprint' or col.startswith('Sprint.')]
            
            if sprint_columns:
                # Search across all Sprint columns
                masks = []
                for col in sprint_columns:
                    masks.append(self.data[col] == sprint_name)
                
                if masks:  # Only proceed if we have masks
                    # Combine the masks with OR operations
                    combined_mask = masks[0]
                    for mask in masks[1:]:
                        combined_mask = combined_mask | mask
                    
                    sprint_data = self.data[combined_mask]
                else:
                    # No valid sprint columns, return empty dataframe
                    sprint_data = pd.DataFrame(columns=self.data.columns)
            else:
                # Fall back to due date filtering based on sprint name format
                if sprint_name.startswith("Sprint ending "):
                    sprint_date_str = sprint_name.replace("Sprint ending ", "")
                    try:
                        sprint_date = pd.to_datetime(sprint_date_str, format='%d %b %Y')
                        sprint_data = self.data[self.data['Due date'] == sprint_date]
                    except:
                        # If parsing fails, return empty dataframe
                        sprint_data = pd.DataFrame(columns=self.data.columns)
                else:
                    # If no clear date pattern, return empty dataframe
                    sprint_data = pd.DataFrame(columns=self.data.columns)
                
        return sprint_data
    
    def calculate_sprint_metrics(self, sprint_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Calculate key metrics for a sprint.
        
        Args:
            sprint_data: DataFrame containing sprint data. If None, uses the current sprint.
            
        Returns:
            Dictionary of sprint metrics including categorized blockers by person and project
        """
        if sprint_data is None:
            sprint_data = self.get_sprint_data()
        
        if sprint_data.empty:
            return {
                'sprint_name': 'No sprint data available',
                'completion_percentage': 0,
                'total_story_points': 0,
                'completed_story_points': 0,
                'billable_hours': 0,
                'product_hours': 0,
                'internal_hours': 0,
                'other_hours': 0,
                'blockers': [],
                'blockers_by_person': {},
                'blockers_by_project': {}
            }
        
        # 1. Calculate completion percentage
        total_points = sprint_data['Original estimate'].sum()
        completed_points = sprint_data[sprint_data['Status'] == 'Done']['Original estimate'].sum()
        completion_percentage = (completed_points / total_points * 100) if total_points > 0 else 0
        
        # 2. Calculate category breakdown using the new categorization
        # Always use the category-based approach
        if 'Category' not in sprint_data.columns:
            # Categorize the tasks if not already done
            self.categorize_tasks(sprint_data)
            
        billable_hours = sprint_data[sprint_data['Category'] == 'Billable']['Original estimate'].sum()
        product_hours = sprint_data[sprint_data['Category'] == 'Product']['Original estimate'].sum()
        internal_hours = sprint_data[sprint_data['Category'] == 'Internal']['Original estimate'].sum()
        other_hours = sprint_data[sprint_data['Category'] == 'Other']['Original estimate'].sum()
        
        # 3. Identify blockers
        today = pd.Timestamp.now().normalize()
        
        # First, identify high priority blockers
        priority_blockers = sprint_data[
            (sprint_data['Priority'].isin(['Highest', 'High'])) & 
            (sprint_data['Status'] != 'Done')
        ]
        
        # Next, identify overdue tasks (due date in the past and not done)
        overdue_blockers = sprint_data[
            (sprint_data['Due date'].notna()) &
            (sprint_data['Due date'] < today) &
            (sprint_data['Status'] != 'Done')
        ]
        
        # Also identify incomplete tasks when sprint is marked as completed 
        # or has high completion percentage but still has incomplete tasks
        incomplete_tasks = sprint_data[sprint_data['Status'] != 'Done']
        
        # Combine all types of blockers and remove duplicates
        all_blockers = pd.concat([priority_blockers, overdue_blockers, incomplete_tasks]).drop_duplicates()
        
        # Create a copy of the subset we need for blockers
        blocker_columns = ['Issue key', 'Summary', 'Assignee', 'Status', 'Due date', 'Priority']
        if 'Parent summary' in all_blockers.columns:
            blocker_columns.append('Parent summary')  # Add project/parent information
        blocker_subset = all_blockers[blocker_columns]
        
        # Initialize dictionaries for person and project specific blockers
        blockers_by_person = {}
        blockers_by_project = {}
        blockers = []

        for _, row in blocker_subset.iterrows():
            # Make sure due date is properly serialized
            due_date = None
            if not pd.isna(row['Due date']):
                try:
                    if isinstance(row['Due date'], pd.Timestamp):
                        due_date = row['Due date'].strftime('%d/%b/%y %I:%M %p')
                    else:
                        due_date = pd.to_datetime(row['Due date']).strftime('%d/%b/%y %I:%M %p')
                except Exception as e:
                    print(f"Error formatting due date: {e}")
                    due_date = str(row['Due date'])
            
            # Determine blocker type: 'overdue' (red) or 'incomplete' (yellow)
            blocker_type = 'incomplete'  # Default - yellow
            
            # Overdue tasks (red)
            if not pd.isna(row['Due date']) and row['Due date'] < today:
                blocker_type = 'overdue'
            elif row.get('Priority') in ['Highest', 'High']:
                blocker_type = 'high_priority'
            
            blocker = {
                'Issue key': row['Issue key'],
                'Summary': row['Summary'],
                'Assignee': row['Assignee'],
                'Status': row['Status'],
                'Due date': due_date,
                'blocker_type': blocker_type
            }

            # Add to main blockers list
            blockers.append(blocker)

            # Add to person-specific blockers
            assignee = row['Assignee'] if not pd.isna(row['Assignee']) else 'Unassigned'
            if assignee not in blockers_by_person:
                blockers_by_person[assignee] = []
            blockers_by_person[assignee].append(blocker)

            # Add to project-specific blockers
            project = row.get('Parent summary', 'No Project')
            if pd.isna(project):
                project = 'No Project'
            if project not in blockers_by_project:
                blockers_by_project[project] = []
            blockers_by_project[project].append(blocker)

        # Get sprint name
        # First check if we already know the sprint_name from the context this method was called from
        # Since we might be calling this with an already filtered sprint dataset
        if hasattr(self, 'current_sprint') and self.current_sprint is not None:
            sprint_name = self.current_sprint
        # Then try to get from 'All_Sprints' if available
        elif 'All_Sprints' in sprint_data.columns and not sprint_data.empty and not sprint_data['All_Sprints'].isna().all():
            # Take first sprint from the first row
            first_sprints = str(sprint_data['All_Sprints'].iloc[0]).split(';')[0]
            sprint_name = first_sprints if first_sprints and first_sprints != 'nan' else "Unknown Sprint"
        # Then try traditional Sprint column
        elif 'Sprint' in sprint_data.columns and not sprint_data.empty and not sprint_data['Sprint'].isna().all():
            sprint_name = str(sprint_data['Sprint'].iloc[0])
        # Fall back to due date method
        else:
            if not sprint_data.empty and 'Due date' in sprint_data.columns:
                latest_due = sprint_data['Due date'].max()
                if pd.notna(latest_due):
                    sprint_name = f"Sprint ending {latest_due.strftime('%d/%b/%y')}"
                else:
                    sprint_name = "Unknown Sprint"
            else:
                sprint_name = "Unknown Sprint"
        
        # Determine sprint status
        if sprint_data.empty or 'Status' not in sprint_data.columns:
            sprint_status = "Not Started"
        elif sprint_data['Status'].str.contains('Done', na=False).all():
            sprint_status = "Completed"
        elif sprint_data['Status'].str.contains('Done', na=False).any():
            sprint_status = "In Progress"
        else:
            sprint_status = "Not Started"
            
        # Ensure there's a consistent relationship between sprint status and blockers
        # If there are incomplete tasks but status is "Completed", adjust the status
        if sprint_status == "Completed" and len(sprint_data[sprint_data['Status'] != 'Done']) > 0:
            sprint_status = "In Progress"
        


        
        # 4. Resource utilization by team member
        resource_utilization = []
        assignee_distribution = {}
        if 'Assignee' in sprint_data.columns:
            for assignee in sprint_data['Assignee'].unique():
                if pd.isna(assignee):
                    continue
                assignee_tasks = sprint_data[sprint_data['Assignee'] == assignee]
                assignee_total_points = assignee_tasks['Original estimate'].sum()
                assignee_completed_points = assignee_tasks[assignee_tasks['Status'] == 'Done']['Original estimate'].sum()
                resource_utilization.append({
                    'assignee': assignee,
                    'total_points': float(assignee_total_points),
                    'completed_points': float(assignee_completed_points),
                    'completion_rate': float(assignee_completed_points / assignee_total_points * 100) if total_points > 0 else 0.0
                })
                assignee_distribution[assignee] = float(assignee_total_points)

        
        
        return {
            'sprint_name': sprint_name,
            'sprint_status': sprint_status,
            'completion_percentage': float(completion_percentage),
            'total_story_points': float(total_points),
            'completed_story_points': float(completed_points),
            'billable_hours': float(billable_hours),
            'product_hours': float(product_hours),
            'internal_hours': float(internal_hours),
            'other_hours': float(other_hours),
            'blockers': blockers,
            'blockers_by_person': blockers_by_person,
            'blockers_by_project': blockers_by_project,
            'resource_utilization': resource_utilization,
            'assignee_distribution': {k: float(v) for k, v in assignee_distribution.items()}  # Ensure it's JSON serializable
        }
    
    def calculate_velocity_trend(self) -> Dict[str, List]:
        """
        Calculate velocity trend across sprints.
        
        Returns:
            Dictionary with sprint names and velocities
        """
        sprint_names = []
        velocities = []
        categories = {"Billable": [], "Product": [], "Internal": [], "Other": []}
        
        for i, sprint_name in enumerate(self.sprints):
            sprint_data = self.get_sprint_data(i)
            if sprint_data.empty:
                continue
                
            # Calculate velocity (completed points)
            completed_points = sprint_data[sprint_data['Status'] == 'Done']['Original estimate'].sum()
            
            # Only add to our records if we have actual data (prevents zero velocity bugs)
            if not sprint_data.empty:
                if not pd.isna(completed_points) and completed_points > 0:
                    # Record sprint name and velocity
                    sprint_names.append(sprint_name)
                    velocities.append(completed_points)
            
            # Calculate category breakdown
            if 'Category' in sprint_data.columns:
                for category in categories.keys():
                    cat_points = sprint_data[sprint_data['Category'] == category]['Original estimate'].sum()
                    categories[category].append(cat_points)
        
        result = {
            'sprint_names': sprint_names,
            'velocities': velocities
        }
        
        # Add categories if we have them
        if any(len(v) > 0 for v in categories.values()):
            result['categories'] = categories
            
        return result
    
    def calculate_scope_change(self, sprint_data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate scope change within a sprint.
        
        This method is deprecated and will be removed in a future version.
        It now returns empty values for backwards compatibility.
        
        Args:
            sprint_data: DataFrame containing sprint data
            
        Returns:
            Dictionary with scope change metrics (all zeros)
        """
        # Return empty values
        return {
            'initial_scope': 0,
            'work_added': 0,
            'work_removed': 0
        }
    
    def project_future_capacity(self, sprints_to_consider: int = 4, team_capacity_hours: float = None, sprint_index: int = -1) -> Dict[str, Any]:
        """
        Project future capacity based on recent sprint velocities and team capacity.
        
        Args:
            sprints_to_consider: Number of most recent sprints to consider
            team_capacity_hours: Total team capacity in hours per sprint (if None, will be estimated from data)
            sprint_index: Index of the sprint to use as the current sprint. Default is -1 (most recent sprint).
            
        Returns:
            Dictionary with projected capacity for current sprint, next sprint, and sprint after next
        """
        # Get velocity trend data
        velocity_data = self.calculate_velocity_trend()
        sprint_names = velocity_data.get('sprint_names', [])
        velocities = velocity_data.get('velocities', [])
        categories_data = velocity_data.get('categories', {})
        
        # Exclude the current sprint from velocity calculations
        # Assuming the last sprint in the list is the current one
        completed_sprint_names = sprint_names[:-1] if sprint_names else []
        completed_velocities = velocities[:-1] if velocities else []
        
        # Initialize variables
        avg_velocity = 0
        moving_avgs = []
        latest_moving_avg = 0
        data_quality_warning = None;
        
        # Ensure we have enough data
        if len(completed_velocities) == 0:
            # No historical sprint data available
            data_quality_warning = "No historical sprint data available for forecasting."
            avg_velocity = 0
            latest_moving_avg = 0
        else:
            # Calculate overall average velocity (from completed sprints only)
            avg_velocity = sum(completed_velocities) / len(completed_velocities)
            
            # Calculate moving averages with window size = sprints_to_consider
            if len(completed_velocities) >= sprints_to_consider:
                # Calculate the moving average for the most recent window of completed sprints
                recent_window = completed_velocities[-sprints_to_consider:]
                latest_moving_avg = sum(recent_window) / len(recent_window)
                
                # Store moving averages properly positioned for visualization
                # First, create a list with None values for the first (sprints_to_consider-1) positions
                # This ensures the moving average line starts at the right position in charts
                moving_avgs = [None] * (sprints_to_consider - 1)
                
                # Then calculate and append moving averages for all valid windows
                for i in range(sprints_to_consider - 1, len(completed_velocities)):
                    window = completed_velocities[max(0, i - sprints_to_consider + 1):i + 1]
                    moving_avg = sum(window) / len(window)
                    moving_avgs.append(round(moving_avg, 1))
            else:
                data_quality_warning = f"Only {len(completed_velocities)} completed sprints available, but {sprints_to_consider} needed for ideal moving average calculation."
                # Use overall average as fallback
                latest_moving_avg = avg_velocity
                # Create empty list for visualization (no moving averages to display yet)
                moving_avgs = []
        
        # Estimate team capacity if not provided
        if team_capacity_hours is None:
            if len(completed_velocities) > 0:
                # Use the maximum historical velocity as a rough estimate of team capacity
                team_capacity_hours = max(completed_velocities) * 1.1  # Add 10% buffer
            else:
                # Default to a reasonable value if no data
                team_capacity_hours = 80  # Assuming a small team of 2 people with 40 hours each
        
        # Calculate historical utilization (avg velocity as % of capacity)
        avg_utilization = avg_velocity / team_capacity_hours if team_capacity_hours > 0 else 0
        
        # Calculate category breakdown percentages based on historical data
        category_percentages = {}
        category_forecasts = {}
        
        # Check if we have category data
        if categories_data and any(len(v) > 0 for v in categories_data.values()):
            # Calculate the sum of all category hours for each sprint
            # Only use completed sprints to avoid skewing category percentages
            total_category_hours = [0] * len(completed_velocities)
            
            for category, cat_hours in categories_data.items():
                # Exclude the current sprint (last entry) from category calculations
                cat_hours_completed = cat_hours[:-1] if cat_hours else []
                
                for i, hours in enumerate(cat_hours_completed):
                    if i < len(total_category_hours):
                        total_category_hours[i] += hours
            
            # Calculate the average percentage for each category
            for category, cat_hours in categories_data.items():
                # Exclude the current sprint from category calculations
                cat_hours_completed = cat_hours[:-1] if cat_hours else []
                
                category_sum = sum(cat_hours_completed)
                # Avoid division by zero
                if category_sum > 0 and sum(total_category_hours) > 0:
                    category_percentages[category] = category_sum / sum(total_category_hours)
                else:
                    category_percentages[category] = 0
                    
            # Normalize the category percentages to ensure they add up to 1.0
            percentage_sum = sum(category_percentages.values())
            if percentage_sum > 0:  # Avoid division by zero
                for category in category_percentages:
                    category_percentages[category] /= percentage_sum
        else:
            # Default equal distribution if no category data
            category_percentages = {
                'Billable': 0.6,  # Default to 60% billable
                'Product': 0.2,   # 20% product work
                'Internal': 0.15, # 15% internal
                'Other': 0.05     # 5% other
            }
        
        # Calculate forecast adjustments based on historical utilization
        adjustment_factor = 1.0
        
        # If historical utilization is high (>90%), reduce slightly
        if avg_utilization > 0.9:
            adjustment_factor = 0.95  # Reduce by 5%
        # If historical utilization is low (<70%), increase slightly
        elif avg_utilization < 0.7:
            adjustment_factor = 1.1   # Increase by 10%
        
        # Calculate forecasts for upcoming sprints
        this_sprint_forecast = latest_moving_avg * adjustment_factor
        # Ensure forecast doesn't exceed team capacity
        this_sprint_forecast = min(this_sprint_forecast, team_capacity_hours * 0.95)  # Max 95% of capacity
        
        # For next sprint, apply a slight growth if utilization is good
        next_sprint_forecast = this_sprint_forecast * (1.05 if avg_utilization > 0.8 else 1.0)
        next_sprint_forecast = min(next_sprint_forecast, team_capacity_hours * 0.95)
        
        # For sprint after next, apply additional growth
        next_next_sprint_forecast = next_sprint_forecast * 1.05
        next_next_sprint_forecast = min(next_next_sprint_forecast, team_capacity_hours * 0.95)
        
        # Calculate category breakdown for forecasts
        for category, percentage in category_percentages.items():
            category_forecasts[category] = this_sprint_forecast * percentage
        
        # Save the original current sprint to restore later
        original_current = self.current_sprint
        
        # Determine the current sprint using the provided index
        try:
            if len(self.sprints) > 0:
                # Handle positive and negative indices properly
                if 0 <= sprint_index < len(self.sprints):
                    current_idx = sprint_index
                else:
                    adjusted_idx = len(self.sprints) + sprint_index if sprint_index < 0 else sprint_index
                    if 0 <= adjusted_idx < len(self.sprints):
                        current_idx = adjusted_idx
                    else:
                        # Fallback to last sprint if index is out of range
                        current_idx = len(self.sprints) - 1
                
                current_target_sprint = self.sprints[current_idx]
            else:
                # No sprints available
                current_target_sprint = "Unknown"
                current_idx = -1
        except Exception:
            # Final fallback - if anything goes wrong, use the last sprint
            current_target_sprint = self.sprints[-1] if self.sprints else "Unknown"
            current_idx = len(self.sprints) - 1 if self.sprints else -1
        
        # Calculate allocated hours without changing current_sprint permanently
        
        # Helper function to calculate allocated hours for a sprint
        def get_sprint_allocated_hours(sprint_name):
            if sprint_name != "Unknown" and 'Sprints' in self.data.columns:
                temp_data = self.data[self.data['Sprints'].str.contains(sprint_name, na=False)]
                return temp_data['Original estimate'].sum() if not temp_data.empty else 0
            return 0
        
        # 1. Calculate allocated hours for current sprint
        current_allocated = get_sprint_allocated_hours(current_target_sprint)
        
        # 2. Calculate allocated hours for next sprint if it exists
        next_allocated = 0
        if current_idx + 1 < len(self.sprints):
            next_sprint = self.sprints[current_idx + 1]
            next_allocated = get_sprint_allocated_hours(next_sprint)
            
        # 3. Calculate allocated hours for sprint after next if it exists
        next_next_allocated = 0
        if current_idx + 2 < len(self.sprints):
            next_next_sprint = self.sprints[current_idx + 2]
            next_next_allocated = get_sprint_allocated_hours(next_next_sprint)

        # Unallocated hours = forecast_hours - allocated_hours
        current_remaining = this_sprint_forecast - current_allocated
        next_remaining = next_sprint_forecast - next_allocated
        next_next_remaining = next_next_sprint_forecast - next_next_allocated

        # Get names for next sprints for consistent use throughout return values
        next_sprint_name = self.sprints[current_idx + 1] if current_idx + 1 < len(self.sprints) else "Future Sprint 1"
        next_next_sprint_name = self.sprints[current_idx + 2] if current_idx + 2 < len(self.sprints) else "Future Sprint 2"
        
        # Restore the original current sprint before returning
        self.current_sprint = original_current

        # Convert remaining variables to zero if negative (can't have negative remaining)
        current_remaining = max(0, current_remaining)
        next_remaining = max(0, next_remaining)
        next_next_remaining = max(0, next_next_remaining)
        
        # Create a helper function to generate sprint forecast data
        def create_sprint_forecast(name, forecast, allocated, remaining, category_dict=None, ratio=1.0):
            """Helper function to create a consistent sprint forecast dictionary"""
            if category_dict is None:
                category_dict = category_forecasts
                
            return {
                'sprint_name': name,
                'forecast_hours': round(forecast, 1),
                'allocated_hours': round(allocated, 1),
                'category_breakdown': {cat: round(val * ratio, 1) for cat, val in category_dict.items()},
                'based_on_sprints': len(completed_velocities),
                'team_capacity': team_capacity_hours,
                'historical_utilization': round(avg_utilization * 100, 1),
                'unallocated_hours': round(remaining, 1),
                'remaining_percentage': round((remaining / team_capacity_hours) * 100 if team_capacity_hours > 0 else 0, 1)
            }
        
        # Return data structure with computed forecasts
        return {
            'current_sprint': create_sprint_forecast(
                current_target_sprint, 
                this_sprint_forecast, 
                current_allocated, 
                current_remaining
            ),
            'next_sprint': create_sprint_forecast(
                next_sprint_name,
                next_sprint_forecast,
                next_allocated,
                next_remaining,
                ratio=(next_sprint_forecast / this_sprint_forecast) if this_sprint_forecast > 0 else 1.0
            ),
            'next_next_sprint': create_sprint_forecast(
                next_next_sprint_name,
                next_next_sprint_forecast,
                next_next_allocated,
                next_next_remaining,
                ratio=(next_next_sprint_forecast / this_sprint_forecast) if this_sprint_forecast > 0 else 1.0
            ),
            'historical': {
                'avg_velocity': round(avg_velocity, 1),
                'velocities': [round(v, 1) for v in completed_velocities],  # Show only completed sprint velocities
                'sprint_count': len(completed_velocities),
                'moving_avgs': moving_avgs,
                'latest_moving_avg': round(latest_moving_avg, 1),
                'data_quality_warning': data_quality_warning
            }
        }
    
    def get_all_sprints(self) -> List[Dict[str, Any]]:
        """
        Get a list of all identified sprints with additional metrics.
        
        Returns:
            List of sprint dictionaries with name, end_date, completed points, and category breakdown
        """
        if not self.sprints:
            return []
            
        sprint_details = []
        for i, sprint_name in enumerate(self.sprints):
            sprint_data = self.get_sprint_data(i)
            
            # Default values
            sprint_info = {
                'name': sprint_name,
                'total_points': 0,
                'completed_points': 0,
                'utilization': 0,
                'categories': {
                    'Billable': 0,
                    'Product': 0,
                    'Internal': 0,
                    'Other': 0
                }
            }
            
            # Extract due date if available
            if 'Due date' in sprint_data.columns and not sprint_data.empty and not sprint_data['Due date'].isna().all():
                # Get the most common due date
                due_date = sprint_data['Due date'].mode().iloc[0] if not sprint_data['Due date'].mode().empty else None
                if due_date:
                    sprint_info['end_date'] = due_date
            
            # Calculate metrics if we have sprint data
            if not sprint_data.empty and 'Original estimate' in sprint_data.columns:
                total_points = sprint_data['Original estimate'].sum()
                completed_points = sprint_data[sprint_data['Status'] == 'Done']['Original estimate'].sum()
                
                sprint_info['total_points'] = total_points
                sprint_info['completed_points'] = completed_points
                sprint_info['utilization'] = round(completed_points / total_points * 100, 1) if total_points > 0 else 0
                
                # Calculate category breakdown
                if 'Category' in sprint_data.columns:
                    for category in sprint_info['categories'].keys():
                        # Total points in this category
                        cat_total = sprint_data[sprint_data['Category'] == category]['Original estimate'].sum()
                        # Completed points in this category
                        cat_completed = sprint_data[(sprint_data['Category'] == category) & 
                                                   (sprint_data['Status'] == 'Done')]['Original estimate'].sum()
                        
                        sprint_info['categories'][category] = {
                            'total': cat_total,
                            'completed': cat_completed,
                            'utilization': round(cat_completed / cat_total * 100, 1) if cat_total > 0 else 0
                        }
            
            sprint_details.append(sprint_info)
            
        return sprint_details
    
    def categorize_tasks(self, data=None) -> None:
        """
        Categorize tasks into "Billable", "Product", "Internal", and "Other" based on Parent Summary format.
        Parent Summary format: {Category} | {Project}
        
        Args:
            data: Optional DataFrame to categorize instead of self.data
        """
        # Use provided data or instance data
        df = data if data is not None else self.data
        
        if 'Parent summary' not in df.columns:
            # Create a default category column if Parent summary is not available
            df['Category'] = 'Other'
            return
        
        # Define categorization function
        def determine_category(row):
            parent_summary = str(row.get('Parent summary', '')).strip()
            
            # Check for empty or NaN values
            if parent_summary == 'nan' or parent_summary == '' or pd.isna(parent_summary):
                return 'Other'
            
            # Split by '|' and get the category part
            if '|' in parent_summary:
                parts = parent_summary.split('|')
                category_part = parts[0].strip().lower()
                
                # Look for category in the first part
                if 'billable' in category_part:
                    return 'Billable'
                elif 'product' in category_part:
                    return 'Product'
                elif 'internal' in category_part:
                    return 'Internal'
                else:
                    return 'Other'
            else:
                # Fall back to previous logic if '|' is not found
                if '[Billable]' in parent_summary or '(Billable)' in parent_summary:
                    return 'Billable'
                elif '[Product]' in parent_summary or '(Product)' in parent_summary:
                    return 'Product'
                elif '[Internal]' in parent_summary or '(Internal)' in parent_summary:
                    return 'Internal'
                else:
                    return 'Other'
        
        # Apply the categorization function to create a new 'Category' column
        df['Category'] = df.apply(determine_category, axis=1)
        
        # If we're working on the instance data, update it
        if data is None:
            self.data['Category'] = df['Category']
    
    def _merge_sprint_columns(self) -> None:
        """
        Merge multiple Sprint columns into a single 'Sprints' column.
        This handles Jira exports where tasks can be associated with multiple sprints.
        """
        # Find all Sprint columns
        sprint_columns = [col for col in self.data.columns if col == 'Sprint' or col.startswith('Sprint.')]
        
        if not sprint_columns:
            return
            
        # Create a new column by combining all sprint values
        self.data['Sprints'] = ''
        
        # For each row, collect all non-null sprint values from all sprint columns
        for index, row in self.data.iterrows():
            sprint_values = []
            for col in sprint_columns:
                if pd.notna(row[col]) and row[col] != '':
                    sprint_values.append(str(row[col]))
            
            # Join with semicolons
            self.data.at[index, 'Sprints'] = ';'.join(sprint_values) if sprint_values else ''
            
        # Extract unique sprint names from the combined column
        self.all_sprints = set()
        
    def get_assignee_data(self, sprint_index: int = -1) -> list:
        """
        Get data for all assignees in the specified sprint.
        
        Args:
            sprint_index: Index of the sprint (negative for most recent)
            
        Returns:
            List of dictionaries containing assignee details and performance metrics
        """
        try:
            # Get data for the sprint
            sprint_data = self.get_sprint_data(sprint_index)
            
            if sprint_data.empty:
                return []
                
            # Group data by assignee
            assignees = []
            
            # Get unique assignees
            unique_assignees = sprint_data['Assignee'].dropna().unique()
            
            for assignee in unique_assignees:
                assignee_data = sprint_data[sprint_data['Assignee'] == assignee]
                
                # Calculate metrics for this assignee
                total_points = assignee_data['Original estimate'].sum()
                completed_points = assignee_data[assignee_data['Status'] == 'Done']['Original estimate'].sum()
                completion_percentage = (completed_points / total_points * 100) if total_points > 0 else 0
                
                # Calculate category breakdown for this assignee
                category_breakdown = {}
                if 'Category' in assignee_data.columns:
                    for category, cat_group in assignee_data.groupby('Category'):
                        category_breakdown[category] = cat_group['Original estimate'].sum()
                
                # Count tasks by status
                status_counts = {}
                for status, status_group in assignee_data.groupby('Status'):
                    status_counts[status] = len(status_group)
                
                # Identify blockers (high priority, overdue, or incomplete tasks)
                today = pd.Timestamp.now().normalize()
                
                # Create blocker_list for this assignee
                blocker_list = []
                
                # Iterate through assignee's tasks
                for _, row in assignee_data.iterrows():
                    # Skip if the task is Done
                    if row['Status'] == 'Done':
                        continue
                        
                    # Initialize as None - task will only be added if it meets blocker criteria
                    blocker_type = None
                    
                    # Check for overdue tasks (red)
                    if 'Due date' in row and pd.notna(row['Due date']):
                        due_date = pd.Timestamp(row['Due date']).normalize() if isinstance(row['Due date'], str) else row['Due date']
                        if due_date < today:
                            blocker_type = 'overdue'
                    
                    # Check for high priority tasks (red)
                    if 'Priority' in row and pd.notna(row['Priority']) and row['Priority'] in ['Highest', 'High']:
                        blocker_type = 'overdue'  # High priority tasks are treated as red/overdue
                    
                    # If task isn't done and hasn't been marked as overdue, mark as incomplete (yellow)
                    if blocker_type is None and row['Status'] != 'Done':
                        blocker_type = 'incomplete'
                    
                    # Only add to blocker list if we determined it's a blocker
                    if blocker_type is not None:
                        issue_key = row['Issue key']
                        blocker_list.append({
                            'Issue key': issue_key,
                            'Summary': row['Summary'],
                            'Status': row['Status'],
                            'Due date': None if pd.isna(row.get('Due date')) else 
                                      row['Due date'].isoformat() if hasattr(row['Due date'], 'isoformat') 
                                      else str(row['Due date']),
                            'blocker_type': blocker_type,
                            'Priority': row.get('Priority', 'Normal'),
                            'issue_url': f'https://benoveltyv3.atlassian.net/browse/{issue_key}'
                        })
                
                # Add assignee data to the list
                assignees.append({
                    'name': assignee,
                    'total_tasks': len(assignee_data),
                    'total_points': total_points,
                    'completed_points': completed_points,
                    'completion_percentage': round(completion_percentage, 1),
                    'category_breakdown': category_breakdown,
                    'status_counts': status_counts,
                    'blockers': blocker_list  # This will now include all identified blockers
                })
            
            return assignees
        
        except Exception as e:
            print(f"Error in get_assignee_data: {e}")
            traceback.print_exc()
            # Return empty list on error
            return []
    
    def get_project_data(self, sprint_index: int = -1) -> list:
        """
        Get data for all projects in the specified sprint.
        Projects are identified from the Category field or Parent summary field.
        
        Args:
            sprint_index: Index of the sprint (negative for most recent)
            
        Returns:
            List of dictionaries containing project details and performance metrics
        """
        try:
            # Get data for the sprint
            sprint_data = self.get_sprint_data(sprint_index)
            
            if sprint_data.empty:
                return []
            
            # Make sure we have Category column
            if 'Category' not in sprint_data.columns:
                self.categorize_tasks(sprint_data)
                
            # Ensure we can identify projects from Parent summary
            projects = []
            project_groups = {}
            
            # First attempt: group by Parent summary if it has the project information
            if 'Parent summary' in sprint_data.columns and not sprint_data['Parent summary'].isna().all():
                # Extract project names from Parent summary (format: Category | Project)
                for _, row in sprint_data.iterrows():
                    parent_summary = str(row.get('Parent summary', ''))
                    if '|' in parent_summary:
                        # Extract project name from "Category | Project"
                        project_name = parent_summary.split('|')[1].strip()
                        
                        # Group by project name
                        if project_name not in project_groups:
                            project_groups[project_name] = []
                        
                        project_groups[project_name].append(row)
            
            # If no projects found with first method, use Categories as projects
            if not project_groups and 'Category' in sprint_data.columns:
                for category, category_group in sprint_data.groupby('Category'):
                    project_groups[category] = category_group.to_dict('records')
            
            # Process each project group
            for project_name, project_items in project_groups.items():
                # Convert list of rows to DataFrame for easier processing
                project_df = pd.DataFrame(project_items)
                
                # Calculate metrics for this project
                total_points = project_df['Original estimate'].sum()
                completed_points = project_df[project_df['Status'] == 'Done']['Original estimate'].sum()
                completion_percentage = (completed_points / total_points * 100) if total_points > 0 else 0
                
                # Count tasks by status
                status_counts = {}
                for status, status_group in project_df.groupby('Status'):
                    status_counts[status] = len(status_group)
                
                # Get assigned team members
                team_members = project_df['Assignee'].dropna().unique().tolist()
                
                # Identify blockers (high priority, overdue, or incomplete tasks)
                today = pd.Timestamp.now().normalize()
                
                # Create blocker_list for this project
                blocker_list = []
                
                # Iterate through project tasks
                for _, row in project_df.iterrows():
                    # Skip if the task is Done
                    if row['Status'] == 'Done':
                        continue
                        
                    # Initialize as None - task will only be added if it meets blocker criteria
                    blocker_type = None
                    
                    # Check for overdue tasks (red)
                    if 'Due date' in row and pd.notna(row['Due date']):
                        due_date = pd.Timestamp(row['Due date']).normalize() if isinstance(row['Due date'], str) else row['Due date']
                        if due_date < today:
                            blocker_type = 'overdue'
                    
                    # Check for high priority tasks (red)
                    if 'Priority' in row and pd.notna(row['Priority']) and row['Priority'] in ['Highest', 'High']:
                        blocker_type = 'overdue'  # High priority tasks are treated as red/overdue
                    
                    # If task isn't done and hasn't been marked as overdue, mark as incomplete (yellow)
                    if blocker_type is None and row['Status'] != 'Done':
                        blocker_type = 'incomplete'
                    
                    # Only add to blocker list if we determined it's a blocker
                    if blocker_type is not None:
                        issue_key = row['Issue key']
                        blocker_list.append({
                            'Issue key': issue_key,
                            'Summary': row['Summary'],
                            'Assignee': row.get('Assignee', 'Unassigned'),
                            'Status': row['Status'],
                            'Due date': None if pd.isna(row.get('Due date')) else 
                                      row['Due date'].isoformat() if hasattr(row['Due date'], 'isoformat') 
                                      else str(row['Due date']),
                            'blocker_type': blocker_type,
                            'Priority': row.get('Priority', 'Normal'),
                            'issue_url': f'https://benoveltyv3.atlassian.net/browse/{issue_key}'
                        })
                
                # Group tasks by assignee
                assignee_distribution = {}
                for assignee, assignee_group in project_df.groupby('Assignee'):
                    if pd.isna(assignee):
                        continue
                    assignee_distribution[assignee] = assignee_group['Original estimate'].sum()
                
                # Add project data to the list
                projects.append({
                    'name': project_name,
                    'total_tasks': len(project_df),
                    'total_points': float(total_points),  # Ensure it's JSON serializable
                    'completed_points': float(completed_points),  # Ensure it's JSON serializable
                    'completion_percentage': round(completion_percentage, 1),
                    'status_counts': status_counts,
                    'team_members': team_members,
                    'blockers': blocker_list,  # Add the blockers list for this project
                    'assignee_distribution': {k: float(v) for k, v in assignee_distribution.items()}  # Ensure it's JSON serializable
                })
            
            return projects
        except Exception as e:
            print(f"Error in get_project_data: {e}")
            import traceback
            traceback.print_exc()
            # Return empty list on error
            return []

