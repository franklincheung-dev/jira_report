"""
Visualization utilities for the Agile Project Insights Dashboard.

This module provides functions to generate the charts and visualizations
required for the dashboard.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Any, Optional


def create_completion_donut(completion_percentage: float, total_points: float, completed_points: float) -> Dict:
    """
    Create a donut chart showing sprint completion percentage.
    
    Args:
        completion_percentage: Percentage of completed hours
        total_points: Total hours planned
        completed_points: Hours completed
        
    Returns:
        Plotly figure as JSON
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=completion_percentage,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"Sprint Completion<br><span style='font-size:0.8em;color:gray'>{completed_points:.1f} of {total_points:.1f} Hours</span>", 'font': {'size': 16}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': "rgba(50, 168, 82, 0.9)"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 33], 'color': 'rgba(255, 0, 0, 0.1)'},
                {'range': [33, 66], 'color': 'rgba(255, 165, 0, 0.1)'},
                {'range': [66, 100], 'color': 'rgba(0, 128, 0, 0.1)'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig.to_json()


def create_category_chart(billable_hours: float, product_hours: float, internal_hours: float, other_hours: float) -> Dict:
    """
    Create a pie chart showing work breakdown by category.
    
    Args:
        billable_hours: Hours spent on billable work
        product_hours: Hours spent on product development
        internal_hours: Hours spent on internal initiatives
        other_hours: Hours spent on other tasks
        
    Returns:
        Plotly figure as JSON
    """
    labels = ['Billable', 'Product', 'Internal', 'Other']
    values = [billable_hours, product_hours, internal_hours, other_hours]
    
    # Filter out zero values
    non_zero_labels = []
    non_zero_values = []
    for label, value in zip(labels, values):
        if value > 0:
            non_zero_labels.append(label)
            non_zero_values.append(value)
    
    fig = go.Figure(data=[go.Pie(
        labels=non_zero_labels, 
        values=non_zero_values,
        hole=.3,
        marker_colors=[
            'rgba(50, 168, 82, 0.9)',  # Billable - Green
            'rgba(66, 133, 244, 0.9)',  # Product - Blue
            'rgba(219, 68, 55, 0.9)',  # Internal - Red
            'rgba(244, 180, 0, 0.9)'   # Other - Yellow
        ]
    )])
    
    fig.update_layout(
        title="Effort Allocation by Category",
        height=300,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig.to_json()


def create_capacity_chart(team_capacity: float, actual_utilization: float) -> Dict:
    """
    Create a stacked bar chart showing actual utilization and unallocated hours.
    
    Args:
        team_capacity: Total capacity of the team
        actual_utilization: Actual utilization
        
    Returns:
        Plotly figure as JSON
    """
    # Calculate unallocated hours
    unallocated_hours = max(0, team_capacity - actual_utilization)
    
    # Create the stacked bar chart
    fig = go.Figure(data=[
        go.Bar(
            name='Utilized',
            x=['Resource Allocation'],
            y=[actual_utilization],
            marker_color='rgba(26, 118, 255, 0.8)',
            text=[f'{round(actual_utilization, 1)} hrs ({round(actual_utilization/team_capacity*100 if team_capacity > 0 else 0, 1)}%)'],
            textposition='inside'
        ),
        go.Bar(
            name='Unallocated',
            x=['Resource Allocation'],
            y=[unallocated_hours],
            marker_color='rgba(211, 211, 211, 0.7)',
            text=[f'{round(unallocated_hours, 1)} hrs ({round(unallocated_hours/team_capacity*100 if team_capacity > 0 else 0, 1)}%)'],
            textposition='inside'
        )
    ])
    
    # Update the layout for stacked bars and add team capacity label
    fig.update_layout(
        title=f"Team Capacity: {round(team_capacity, 1)} Hours",
        height=300,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        barmode='stack',  # Change from 'group' to 'stack'
        yaxis_title="Hours",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig.to_json()


def create_velocity_trend(sprint_names: List[str], velocities: List[float], moving_avgs: Optional[List[float]] = None, 
                      projected_capacity: Optional[Dict] = None) -> Dict:
    """
    Create a line chart showing velocity trend across sprints with moving average and forecast.
    
    Args:
        sprint_names: List of sprint names
        velocities: List of velocities (hours completed) per sprint
        moving_avgs: Optional list of moving average values for all sprints
        projected_capacity: Optional dictionary containing forecast data for future sprints
        
    Returns:
        Plotly figure as JSON
    """
    fig = go.Figure()
    
    # Add velocity data line
    fig.add_trace(go.Scatter(
        x=sprint_names,
        y=velocities,
        mode='lines+markers',
        name='Velocity',
        line=dict(color='rgba(50, 168, 82, 0.9)', width=3),
        marker=dict(size=8, line=dict(width=2, color='DarkSlateGrey'))
    ))
    
    # Add overall average line
    avg_velocity = sum(velocities) / len(velocities) if velocities else 0

    # Only span the average line across historical sprints (up to current sprint)
    if velocities and sprint_names:
        start_x = sprint_names[0]
        end_x = sprint_names[len(velocities)-1]
        fig.add_shape(
            type="line",
            xref="x",
            yref="y",
            x0=start_x,
            y0=avg_velocity,
            x1=end_x,
            y1=avg_velocity,
            line=dict(
                color="Red",
                width=2,
                dash="dash",
            )
        )
    
    # Add annotation for the average
    fig.add_annotation(
        x=len(sprint_names) - 1,
        y=avg_velocity,
        text=f"Avg: {avg_velocity:.1f}",
        showarrow=False,
        yshift=10,
        xshift=5,
        font=dict(color="Red")
    )
    
    # Add moving average line for the entire series if provided
    if moving_avgs and len(moving_avgs) >= 4:
        window_size = 4
        # Create an array with actual moving average values
        ma_plot = moving_avgs
        fig.add_trace(go.Scatter(
            x=sprint_names,
            y=ma_plot,
            mode='lines+markers',
            name='Moving Avg (last 4 sprints)',
            line=dict(color='rgba(66, 133, 244, 0.9)', width=2, dash='dot'),
            marker=dict(size=6, color='rgba(66, 133, 244, 0.9)'),
        ))
        
    # Add forecast for the next two sprints if provided
    if projected_capacity and sprint_names and velocities:
        # Get forecast data
        current_sprint = projected_capacity.get('current_sprint', {})
        next_sprint = projected_capacity.get('next_sprint', {})
        next_next_sprint = projected_capacity.get('next_next_sprint', {})
        
        # Get the forecast hours for each sprint
        current_forecast = current_sprint.get('forecast_hours', 0)
        next_forecast = next_sprint.get('forecast_hours', 0)
        next_next_forecast = next_next_sprint.get('forecast_hours', 0)
        
        if current_forecast > 0 and next_forecast > 0 and next_next_forecast > 0:
            # Create names for future sprints
            last_sprint_name = sprint_names[-1]
            
            # Try to extract numeric patterns to create logical next sprint names
            # Check if the sprint name contains a year and sprint number
            import re
            
            # Pattern: "Year Sprint #" (e.g., "2025 Sprint 9")
            year_sprint_pattern = re.compile(r"(\d{4})\s+Sprint\s+(\d+)")
            match = year_sprint_pattern.match(last_sprint_name) if isinstance(last_sprint_name, str) else None
            
            if match:
                year = match.group(1)
                sprint_num = int(match.group(2))
                next_sprint_name = f"{year} Sprint {sprint_num + 1}"
                next_next_sprint_name = f"{year} Sprint {sprint_num + 2}"
            else:
                # Fallback - just add "Next" label
                next_sprint_name = "Next Sprint"
                next_next_sprint_name = "Sprint After Next"
            
            # Add forecast points to the chart
            forecast_x = [last_sprint_name, next_sprint_name, next_next_sprint_name]
            forecast_y = [current_forecast, next_forecast, next_next_forecast]
            
            fig.add_trace(go.Scatter(
                x=forecast_x,
                y=forecast_y,
                mode='lines+markers',
                name='Forecast',
                line=dict(color='rgba(255, 165, 0, 0.9)', width=2, dash='dot'),
                marker=dict(size=8, symbol='star', color='rgba(255, 165, 0, 0.9)'),
            ))
        
        # Add simple text annotation for the latest moving average without box
        if sprint_names and moving_avgs:
            latest_moving_avg = moving_avgs[-1]
            
            # Make sure the most recent moving average is displayed
            # Only add this annotation if we have at least 4 sprints of data
            if len(sprint_names) >= 4:
                fig.add_annotation(
                    x=sprint_names[-1],
                    y=latest_moving_avg,
                    text=f"Moving Avg: {latest_moving_avg:.1f}",
                    showarrow=False,
                    yshift=15,
                    xshift=0,
                    font=dict(color="rgba(66, 133, 244, 0.9)", size=11)
                )
    
    fig.update_layout(
        title="Velocity Trend",
        xaxis_title="Sprint",
        yaxis_title="Hours Completed",
        height=300,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig.to_json()


# Scope change chart function removed as per requirements


def generate_dashboard(metrics: Dict[str, Any], team_capacity: float = 0, 
                      velocity_data: Optional[Dict] = None, scope_change: Optional[Dict] = None,
                      projected_capacity: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate all charts for the dashboard.
    
    Args:
        metrics: Sprint metrics
        team_capacity: Team capacity for the sprint
        velocity_data: Velocity trend data
        scope_change: Scope change data (deprecated, kept for backwards compatibility)
        projected_capacity: Enhanced projected capacity data with next sprint and sprint after next
        
    Returns:
        Dictionary of Plotly figures as JSON for each chart
    """
    # Set defaults if no data is provided
    if velocity_data is None:
        velocity_data = {'sprint_names': [], 'velocities': []}
    
    # Set default for projected_capacity
    if projected_capacity is None:
        projected_capacity = {
            'next_sprint': {'forecast_hours': 0, 'category_breakdown': {}},
            'next_next_sprint': {'forecast_hours': 0, 'category_breakdown': {}},
            'historical': {'avg_velocity': 0, 'velocities': []}
        }
    
    # Generate charts
    completion_chart = create_completion_donut(
        metrics['completion_percentage'],
        metrics['total_story_points'],  # Now representing hours
        metrics['completed_story_points']  # Now representing hours
    )
    
    billable_chart = create_category_chart(
        metrics['billable_hours'],
        metrics.get('product_hours', 0),
        metrics.get('internal_hours', 0),
        metrics.get('other_hours', 0)
    )
    
    capacity_chart = create_capacity_chart(
        team_capacity,
        metrics['total_story_points']  # Now representing hours
    )
    
    # Pass moving averages and projected capacity to velocity trend chart if available
    moving_avgs = projected_capacity.get('historical', {}).get('moving_avgs') if projected_capacity else None
    velocity_chart = create_velocity_trend(
        velocity_data['sprint_names'],
        velocity_data['velocities'],
        moving_avgs,
        projected_capacity
    )
    
    # Empty JSON object for scope_change_chart to maintain API compatibility
    # This will be removed from the UI but kept in the API for backwards compatibility
    empty_chart = go.Figure()
    empty_chart.update_layout(
        title="",
        height=10, # Minimum allowed height is 10
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    
    return {
        'completion_chart': completion_chart,
        'billable_chart': billable_chart,
        'capacity_chart': capacity_chart,
        'velocity_chart': velocity_chart,
        'scope_change_chart': empty_chart.to_json(),
        'metrics': metrics,
        'projected_capacity': projected_capacity  # Now sending complete forecast data to frontend
    }
