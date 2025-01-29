from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, Product, Cart, CartItem
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
    list_display = ('name', 'price', 'weight_or_quantity', 'unique_code', 'qr_code')
    fields = ('name', 'price', 'weight_or_quantity', 'image')
    actions = ['download_product_pdf_action']

    def download_product_pdf(self, product):
        
        # Generate PDF
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.setTitle(f"Product_{product.name}")
        
        # Product details
        pdf.drawString(100, 750, f"Product Name: {product.name}")
        pdf.drawString(100, 730, f"Price: ${product.price}")
        pdf.drawString(100, 710, f"Weight/Quantity: {product.weight_or_quantity}")
        
        # Product Image
        if product.image:
            pdf.drawImage(product.image.path, 100, 500, width=200, height=200)
        
        # QR Code
        if product.qr_code:
            pdf.drawImage(product.qr_code.path, 400, 500, width=100, height=100)
        
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

# Register models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Cart, CartAdmin)