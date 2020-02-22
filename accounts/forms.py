from django import forms
from django.contrib.auth import authenticate, get_user_model

User = get_user_model()

class LoginForm(forms.Form):
    """Form used to login to existing account."""

    username = forms.CharField(widget=forms.TextInput({
        'static': 'Username',
        'class': 'text-center'
    }))
    password = forms.CharField(widget=forms.PasswordInput({
        'static': 'Password',
        'class': 'text-center'
    }))

    def clean(self, *args, **kwargs):

        # Get username and password from form input.
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        # Ensure appropriate values are actually given.
        if not username: raise forms.ValidationError('No username given.')
        elif not password: raise forms.ValidationError('No password given.')
        
        # Get user associated with given login details.
        user = authenticate(username=username, password=password)

        # Ensure user is valid.
        if not user:
            raise forms.ValidationError('Incorrect username or password.')
        elif not user.check_password(password):
            raise forms.ValidationError('Incorrect username or password.')
        elif not user.is_active:
            raise forms.ValidationError('Given user is inactive.')

        return super(LoginForm, self).clean(*args, **kwargs)

class RegisterForm(forms.ModelForm):
    """Form used to register new account."""

    username = forms.CharField(widget=forms.TextInput({
        'static': 'Username',
        'class': 'text-center'
    }))
    email = forms.EmailField(widget=forms.TextInput({
        'static': 'Email',
        'class': 'text-center'
    }))
    password = forms.CharField(widget=forms.PasswordInput({
        'static': 'Password',
        'class': 'text-center'
    }))

    def clean(self, *args, **kwargs):

        # Get username and email from form input.
        username = self.cleaned_data['username']
        email = self.cleaned_data['email']

        # Ensure given values are unique.
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Given username is already taken.')
        elif User.objects.filter(email=email).exists():
            raise forms.ValidationError('Given email address is already taken.')

        return super(RegisterForm, self).clean(*args, **kwargs)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']