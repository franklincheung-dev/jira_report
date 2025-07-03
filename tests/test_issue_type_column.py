import pandas as pd
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from data.processor import JiraDataProcessor


def test_issue_type_column_standardization():
    data = {
        'Issue Type': ['Task', 'Task'],
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
    df = pd.DataFrame(data)
    proc = JiraDataProcessor(dataframe=df)
    assert 'Issue Type' in proc.data.columns
    assert 'Work type' in proc.data.columns
    assert proc.data['Issue Type'].equals(proc.data['Work type'])
