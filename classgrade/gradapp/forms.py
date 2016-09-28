from django.forms import ModelForm
from gradapp.models import Assignmentype, Assignment, Evalassignment
from datetimewidget.widgets import DateTimeWidget


class AssignmentypeForm(ModelForm):

    class Meta:
        model = Assignmentype
        exclude = ['prof', 'archived']
        widgets = {
            'deadline_submission':
            DateTimeWidget(usel10n=True, bootstrap_version=3),
            'deadline_grading':
            DateTimeWidget(usel10n=True, bootstrap_version=3),
        }


class LightAssignmentypeForm(ModelForm):

    class Meta:
        model = Assignmentype
        exclude = ['prof', 'archived', 'list_students']


class AssignmentForm(ModelForm):

    class Meta:
        model = Assignment
        fields = ['document']


class EvalassignmentForm(ModelForm):

    class Meta:
        model = Evalassignment
        fields = ['grade_assignment', 'grade_assignment_comments']
