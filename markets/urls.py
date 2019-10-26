from django.urls import path
from . import views

urlpatterns = [

    # Browse all propositions.
    path('', views.browse_view),

    # Funds, stakes and orders.
    path('balances', views.balances_view),

    # Cancel order.
    path('cancel/<int:id>', views.cancel_view),

    # Information page for proposition.
    path('<str:code>', views.proposition_view),
    path('<str:code>/history', views.history_view)
]