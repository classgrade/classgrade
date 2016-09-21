from django import forms


class AssignmentypeForm(forms.Form):
    title = forms.CharField(max_length=100,
                            label='Assignment title',
                            help_text='Max 100 char')
    description = forms.CharField(max_length=500,
                                  label='Assignment description (for students)',
                                  help_text='Max 500 char',
                                  widget=forms.Textarea)
    nb_graders = forms.IntegerField(label='number of graders',
                                    help_text='Default: 3')
    file_type = forms.CharField(max_length=20, label='Assignment file type',
                                help_text='Enter the file extension\
                                          (default:ipynb)')
    deadline_submission = forms.DateTimeField(label='Submission deadline',
                                              help_text='%Y-%m-%d %H:%M')
    deadline_grading = forms.DateTimeField(label='Grading deadline',
                                           help_text='%Y-%m-%d %H:%M')
