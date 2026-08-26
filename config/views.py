from django.shortcuts import render

def error_404(request, exception=None):
    return render(request, "404.html", {"message": "The page or issue you are looking for could not be found."}, status=404)

def error_403(request, exception=None):
    return render(request, "403.html", {"message": "You do not have permission to access this resource or project."}, status=403)

def error_500(request):
    return render(request, "500.html", {"message": "An unexpected error occurred. Our engineers have been alerted."}, status=500)
