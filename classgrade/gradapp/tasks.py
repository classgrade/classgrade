# coding=utf-8
import csv
import logging
from random import shuffle
from django.core.mail import send_mail
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from xkcdpass import xkcd_password as xp
from unidecode import unidecode
from classgrade import settings
from gradapp.models import Assignmentype, Evalassignment, Evalquestion
from gradapp.models import Student, Assignment

logger = logging.getLogger(__name__)


def get_students(csv_file):
    """
    :param csv_file: csv file with list of students.\
        Each row contains: first_name, last_name, email
    :type csv_file: str
    :rtype: 2 lists existing_students and new_students [[username, email], ..]
    """

    with open(csv_file) as ff:
        reader = csv.reader(ff, delimiter=',')
        existing_students = []
        new_students = []
        for i, row in enumerate(reader):
            row = [unidecode(x.strip()) for x in row[:3]]
            username = "_".join(row[:2])
            username = username.replace(" ", "_")
            email = row[2]
            try:
                u = User.objects.get(username=username)
                Student.objects.get(user=u)
                existing_students.append([u.username, u.email])
            except ObjectDoesNotExist:
                new_students.append([username, email])
    return existing_students, new_students


def create_assignment(assignmentype_pk, existing_students, new_students):
    """
    For an assignmentype, create new students; and for new+existing students
    create their assignment row.

    :param assignmentype_pk: id of the assignmentype
    :param existing_students: list with existing students, each element is a
    list with student username and email.
    :param new_students: list with new students, each element is a list with
    student username and email.

    :type assignmentype_pk: integer
    :type existing_students: list of list of 2 strings
    :type new_students: list of list of 2 strings
    """
    words = xp.locate_wordfile()
    mywords = xp.generate_wordlist(wordfile=words, min_length=4,
                                   max_length=6)
    assignmentype = Assignmentype.objects.get(id=assignmentype_pk)
    for assignment in assignmentype.assignment_set.all():
        assignment.delete()
    for st in existing_students:
        student = Student.objects.get(user__username=st[0])
        # Get an existing assignment or create it
        Assignment.objects.get_or_create(student=student,
                                         assignmentype=assignmentype)

    for st in new_students:
        password = xp.generate_xkcdpassword(mywords, numwords=4)
        u = User.objects.create_user(st[0], st[1], password)
        student = Student.objects.create(user=u)
        # Send email
        try:
            email_new_student(u.email, u.username, password)
        except Exception as e:
            if hasattr(e, 'traceback'):
                message =  str(e.traceback)
            else:
                message = repr(e)
            logger.error('Not possible to email new student %s: %s' %
                         (u.username, message))
        # Create the assignment
        Assignment.objects.create(student=student,
                                  assignmentype=assignmentype)
    # Create associated Evalassignment
    log = create_evalassignment(assignmentype.title)
    logger.info(log)


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
                                                  evaluator=assignment.student.
                                                  user)
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
    message = (u'Bonjour et bienvenu sur Peergrade Telecom.\n\n'
               u'Pour vous connecter à Peergrade Telecom, votre login et votre '
               u'mot de passe sont:\n    %s\n    %s\nPour plus de sécurité, '
               u'modifier votre mot de passe:%s\n\nAdresse du site:%s\n'
               u'Bon travail,\n'
               u"L'équipe enseignante." %
               (student_login, student_password,
                settings.SITE_URL + 'accounts-reset/recover/',
                settings.SITE_URL))
    send_mail(subject, message, settings.EMAIL_HOST_USER,
              [student_email], fail_silently=False)


def email_confirm_upload_assignment(student_email, assignmentype_title,
                                    assignment_filename, deadline_submission):
    """
    Send an email when student uploads a new assignment file
    """
    subject = u'%s: Votre devoir a bien été soumis' % assignmentype_title
    message = (u'Bien reçu votre devoir %s.\nSi vous le souhaitez, '
               u"vous pouvez resoumettre une nouvelle version jusqu'au %s.\n\n"
               u"Bonne journée,\nL'équipe enseignante" %
               (assignment_filename, deadline_submission))
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
                        questions_grade = [evalq.grade for evalq in
                                           evalassignment.
                                           evalquestion_set.all().
                                           order_by('question')]
                        evalassignment.grade_assignment =\
                            compute_grade(questions_coeff, questions_grade)
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
            questions_grade = [evalq.grade for evalq in evalassignment.
                               evalquestion_set.all().order_by('question')]
            evalassignment.grade_assignment = compute_grade(questions_coeff,
                                                            questions_grade)
            evalassignment.save()
        else:
            return 'Question coeff are not defined'
    except Exception as e:
        return 'Oups... ' + str(e)


def compute_grade(questions_coeff, questions_grade):
    """
    Compute a grade from grade for each question (/2) and
    associated coefficients

    :param questions_coeff: list of coefficients for each question
    :param questions_grade: list of grade for each question
    """
    assign_grade = 0
    sum_coeff = 0
    for coeff, grade in zip(questions_coeff, questions_grade):
        assign_grade += coeff * grade
        sum_coeff += coeff
    return int(assign_grade * 10 * 100 / sum_coeff) / 100
