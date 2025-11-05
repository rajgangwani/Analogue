from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .forms import UserRegisterForm, ProfileForm
from .models import Profile, Module


# ---------------- REGISTER VIEW ----------------
def register_view(request):
    if request.method == 'POST':
        uform = UserRegisterForm(request.POST)
        pform = ProfileForm(request.POST)

        if uform.is_valid() and pform.is_valid():
            # Create user and set password
            user = uform.save(commit=False)
            user.set_password(uform.cleaned_data['password'])
            user.save()

            # Create linked profile
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.user_type = pform.cleaned_data.get('user_type')
            profile.organization = pform.cleaned_data.get('organization')
            profile.save()

            messages.success(request, "🎉 Registration successful! You can now log in.")
            return redirect('login')
        else:
            messages.error(request, "⚠️ Please correct the highlighted errors.")
    else:
        uform = UserRegisterForm()
        pform = ProfileForm()

    return render(request, 'portal/register.html', {'uform': uform, 'pform': pform})


# ---------------- LOGIN VIEW ----------------
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"👋 Welcome back, {user.username}!")
            return redirect('home')
        else:
            messages.error(request, "❌ Invalid username or password.")

    return render(request, 'portal/login.html')


# ---------------- LOGOUT VIEW ----------------
@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You’ve been logged out successfully.")
    return redirect('login')


# ---------------- HOME VIEW ----------------
@login_required
def home_view(request):
    profile = Profile.objects.get(user=request.user)
    modules = Module.objects.all().order_by('name')

    # Automatically deactivate expired trials
    if not profile.is_premium and not profile.is_trial_active:
        profile.is_premium = False
        profile.save()

    context = {
        'profile': profile,
        'modules': modules,
    }
    return render(request, 'portal/home.html', context)


# ---------------- MODULE DETAIL VIEW ----------------
@login_required
def module_detail(request, name):
    """
    Displays details for a specific module when clicked.
    Restricts premium modules if the user is not premium or trial expired.
    """
    module = get_object_or_404(Module, name__iexact=name)
    profile = Profile.objects.get(user=request.user)

    # Restrict premium modules for non-premium users
    if module.is_premium and not profile.is_premium and not profile.is_trial_active:
        messages.warning(request, "🚫 This module requires Premium access.")
        return redirect('home')

    return render(request, 'portal/module_detail.html', {
        'module': module,
        'profile': profile
    })
