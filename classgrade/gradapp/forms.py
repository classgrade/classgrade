from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from gradapp.models import Assignmentype, Assignment
from datetimewidget.widgets import DateTimeWidget


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
        for i in range(1, nb_questions + 1):
            self.fields['coeff_%s' % i] = forms.\
                FloatField(required=True, validators=[MinValueValidator(0)])
            self.fields['coeff_%s' % i].label = 'Q%i' % i


class NbQuestionForm(forms.Form):

    def __init__(self, *args, **kwargs):
        nb_questions = kwargs.pop('nb_questions')
        super(NbQuestionForm, self).__init__(*args, **kwargs)
        self.fields['question'] = forms.IntegerField(
            required=True, validators=[MinValueValidator(1),
                                       MaxValueValidator(nb_questions + 1)])
        self.fields['question'].label = 'Question number'
        self.fields['question'].help_text = ('(value between 1 and %s)' %
                                             (nb_questions + 1))
