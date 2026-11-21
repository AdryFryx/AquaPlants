import json

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..models import InformeFalla, Medicion


def render_dashboard_supervisor(request):
    usuario_actual = request.user
    informes = InformeFalla.objects.filter(
        supervisor_asignado=usuario_actual,
        estado='PENDIENTE'
    ).select_related('dispositivo', 'dispositivo__usuario_encargado')

    informes_resueltos = InformeFalla.objects.filter(
        supervisor_asignado=usuario_actual,
        estado='RESUELTO'
    ).order_by('-fecha_resolucion')[:15]

    datos_graficos = {}
    for informe in informes:
        mediciones = list(Medicion.objects.filter(dispositivo=informe.dispositivo).order_by('-timestamp')[:15])
        mediciones.reverse()

        datos_graficos[informe.id] = {
            'etiquetas': [m.timestamp.strftime('%H:%M') for m in mediciones],
            'temperatura': [m.temperatura if m.temperatura else 0 for m in mediciones],
            'ph': [m.ph if m.ph else 0 for m in mediciones],
            'agua': [m.nivel_agua if m.nivel_agua else 0 for m in mediciones],
            'nutriente_a': [m.nutriente_a if m.nutriente_a else 0 for m in mediciones],
            'nutriente_b': [m.nutriente_b if m.nutriente_b else 0 for m in mediciones]
        }

    contexto = {
        'rol': 'Supervisor',
        'informes_pendientes': informes,
        'informes_resueltos': informes_resueltos,
        'datos_graficos_json': json.dumps(datos_graficos)
    }
    return render(request, 'api/dashboard_supervisor.html', contexto)


@login_required(login_url='login_web')
@require_POST
def resolver_informe(request):
    informe_id = request.POST.get('informe_id')
    comentario = request.POST.get('comentario', 'Resuelto sin comentarios adicionales.')

    informe = InformeFalla.objects.get(id=informe_id)
    informe.estado = 'RESUELTO'
    informe.comentario_resolucion = comentario
    informe.fecha_resolucion = timezone.now()
    informe.save()

    messages.success(request, "¡Ticket cerrado exitosamente con tu feedback guardado!")
    return redirect('dashboard_admin')