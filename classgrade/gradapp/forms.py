from django.forms import ModelForm
from gradapp.models import Assignmentype, Assignment, Evalassignment


class AssignmentypeForm(ModelForm):

    class Meta:
        model = Assignmentype
        exclude = ['prof', 'archived']


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
