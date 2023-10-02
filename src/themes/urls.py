from django.urls import path
from rest_framework.routers import DefaultRouter

from themes import views
from themes.models import Area, Element, ElementDetail

themes_router = DefaultRouter()

themes_router.register(r"areas", views.AreaViewSet, "area")
themes_router.register(r"elements", views.ElementViewSet, "element")
themes_router.register(r"theme_groups", views.ThemeGroupViewSet)
themes_router.register(r"zones", views.ZoneViewSet, "zone")

urlpatterns = [
    path("areas/autocomplete/", views.AreaAutocompleteSearchView.as_view(), name="area_autocomplete"),
    path("elements/autocomplete/", views.ElementAutocompleteSearchView.as_view(), name="element_autocomplete"),
    path("details/", views.ElementDetailListCreateView.as_view(), name="detail"),
    path("details/search/", views.ElementDetailSearchView.as_view(), name="detail_search"),
    path("details/search/twitter/", views.TwitterDetailSearch.as_view(), name="detail_twitter_search"),
    path("details/autocomplete/", views.ElementDetailAutocompleteSearchView.as_view(),
         name="detail_autocomplete"),
    path("details/ambit-task/", views.ElementDetailAmbitTaskView.as_view(), name="detail_ambit_task"),
    path("details/active/", views.ElementDetailBulkActiveView.as_view(), name="detail_bulk_active"),
    path("details/delete/", views.CreateElementDetailDeleteRegisterView.as_view(), name='element_detail_delete'),
    path("details/<int:pk>/", views.ElementDetailRetrieveUpdateDestroyView.as_view(), name="detail_detail"),
    path("details/<int:pk>/check/", views.ElementDetailCheckView.as_view(), name="detail_check"),
    path("details/<int:pk>/copy/", views.ElementDetailCopyView.as_view(), name="detail_copy"),
    path("details/change/<int:id>/", views.ElementDetailChangeListView.as_view(), name="detail_change_list"),
    path("details/<int:id>/features/", views.ElementDetailFeaturesListView.as_view(), name="detail_features"),
    path("details/<int:pk>/set-order/<int:position>/",
         views.SetPositionView.as_view(model_class=ElementDetail), name="detail_set_position"),
    path("element/<int:pk>/set-order/<int:position>/",
         views.SetPositionView.as_view(model_class=Element), name="element_set_position"),
    path("area/<int:pk>/set-order/<int:position>/",
         views.SetPositionView.as_view(model_class=Area), name="area_set_position"),
    path("group/<int:pk>/tree/", views.GroupThemeTreeListView.as_view(), name="themes_tree"),
    path("tree/", views.GetThemesTreeView.as_view(), name="themes_tree"),
    path("tree/cache/", views.ThemeCacheView.as_view(), name="themes_tree_cache"),
]
urlpatterns += themes_router.urls
