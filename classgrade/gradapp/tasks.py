from random import shuffle
from django.core.mail import send_mail
from classgrade import settings
from gradapp.models import Assignmentype, Evalassignment


def create_evalassignment(assignmentype_title):
    """
    Create gradapp.models.evalassignment for a assignmentype (given its title)
    """
    try:
        assignmentype = Assignmentype.objects.\
            filter(title=assignmentype_title).first()
        nb_grading = assignmentype.nb_grading
        assignments = [a for a in assignmentype.assignment_set.all()]
        shuffle(assignments)
        nb_assignments = len(assignments)
        for i, assignment in enumerate(assignments):
            for igrade in range(nb_grading):
                to_be_evaluated = assignments[(i + 1 + igrade) % nb_assignments]
                if to_be_evaluated.student == assignment.student:
                    return 'Oups... too few students compare to the number'\
                        'of assignment each student must evaluate'
                Evalassignment.objects.create(assignment=to_be_evaluated,
                                              evaluator=assignment.student)
        return 'Evalassignments create for assignment %s' % assignmentype_title
    except Exception as e:
        return 'Oups... ' + str(e)


def email_new_student(student_email, student_login, student_password):
    """
    Send an email when creating a new student. This email contains his/her
    login and password, which need to be reset
    """
    subject = 'Peergrade Telecom'
    message = (u'Bonjour,\n '
               u'pour vous connecter à Peergrade Telecom, votre login et mot '
               u'de passe sont:\n%s\n%s\n Pensez à modifier votre mot de passe'
               u' sur le site:\n%s\n' % (student_login, student_password,
                                         settings.SITE_URL))
    send_mail(subject, message, settings.EMAIL_HOST_USER,
              [student_email], fail_silently=False)
