from backend import GROUP_NAME

from braces.views import GroupRequiredMixin, LoginRequiredMixin


class BackendMixin(GroupRequiredMixin, LoginRequiredMixin):
    """Mixin for backend. Ensure that the user is logged in and is a member 
       of sports managers group."""
    group_required = GROUP_NAME
