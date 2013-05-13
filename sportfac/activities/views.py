# Create your views here.
from django.views.generic import DetailView, ListView

from .models import Activity

class ActivityDetailView(DetailView):
    model = Activity


class ActivityListView(ListView):
    model = Activity

