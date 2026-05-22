from django.urls import path

from apps.camera.views import (
    CameraAiPreview, CameraHallChoiceView, CameraListView,
    CameraPreview, CameraRoiEditView, CameraVerifyView,
)

app_name = 'camera'
urlpatterns = [
    path("list/", CameraHallChoiceView.as_view(), name="list-halls"),
    path("list/<int:pk>/", CameraListView.as_view(), name="list"),
    path("verify/", CameraVerifyView.as_view(), name="verify"),
    path("preview/<int:pk>/", CameraPreview.as_view(), name="preview"),
    path("preview-ai/<int:pk>/", CameraAiPreview.as_view(), name="preview-ai"),
    path("roi/<int:pk>/", CameraRoiEditView.as_view(), name="roi"),
]
