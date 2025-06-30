import pandas as pd
from src.data import JiraDataProcessor


def test_categorize_tasks():
    data = {
        'Issue Type': ['Task'] * 4,
        'Issue key': ['1', '2', '3', '4'],
        'Issue id': [1, 2, 3, 4],
        'Summary': ['a', 'b', 'c', 'd'],
        'Assignee': ['user'] * 4,
        'Assignee Id': [10] * 4,
        'Reporter': ['rep'] * 4,
        'Reporter Id': [20] * 4,
        'Priority': ['Medium'] * 4,
        'Status': ['To Do'] * 4,
        'Resolution': ['Unresolved'] * 4,
        'Created': ['2024-01-01'] * 4,
        'Updated': ['2024-01-02'] * 4,
        'Due date': ['2024-01-03'] * 4,
        'Original estimate': [3600] * 4,
        'Parent': ['P'] * 4,
        'Parent summary': [
            'Billable | Project1',
            'Product | Project2',
            'Internal | Project3',
            'Something else'
        ],
        'Description': ['desc'] * 4,
        'Sprint': ['Sprint 1'] * 4,
    }
    df = pd.DataFrame(data)
    processor = JiraDataProcessor(dataframe=df)
    processor.categorize_tasks()
    expected = ['Billable', 'Product', 'Internal', 'Other']
    assert processor.data['Category'].tolist() == expected
