from django.forms import ModelForm
from gradapp.models import Assignmentype, Assignment


class AssignmentypeForm(ModelForm):

    class Meta:
        model = Assignmentype
        exclude = ['prof', 'archived']


class AssignmentForm(ModelForm):

    class Meta:
        model = Assignment
        fields = ['document']
