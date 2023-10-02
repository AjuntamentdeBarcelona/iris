from django.urls import path
from rest_framework.routers import DefaultRouter

from profiles import views

profiles_router = DefaultRouter()

urlpatterns = [
    path(r"permissions/", views.PermissionListView.as_view(), name="permissions"),
    path(r"user-permissions/", views.UserPermissionListView.as_view(), name="user_permissions"),
    path(r"user-groups/", views.UserGroupView.as_view(), name="user_group"),
    path(r"user-groups/set/", views.UserGroupSetView.as_view(), name="user_group_set"),
    path(r"groups/rebuildtree/", views.GroupsRebuildTreeView.as_view(), name="groups_rebuild_tree"),
    path(r"groups/input_channels/", views.GroupInputChannelsView.as_view(), name="groups_input_channels"),
    path(r"groups/tree/", views.GetGroupsTreeView.as_view(), name="groups_tree"),
    path(r"groups/<int:pk>/ambit/", views.GroupAmbitView.as_view(), name="groups_ambit"),
    path(r"groups/set-profile-to-all/<int:pk>/", views.SetProfileToAll.as_view(), name="setup_groups"),
    path(r"groups/delete/", views.CreateGroupDeleteRegisterView.as_view(), name="groups_delete"),
    path(r"profiles-data-checks/", views.ProfilesDataChecksView.as_view(), name="profiles_data_checks"),
    path(r"profile-preferences/", views.ProfilePreferencesView.as_view(), name="profile_preferences_retrieve"),
    path(r"preferences-options/", views.PreferencesOptionsView.as_view(), name="profile_preferences_options"),
    path(r"profile-users/<int:profile_id>/", views.ProfileUsersView.as_view(), name="profile_users")
]

profiles_router.register(r"users", views.UserViewSet)
profiles_router.register(r"groups", views.GroupViewSet, basename='group_view_set')
profiles_router.register(r"responsible", views.GroupResponsibleViewSet, basename='group_responsible_view_set')
profiles_router.register(r"profiles", views.ProfileViewSet)
urlpatterns += profiles_router.urls
