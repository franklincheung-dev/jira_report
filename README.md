# Agile Project Insights Dashboard

A web application that provides a clear and intuitive visualization of software development project statistics from Jira data.

## Overview

The Agile Project Insights Dashboard is designed to give senior management a high-level "big picture" overview of project progress, team performance, and potential risks, without the need to navigate the complexities of the native Jira interface.

## Features

- **Upload Jira CSV exports**: Easily upload your standard Jira issues CSV export.
- **Sprint selection**: Select past, current, or future sprints for analysis.
- **Task categorization**: Automatic categorization into "Billable", "Product", "Internal", and "Other" based on Parent Summary format.
- **Sprint metrics**: View completion percentage, work category breakdown, and capacity utilization.
- **Key blockers**: Quickly identify high-priority issues that need attention.
- **Resource utilization**: Analyze team member workload and performance.
- **Velocity trend**: Track performance over multiple sprints with category breakdown.
- **Scope change analysis**: Understand changes within the active sprint.
- **Future capacity forecast**: Get data-driven projections for upcoming sprints.
- **Report archiving**: Save snapshots of sprint reports for historical reference.
- **PDF export**: Export the dashboard for presentations or sharing.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. Clone this repository or download the source code.

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
```

3. Install the dependencies:

```bash
pip install -r requirements.txt
```

### Running the Application

1. Run the application:

```bash
python run.py
```

2. Open a web browser and navigate to: `http://localhost:5000`

3. Upload a Jira CSV export file to get started.

### Run with Docker

1. Build the container:
```bash
docker build -t agile-dashboard .
```
2. Run the container:
```bash
docker run -p 5001:5001 agile-dashboard
```
The app will be available at http://localhost:5001


## Usage

1. **Upload Data**: Use the sidebar to upload your Jira CSV export file.
2. **Select Sprint**: Choose the sprint you want to analyze from past, current, or future sprints.
3. **Configure**: Customize settings if needed. The system will automatically categorize tasks based on Parent Summary format.
4. **Generate Dashboard**: Click the "Generate Dashboard" button to view the insights.
5. **Analyze**: Review the sprint completion, category breakdown, resource utilization, and other metrics.
6. **Archive Reports**: Save sprint reports for historical reference.
7. **Export**: Use the PDF export button to share reports with stakeholders.

## Project Structure

- `src/data/`: Data processing components
- `src/visualization/`: Chart and visualization utilities
- `src/app/`: Flask web application
- `templates/`: HTML templates for the web interface
- `static/`: CSS and JavaScript files

## Requirements

The application expects a standard Jira CSV export with the following columns:
- Work type
- Issue key
- Issue id
- Summary
- Assignee
- Assignee Id
- Reporter
- Reporter Id
- Priority
- Status
- Resolution
- Created
- Updated
- Due date
- Original estimate
- Parent
- Parent summary
- Description
- Sprint (can have multiple Sprint columns like Sprint.1, Sprint.2, etc. for tasks associated with multiple sprints)

The enhanced version automatically categorizes tasks based on Parent Summary format:
- Tasks with "[Billable]" or "(Billable)" in Parent Summary are categorized as "Billable"
- Tasks with "[Product]" or "(Product)" in Parent Summary are categorized as "Product"
- Tasks with "[Internal]" or "(Internal)" in Parent Summary are categorized as "Internal"
- All other tasks are categorized as "Other"

The application can handle tasks associated with multiple sprints, which is common in Jira exports where a task appears in several sprints. The system automatically consolidates all sprint assignments for accurate sprint-based reporting.

## Environment Variables & Data Privacy

- **Never commit sensitive data**: Do not store secrets, API keys, or credentials in your code or commit them to the repository.
- **Use a `.env` file**: Store all secrets and environment-specific settings in a `.env` file (see `.env.example` for the format). This file is already excluded from version control by `.gitignore`.
- **Data files**: All uploaded data, reports, and generated files are ignored by default and will not be pushed to GitHub.
- **If you add new config or credentials**: Always update `.env.example` and keep `.gitignore` up to date.

## Configuration Example

Copy `.env.example` to `.env` and fill in your actual values:

```bash
cp .env.example .env
```

Then edit `.env` as needed for your deployment.
