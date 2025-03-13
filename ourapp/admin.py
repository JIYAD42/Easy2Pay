from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, Product, Cart, CartItem, Offer
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import qrcode
import uuid
from django.urls import path

class CustomUserAdmin(BaseUserAdmin):
    """
    Custom User Admin for managing CustomUser model.
    """
    model = CustomUser
    list_display = ('email', 'username', 'is_staff', 'is_superuser')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Permissions'), {'fields': ('is_staff', 'is_superuser', 'is_active', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'is_staff', 'is_superuser', 'is_active')}
        ),
    )
    search_fields = ('email', 'username')
    ordering = ('email',)

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'weight_or_quantity', 'unique_code', 'qr_code', 'manufacturer')
    fields = ('name', 'price', 'weight_or_quantity', 'image', 'manufacturer')
    actions = ['download_product_pdf_action']

    def download_product_pdf(self, product):
        
        # Generate PDF
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.setTitle(f"Product_{product.name}")

        # Product Image
        if product.image:
            pdf.drawImage(product.image.path, 100, 650, width=100, height=100)
        
        # Product details
        pdf.drawString(210, 740, f"Product Name: {product.name}")
        pdf.drawString(210, 720, f"Price: ${product.price}")
        pdf.drawString(210, 700, f"Weight/Quantity: {product.weight_or_quantity}")
        
        
        # QR Code
        if product.qr_code:
            pdf.drawImage(product.qr_code.path, 370, 660, width=100, height=100)
        
        pdf.save()
        buffer.seek(0)

        return buffer

    def download_product_pdf_action(self, request, queryset):
        if queryset.count() == 1:  # Allow downloading for a single product
            product = queryset.first()
            pdf_buffer = self.download_product_pdf(product)

            # Send PDF as response
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename=Product_{product.name}.pdf'
            return response
        else:
            self.message_user(request, "Please select only one product for PDF download.")
    download_product_pdf_action.short_description = "Download PDF for selected product"


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

class CartAdmin(admin.ModelAdmin):
    inlines = [CartItemInline]
    list_display = ('user', 'created_at', 'updated_at')

class OfferAdmin(admin.ModelAdmin):
    list_display = ('name', 'discount_percentage', 'valid_from', 'valid_until', 'is_active')
    list_filter = ('valid_from', 'valid_until')
    search_fields = ('name', 'description')
    readonly_fields = ('is_active',)  # To display active status but not edit it
    fieldsets = (
        ("Offer Details", {
            "fields": ("name", "description", "discount_percentage"),
        }),
        ("Validity", {
            "fields": ("valid_from", "valid_until"),
        }),
    )

    def is_active(self, obj):
        return obj.is_active()
    is_active.boolean = True

# Register models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(Offer, OfferAdmin)