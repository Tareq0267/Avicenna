def for_her(request):
    """Make FOR_HER available in templates based on user group membership."""
    is_special = False
    if request.user.is_authenticated:
        is_special = request.user.groups.filter(name='special').exists()
    return {
        'FOR_HER': is_special
    }
