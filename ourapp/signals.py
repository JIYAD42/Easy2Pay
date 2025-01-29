from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, Cart, Product
import qrcode
from io import BytesIO
from django.core.files import File
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.core.files.storage import default_storage

@receiver(post_save, sender=CustomUser)
def create_user_cart(sender, instance, created, **kwargs):
    if created:
        Cart.objects.create(user=instance)
