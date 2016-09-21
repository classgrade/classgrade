from django.forms import ModelForm
from gradapp.models import Assignmentype


class AssignmentypeForm(ModelForm):

    class Meta:
        model = Assignmentype
        exclude = ['prof']
