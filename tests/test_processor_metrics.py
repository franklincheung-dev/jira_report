import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from data.processor import JiraDataProcessor
from data.storage import ReportStorage


def sample_dataframe():
    data = {
        'Work type': ['Task', 'Task'],
        'Issue key': ['A-1', 'A-2'],
        'Issue id': [1, 2],
        'Summary': ['a', 'b'],
        'Assignee': ['alice', 'bob'],
        'Assignee Id': [10, 11],
        'Reporter': ['rep', 'rep'],
        'Reporter Id': [20, 20],
        'Priority': ['Medium', 'High'],
        'Status': ['Done', 'To Do'],
        'Resolution': ['Unresolved', 'Unresolved'],
        'Created': ['2024-01-01', '2024-01-02'],
        'Updated': ['2024-01-03', '2024-01-04'],
        'Due date': ['2024-01-05', '2024-01-06'],
        'Original estimate': [3600, 7200],
        'Parent': ['P1', 'P2'],
        'Parent summary': ['Billable | Project1', 'Product | Project2'],
        'Description': ['desc', 'desc'],
        'Sprint': ['Sprint 1', 'Sprint 2'],
    }
    return pd.DataFrame(data)


def test_get_sprint_data():
    df = sample_dataframe()
    proc = JiraDataProcessor(dataframe=df)
    sprint1 = proc.get_sprint_data(0)
    assert len(sprint1) == 1
    assert sprint1.iloc[0]['Issue key'] == 'A-1'


def test_calculate_metrics():
    df = sample_dataframe()
    proc = JiraDataProcessor(dataframe=df)
    sprint1 = proc.get_sprint_data(0)
    metrics = proc.calculate_sprint_metrics(sprint1)
    assert metrics['completed_story_points'] > 0
    assert metrics['total_story_points'] > 0
    assert metrics['completion_percentage'] > 0


def test_report_storage_cycle(tmp_path):
    storage = ReportStorage(storage_dir=tmp_path)
    report = {'metrics': {'sprint_name': 'Sprint 1'}}
    report_id = storage.save_sprint_report('sess1', report)
    reports = storage.list_reports('sess1')
    assert any(r['id'] == report_id for r in reports)
    loaded = storage.get_report('sess1', report_id)
    assert loaded['metrics']['sprint_name'] == 'Sprint 1'
    assert storage.delete_report('sess1', report_id)
