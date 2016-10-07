# coding=utf-8
from random import shuffle
from django.core.mail import send_mail
from classgrade import settings
from gradapp.models import Assignmentype, Evalassignment, Evalquestion


def create_evalassignment(assignmentype_title):
    """
    Create gradapp.models.evalassignment for a assignmentype (given its title)
    """
    try:
        assignmentype = Assignmentype.objects.\
            filter(title=assignmentype_title).first()
        nb_grading = assignmentype.nb_grading
        nb_questions = assignmentype.nb_questions
        assignments = [a for a in assignmentype.assignment_set.all()]
        shuffle(assignments)
        nb_assignments = len(assignments)
        for i, assignment in enumerate(assignments):
            for igrade in range(nb_grading):
                to_be_evaluated = assignments[(i + 1 + igrade) % nb_assignments]
                if to_be_evaluated.student == assignment.student:
                    return 'Oups... too few students compare to the number'\
                        'of assignment each student must evaluate'
                e = Evalassignment.objects.create(assignment=to_be_evaluated,
                                                  evaluator=assignment.student)
                for iq in range(nb_questions):
                    Evalquestion.objects.create(evalassignment=e,
                                                question=(iq + 1))
        return 'Evalassignments create for assignment %s' % assignmentype_title
    except Exception as e:
        return 'Oups... ' + str(e)


def email_new_student(student_email, student_login, student_password):
    """
    Send an email when creating a new student. This email contains his/her
    login and password, which need to be reset
    """
    subject = 'Peergrade Telecom'
    message = (u'Bonjour et bienvenus sur Peergrade Telecom.\n\n'
               u'Pour vous connecter à Peergrade Telecom, votre login et votre '
               u'mot de passe sont:\n    %s\n    %s\nPour plus de sécurité, '
               u'modifier votre mot de passe:%s\n\nAdresse du site:%s' %
               (student_login, student_password,
                settings.SITE_URL + 'accounts-reset/recover/',
                settings.SITE_URL))
    send_mail(subject, message, settings.EMAIL_HOST_USER,
              [student_email], fail_silently=False)


def compute_grades_assignmentype(assignmentype_id):
    """
    Compute grades of an assignmentype if question coefficients have been set
    """
    try:
        assignmentype = Assignmentype.objects.get(id=assignmentype_id)
        if assignmentype.questions_coeff:
            questions_coeff = assignmentype.questions_coeff
            for assignment in assignmentype.assignment_set.all():
                for evalassignment in assignment.evalassignment_set.all():
                    if evalassignment.is_questions_graded:
                        assign_grade = 0
                        sum_coeff = 0
                        for coeff, evalq\
                            in zip(questions_coeff, evalassignment.
                                   evalquestion_set.all().order_by('question')):
                            assign_grade += coeff * evalq.grade
                            sum_coeff += coeff
                        evalassignment.grade_assignment = int(assign_grade *
                                                              10 * 100 /
                                                              sum_coeff) / 100
                        evalassignment.save()
        else:
            return 'Question coeff are not defined'
    except Exception as e:
        return 'Oups... ' + str(e)


def compute_grade_evalassignment(evalassignment_id):
    """
    Compute evalassignment.grade_assignment of
    evalassignment(id=evalassignment_id) if question coeff of associated
    assignmentype have been defined
    """
    try:
        evalassignment = Evalassignment.objects.get(id=evalassignment_id)
        questions_coeff = evalassignment.assignment.assignmentype.\
            questions_coeff
        if questions_coeff:
            assign_grade = 0
            for coeff, evalq in zip(questions_coeff, evalassignment.
                                    evalquestion_set.all().
                                    order_by('question')):
                assign_grade = assign_grade + coeff * evalq.grade
            evalassignment.grade_assignment = assign_grade
            evalassignment.save()
        else:
            return 'Question coeff are not defined'
    except Exception as e:
        return 'Oups... ' + str(e)
