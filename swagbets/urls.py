from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('markets/', include('markets.urls')),
    path('.well-known/', include('base.urls')),
    path('', include('base.urls'))
]