from django.http import HttpResponse

def index(request):
    return HttpResponse("Congratulations....You're inside blog app....")