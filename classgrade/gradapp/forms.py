from django import forms
from gradapp.models import Assignmentype, Assignment
from datetimewidget.widgets import DateTimeWidget
from django.contrib.postgres.forms import SplitArrayField


class AssignmentypeForm(forms.ModelForm):

    class Meta:
        model = Assignmentype
        exclude = ['prof', 'archived', 'questions_coeff']
        widgets = {
            'deadline_submission':
            DateTimeWidget(usel10n=True, bootstrap_version=3,
                           options={'minuteStep': 59}),
            'deadline_grading':
            DateTimeWidget(usel10n=True, bootstrap_version=3,
                           options={'minuteStep': 59}),
        }


class LightAssignmentypeForm(forms.ModelForm):

    class Meta:
        model = Assignmentype
        exclude = ['prof', 'archived', 'list_students', 'questions_coeff',
                   'nb_questions']


class AssignmentForm(forms.ModelForm):

    class Meta:
        model = Assignment
        fields = ['document']


class CoeffForm(forms.Form):

    def __init__(self, *args, **kwargs):
        nb_questions = kwargs.pop('nb_questions')
        super(CoeffForm, self).__init__(*args, **kwargs)
        self.fields['coeff'] = SplitArrayField(forms.FloatField(required=True),
                                               size=nb_questions,
                                               remove_trailing_nulls=False)
        self.fields['coeff'].label = 'Coeff for Q1, ..., Q%s' % nb_questions


# class EvalassignmentForm(ModelForm):
#
#     class Meta:
#         model = Evalassignment
#         fields = ['grade_assignment', 'grade_assignment_comments']
#         widgets = {'grade_assignment': NumberInput(attrs={'min': 0,
#                                                           'max': 20})}
