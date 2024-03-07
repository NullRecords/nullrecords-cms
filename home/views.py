from django.shortcuts import render
from puput.models import Blog

def home_view(request):
    latest_articles = Blog.objects.order_by('-publish_date')[:3]  # Retrieving the latest 3 articles
    return render(request, 'home/welcome_page.html', {'latest_articles': latest_articles})