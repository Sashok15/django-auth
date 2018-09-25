import django_rq
from django.contrib.auth import login, authenticate, logout
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import render, redirect
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from .forms import SignupForm
from .tokens import account_activation_token


@login_required(login_url='/signup/')
def index(request):
    return render(request, 'auth_test/index.html')


def send_message_signup(mail_subject, message, to_email):
    email = EmailMessage(
        mail_subject, message, to=[to_email]
    )
    email.send()


def create_mail_message(request, user, form):
    current_site = get_current_site(request)
    mail_subject = 'Activate your blog account.'
    message = render_to_string('auth_test/active_email.html', {
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
    })
    to_email = form.cleaned_data.get('email')
    queue = django_rq.get_queue('default')
    queue.enqueue(send_message_signup, mail_subject=mail_subject,
                  message=message, to_email=to_email)


def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            create_mail_message(request, user, form)
        return HttpResponse('Please confirm your email address to complete the registration')
    else:
        if request.user.is_authenticated:
            return redirect('/')
        form = SignupForm()
    return render(request, 'auth_test/signup.html', {'form': form})


def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        return HttpResponse('Thank you for your email confirmation. Now you can login your account.')
    else:
        return HttpResponse('Activation link is invalid!')


def log_in(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('/')
            else:
                return HttpResponse('You don`t follow the link in your email.')
        else:

            return render(request, 'auth_test/login.html')
    else:
        return render(request, 'auth_test/login.html')


@login_required(login_url='/signup/')
def login_out(request):
    logout(request)
    return redirect('/login/')
