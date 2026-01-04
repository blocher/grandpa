
from django.shortcuts import render
from django.http import HttpResponse

def calendar_view(request, year=None, month=None):
    # Pass initial date to template if provided
    context = {}
    if year and month:
        context['initial_date'] = f"{year}-{month:02d}-01"
    
    return render(request, 'calendar.html', context)
