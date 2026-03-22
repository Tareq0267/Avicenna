def for_her(request):
    """Make FOR_HER, tier info, and ad visibility available in templates."""
    is_special = False
    user_tier = 'free'
    show_ads = True
    has_ai = False

    if request.user.is_authenticated:
        is_special = request.user.groups.filter(name='special').exists()
        try:
            profile = request.user.profile
            user_tier = profile.subscription_tier
            show_ads = profile.show_ads()
            has_ai = profile.has_ai_access()
        except Exception:
            pass

    return {
        'FOR_HER': is_special,
        'USER_TIER': user_tier,
        'SHOW_ADS': show_ads,
        'HAS_AI_ACCESS': has_ai,
    }
