from django.urls import path

from post_migrate.views import PostMigrateView

urlpatterns = [
    path(r"", PostMigrateView.as_view(), name="post_migrate"),
]
