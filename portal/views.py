from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from .forms import UserRegisterForm, ProfileForm
from .models import Profile, Module

import os
import shutil
import zipfile
from io import BytesIO

# === Import ML utilities ===
from .ml.dti_api import pharmalnet_train_api as run_pharmalnet_training_api  # ✅ updated import

# ---------------- REGISTER VIEW ----------------
def register_view(request):
    if request.method == 'POST':
        uform = UserRegisterForm(request.POST)
        pform = ProfileForm(request.POST)

        if uform.is_valid() and pform.is_valid():
            user = uform.save(commit=False)
            user.set_password(uform.cleaned_data['password'])
            user.save()

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

            profile = Profile.objects.get(user=user)
            modules = Module.objects.all()
            user_folder = os.path.join(str(settings.USER_DATA_ROOT), f"user_{user.id}")
            os.makedirs(user_folder, exist_ok=True)

            for module in modules:
                if module.is_free or profile.is_premium or profile.is_trial_active:
                    module_folder = os.path.join(user_folder, module.name.replace(" ", "_"))
                    os.makedirs(module_folder, exist_ok=True)

                    info_path = os.path.join(module_folder, "details.txt")
                    if not os.path.exists(info_path):
                        with open(info_path, "w", encoding="utf-8") as f:
                            f.write(
                                f"Module: {module.name}\n"
                                f"Description: {module.description or 'N/A'}\n"
                            )

            messages.success(request, f"Welcome back {user.username}! Your workspace is ready.")
            return redirect('home')

        messages.error(request, "Invalid username or password.")
    return render(request, 'portal/login.html')


# ---------------- LOGOUT VIEW ----------------
def logout_view(request):
    if request.user.is_authenticated:
        user_id = request.user.id
        user_folder = os.path.join(str(settings.USER_DATA_ROOT), f"user_{user_id}")

        root = os.path.abspath(str(settings.USER_DATA_ROOT))
        candidate = os.path.abspath(user_folder)
        if candidate.startswith(root) and os.path.exists(candidate):
            shutil.rmtree(candidate, ignore_errors=True)

    logout(request)
    messages.info(request, "👋 Logged out successfully. Your local data has been cleared.")
    return redirect('login')


# ---------------- HOME VIEW ----------------
@login_required
def home_view(request):
    profile = Profile.objects.get(user=request.user)
    modules = Module.objects.all().order_by('name')

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
    """Display module detail page (dynamic template for specific modules)."""
    module = get_object_or_404(Module, name__iexact=name)
    profile = Profile.objects.get(user=request.user)

    # Check access
    if module.is_premium and not profile.is_premium and not profile.is_trial_active:
        messages.warning(request, "🚫 This module requires Premium access.")
        return redirect('home')

    # ✅ Load custom PharmaNet template
    if module.name.lower() == "pharmal-net":
        return render(request, 'portal/pharmal_net.html', {
            'module': module,
            'profile': profile
        })

    # Default template for all other modules
    return render(request, 'portal/module_detail.html', {
        'module': module,
        'profile': profile
    })


# ---------------- DOWNLOAD USER DATA (ALL MODULES) ----------------
@login_required
def download_user_data(request):
    """Create a ZIP archive of all user data (every module folder)."""
    user_id = request.user.id
    user_folder = os.path.join(str(settings.USER_DATA_ROOT), f"user_{user_id}")

    if not os.path.exists(user_folder):
        return HttpResponse("⚠️ No user data available.", content_type="text/plain")

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(user_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, user_folder)
                zipf.write(file_path, arcname)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="user_{user_id}_modules.zip"'
    return response


# ---------------- DOWNLOAD MODULE DATA (SINGLE MODULE) ----------------
@login_required
def download_module_data(request, name):
    """Create a ZIP archive for one module folder (the one the user opened)."""
    user_id = request.user.id
    module_name = name.replace(" ", "_")
    user_folder = os.path.join(str(settings.USER_DATA_ROOT), f"user_{user_id}")
    module_folder = os.path.join(user_folder, module_name)

    if not os.path.exists(module_folder):
        return HttpResponse("⚠️ No data found for this module.", content_type="text/plain")

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(module_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, module_folder)
                zipf.write(file_path, arcname)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{module_name}_data.zip"'
    return response


# ---------------- PHARMAL-NET: ML TRAINING API ----------------
@login_required
def pharmalnet_train_api_view(request):
    """
    This wraps the backend ML API (pharmalnet_train_api from dti_api.py)
    and ensures file saving + forwarding of response.
    """
    if request.method == "POST":
        try:
            # Call backend logic directly
            return run_pharmalnet_training_api(request)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request"}, status=400)

# ---------------- PHARMAL-NET PAGES ----------------
@login_required
def pharmalnet_train(request):
    """
    Render the Pharmal-Net Training page.
    """
    profile = Profile.objects.get(user=request.user)
    module = Module.objects.filter(name__iexact="Pharmal-Net").first()

    if not module:
        messages.error(request, "Pharmal-Net module not found in database.")
        return redirect('home')

    return render(request, 'portal/pharmal_net.html', {
        'module': module,
        'profile': profile
    })


@login_required
def pharmalnet_predict(request):
    """
    Render the Pharmal-Net Prediction page.
    """
    profile = Profile.objects.get(user=request.user)
    module = Module.objects.filter(name__iexact="Pharmal-Net").first()

    if not module:
        messages.error(request, "Pharmal-Net module not found in database.")
        return redirect('home')

    return render(request, 'portal/pharmalnet_predict.html', {
        'module': module,
        'profile': profile
    })

# ---------------- PHARMAL-NET: ML PREDICTION API ----------------
@login_required
def pharmalnet_predict_api_view(request):
    """
    Handles Pharmal-Net prediction using trained ML model and user-provided data.
    """
    from .ml.dti_api import run_pharmalnet_prediction  # import your ML function

    if request.method == "POST":
        try:
            return run_pharmalnet_prediction(request)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=400)
