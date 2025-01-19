from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def debug_view(request):
    """Простой view для проверки работоспособности"""
    return HttpResponse("Debug OK") 