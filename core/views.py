import json
import logging
from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Count
from django.views.decorators.http import require_POST

from .forms import LoginForm, UserCreateForm, UserEditForm
from .models import CustomUser, Section, Subsection, WasteItem

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Role decorators
# ---------------------------------------------------------------------------

def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in roles and not request.user.is_superuser:
                return render(request, 'core/403.html', status=403)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


admin_required = role_required('admin')
staff_required = role_required('admin', 'employee')


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm(request.POST or None)
    error = None

    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        error = 'Invalid username or password.'

    return render(request, 'core/login.html', {'form': form, 'error': error})


def logout_view(request):
    logout(request)
    return redirect('login')


# ---------------------------------------------------------------------------
# Main pages
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    total_items = WasteItem.objects.count()
    from django.utils import timezone
    today = timezone.now().date()
    today_items = WasteItem.objects.filter(timestamp__date=today).count()
    active_users = CustomUser.objects.filter(is_active=True).count()
    active_sections = Section.objects.count()
    recent = WasteItem.objects.select_related('section', 'subsection')[:10]
    context = {
        'total_items': total_items,
        'today_items': today_items,
        'active_users': active_users,
        'active_sections': active_sections,
        'recent_items': recent,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
@staff_required
def geomap(request):
    sections = Section.objects.prefetch_related('subsections').all()
    return render(request, 'core/geomap.html', {'sections': sections})


@login_required
@staff_required
def monitoring(request):
    sections = Section.objects.all()
    subsections = Subsection.objects.select_related('section').all()
    return render(request, 'core/monitoring.html', {
        'sections': sections,
        'subsections': subsections,
    })


# ---------------------------------------------------------------------------
# User management (admin only)
# ---------------------------------------------------------------------------

@login_required
@admin_required
def user_list(request):
    users = CustomUser.objects.select_related('section', 'subsection').all()
    return render(request, 'core/users/list.html', {'users': users})


@login_required
@admin_required
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('user_list')
    return render(request, 'core/users/create.html', {'form': form})


@login_required
@admin_required
def user_edit(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    form = UserEditForm(request.POST or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('user_list')
    return render(request, 'core/users/edit.html', {'form': form, 'target_user': user})


@login_required
@admin_required
@require_POST
def user_deactivate(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    user.is_active = False
    user.save(update_fields=['is_active'])
    return redirect('user_list')


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------

@login_required
def api_waste_stats(request):
    qs = WasteItem.objects.values('waste_type').annotate(count=Count('id'))
    data = {item['waste_type']: item['count'] for item in qs}
    # Include all types, defaulting missing ones to 0
    all_types = [c[0] for c in WasteItem._meta.get_field('waste_type').choices]
    result = {t: data.get(t, 0) for t in all_types}
    return JsonResponse(result)


@login_required
def api_recent_items(request):
    items = WasteItem.objects.select_related('section', 'subsection', 'captured_by')[:10]
    data = []
    for item in items:
        data.append({
            'id': item.pk,
            'waste_type': item.waste_type,
            'waste_type_label': item.get_waste_type_display(),
            'properties': item.properties,
            'properties_label': item.get_properties_display(),
            'confidence': item.confidence,
            'section': item.section.name if item.section else '',
            'subsection': item.subsection.name if item.subsection else '',
            'captured_by': item.captured_by.username if item.captured_by else '',
            'timestamp': item.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        })
    return JsonResponse({'items': data})


@login_required
def api_geomap_data(request):
    subsections = Subsection.objects.annotate(item_count=Count('wasteitem')).select_related('section')
    result = []
    for sub in subsections:
        breakdown = {}
        qs = WasteItem.objects.filter(subsection=sub).values('waste_type').annotate(count=Count('id'))
        for row in qs:
            breakdown[row['waste_type']] = row['count']
        result.append({
            'id': sub.pk,
            'name': sub.name,
            'section': sub.section.name,
            'latitude': sub.latitude,
            'longitude': sub.longitude,
            'total': sub.item_count,
            'breakdown': breakdown,
        })
    return JsonResponse({'subsections': result})


@login_required
@require_POST
def api_add_waste_item(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    waste_type = payload.get('waste_type', 'msw')
    properties = payload.get('properties', 'biodegradable')
    confidence = 0.0
    try:
        confidence = float(payload.get('confidence', 0.0))
    except (TypeError, ValueError):
        logger.warning('Invalid confidence value received: %r', payload.get('confidence'))

    valid_types = [c[0] for c in WasteItem._meta.get_field('waste_type').choices]
    valid_props = [c[0] for c in WasteItem._meta.get_field('properties').choices]
    if waste_type not in valid_types or properties not in valid_props:
        return JsonResponse({'error': 'Invalid waste_type or properties'}, status=400)

    section = None
    subsection = None
    section_id = payload.get('section_id')
    subsection_id = payload.get('subsection_id')
    if section_id:
        section = Section.objects.filter(pk=section_id).first()
    if subsection_id:
        subsection = Subsection.objects.filter(pk=subsection_id).first()

    item = WasteItem.objects.create(
        waste_type=waste_type,
        properties=properties,
        confidence=confidence,
        section=section,
        subsection=subsection,
        captured_by=request.user if request.user.is_authenticated else None,
        notes=payload.get('notes', ''),
    )
    return JsonResponse({
        'id': item.pk,
        'waste_type': item.waste_type,
        'waste_type_label': item.get_waste_type_display(),
        'properties': item.properties,
        'properties_label': item.get_properties_display(),
        'confidence': item.confidence,
        'section': item.section.name if item.section else '',
        'subsection': item.subsection.name if item.subsection else '',
        'timestamp': item.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
    })
