from django.urls import path
from . import views

urlpatterns = [
    # ── Public ──────────────────────────────────────────────────────────────
    path('',              views.home,         name='home'),
    path('menu/',         views.menu,         name='menu'),
    path('about/',        views.about,        name='about'),
    path('reservation/',  views.reservation,  name='reservation'),
    path('gallery/',      views.gallery,      name='gallery'),
    path('contact/',      views.contact,      name='contact'),
    path('policy/',       views.policy,       name='policy'),

    # ── Customer Auth & Dashboard ────────────────────────────────────────────
    path('login/',      views.customer_login,     name='login'),
    path('register/',   views.customer_register,  name='register'),
    path('dashboard/',  views.customer_dashboard, name='dashboard'),
    path('logout/',     views.custom_logout,      name='logout'),
    path('reservation/<int:pk>/cancel/', views.cancel_reservation, name='cancel_reservation'),

    # ── Custom Admin Auth & Dashboard (completely separate from /admin/) ─────
    path('admin-login/',      views.admin_login_view,    name='admin_login'),
    path('admin-dashboard/',  views.admin_dashboard_view, name='admin_dashboard'),

    # Reservation management
    path('admin-dashboard/reservation/<int:pk>/status/', views.admin_update_reservation,  name='admin_update_reservation'),
    path('admin-dashboard/reservation/<int:pk>/fine/',   views.admin_reservation_fine,    name='admin_reservation_fine'),

    # Menu Item CRUD
    path('admin-dashboard/menu/add/',          views.admin_add_menu_item,    name='admin_add_menu_item'),
    path('admin-dashboard/menu/<int:pk>/edit/', views.admin_edit_menu_item,  name='admin_edit_menu_item'),
    path('admin-dashboard/menu/<int:pk>/delete/', views.admin_delete_menu_item, name='admin_delete_menu_item'),

    # Chef CRUD
    path('admin-dashboard/chef/add/',          views.admin_add_chef,    name='admin_add_chef'),
    path('admin-dashboard/chef/<int:pk>/edit/', views.admin_edit_chef,  name='admin_edit_chef'),
    path('admin-dashboard/chef/<int:pk>/delete/', views.admin_delete_chef, name='admin_delete_chef'),

    # Gallery CRUD
    path('admin-dashboard/gallery/add/',          views.admin_add_gallery,    name='admin_add_gallery'),
    path('admin-dashboard/gallery/<int:pk>/edit/', views.admin_edit_gallery,  name='admin_edit_gallery'),
    path('admin-dashboard/gallery/<int:pk>/delete/', views.admin_delete_gallery, name='admin_delete_gallery'),

    # Table management
    path('admin-dashboard/tables/', views.admin_manage_tables, name='admin_manage_tables'),

    # ── POS (Point of Sale — in-restaurant ordering) ─────────────────────────
    path('pos/',                           views.pos_home,          name='pos_home'),
    path('pos/table/<int:table_id>/',      views.pos_order,         name='pos_order'),
    path('pos/order/<int:order_id>/add-item/',      views.pos_add_item,    name='pos_add_item'),
    path('pos/item/<int:item_id>/remove/',           views.pos_remove_item,  name='pos_remove_item'),
    path('pos/order/<int:order_id>/send-kitchen/',   views.pos_send_to_kitchen, name='pos_send_to_kitchen'),
    path('pos/order/<int:order_id>/mark-served/',    views.pos_mark_served, name='pos_mark_served'),
    path('pos/order/<int:order_id>/bill/',           views.pos_generate_bill, name='pos_generate_bill'),
    path('pos/bill/<int:bill_id>/pay/',              views.pos_mark_paid,  name='pos_mark_paid'),

    # ── Kitchen Display System ────────────────────────────────────────────────
    path('kitchen/',                            views.kitchen_display,     name='kitchen_display'),
    path('kitchen/item/<int:item_id>/update/',  views.kitchen_update_item, name='kitchen_update_item'),
]
