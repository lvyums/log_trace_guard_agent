#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from modules.training.report_gen import ReportGenerator
from modules.training.task_engine import TaskEngine

for tid in ['T001-1', 'T001-2', 'T001-3']:
    TaskEngine.record_submission(
        student_id='test_report_ref',
        scenario_id='S001',
        task_id=tid,
        score=30,
        grade='C',
        status='retry',
    )

report = ReportGenerator.generate_report(
    student_id='test_report_ref',
    scenario_id='S001',
)

print('total_tasks:', report['total_tasks'])
print('task_records count:', len(report['task_records']))
for tr in report['task_records']:
    print()
    print('  title:', tr['title'])
    print('  score:', tr['score'], 'grade:', tr['grade'])
    ref = tr.get('reference_answer')
    if ref:
        print('  reference_answer: YES')
        print('  reasoning:', ref['reasoning'][:80])
        print('  hint:', ref['hint'][:80])
        print('  required_fields:', ref['required_fields'])
        print('  answer_summary:', ref['answer_summary'][:120].replace('\n', ' | '))
    else:
        print('  reference_answer: NO')

print()
print('weaknesses:', len(report['weaknesses']))
print('improvement_plan OK:', len(report['improvement_plan']) > 0)
print()
print('ALL TESTS PASSED')
