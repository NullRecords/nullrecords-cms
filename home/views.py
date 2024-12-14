from django.shortcuts import render
from wagtail.models import Page

def home_view(request):
    latest_articles = Page.objects.live().filter(show_in_menus=False).order_by('-first_published_at')[:3]  # Retrieving the latest 3 live news articles
    print(latest_articles)
    return render(request, 'home/welcome_page.html', {'latest_articles': latest_articles})




