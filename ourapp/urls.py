from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('passreset/', views.forgot_password_view, name='passreset'),
    path('login/', views.login_view, name='login'),
    path('home/', views.home_view, name='home'),
    path('scan/', views.scan_qr_view, name='scan'),
    path('scan/check_qr/', views.check_qr, name='check_qr'),
    path('cart/', views.cart_detail, name='cart'),
    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('create_order/', views.create_order, name='create_order'),
    path('payment_success/', views.payment_success, name='payment_success'),
    path('payment_failure/', views.payment_failure, name='payment_failure'),
    path('payment_confirm/', views.payment_confirm, name='payment_confirm'),
    path('payment/', views.payment_view, name='payment'),
    path('offers/', views.offers_list, name='offers'),
    path('points/', views.rdpt, name='points'),
    path('profile-image/<str:name>/', views.generate_profile_image, name='profile_image'),
    path('generate-receipt/<str:order_id>/', views.generate_receipt, name='generate_receipt'),
    path("remove_from_cart/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),
]
