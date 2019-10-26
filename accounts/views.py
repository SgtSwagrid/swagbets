from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, get_user_model, login, logout
from .forms import LoginForm, RegisterForm

def login_view(request):
    """Login to a new account."""

    next = request.GET.get('next')
    form = LoginForm(request.POST or None)

    if form.is_valid():

        # Login to account.
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user = authenticate(username=username, password=password)
        login(request, user)

        # Redirect to next page.
        if next:
            return redirect(next)
        return redirect('/markets/')

    # Display login page.
    return render(request, 'accounts/login.html', {'form': form})

def register_view(request):
    """Create a new account."""

    next = request.GET.get('next')
    form = RegisterForm(request.POST or None)

    if form.is_valid():

        # Create account and login.
        password = form.cleaned_data['password']
        user = form.save(commit=False)
        user.set_password(password)
        user.save()
        user = authenticate(username=user.username, password=password)
        login(request, user)

        # Redirect to next page.
        if next:
            return redirect(next)
        return redirect('/markets/')

    # Display register page.
    return render(request, 'accounts/register.html', {'form': form})

def logout_view(request):
    """Logout of current account."""

    logout(request)
    return redirect('/')