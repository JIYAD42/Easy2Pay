from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth import get_user_model
from django.db import models
import qrcode
from io import BytesIO
from PIL import Image
from django.core.files import File
from django.conf import settings
from decimal import Decimal
import uuid
from django.core.files.base import ContentFile
from django.utils.timezone import now

class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field is required.")
        if not username:
            raise ValueError("The Username field is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, username, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    points = models.PositiveIntegerField(default=0)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    weight_or_quantity = models.CharField(max_length=255)
    image = models.ImageField(upload_to='products/')
    unique_code = models.CharField(max_length=255, unique=True, blank=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)
    is_paid = models.BooleanField(default=False)
    manufacturer = models.CharField(max_length=255, default="manfacturer")


    def save(self, *args, **kwargs):
        # Generate unique code
        if not self.unique_code:
            self.unique_code = str(uuid.uuid4()).replace('-', '')[:12]
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(self.unique_code)
        qr.make(fit=True)
        qr_img = qr.make_image(fill='black', back_color='white')
        buffer = BytesIO()
        qr_img.save(buffer)
        qr_code_file = ContentFile(buffer.getvalue())
        self.qr_code.save(f'{self.unique_code}.png', qr_code_file, save=False)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def total_price(self):
        """
        Calculate the total price of all items in the cart.
        """
        return sum(item.total_price() for item in self.items.all())

    def __str__(self):
        return f"Cart for {self.user.email}"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, 
        on_delete=models.CASCADE, 
        related_name="items"
    )
    product = models.ForeignKey(
        'Product', 
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)

    def total_price(self):
        """
        Calculate the total price of this item based on the quantity.
        """
        return Decimal(self.quantity) * self.product.price

    def __str__(self):
        return f"{self.quantity} of {self.product.name}"

class Offer(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    id = models.CharField(max_length=255, unique=True, blank=True, primary_key=True)

    def save(self, *args, **kwargs):
        # Generate unique code
        if not self.id:
            self.id = str(uuid.uuid4()).replace('-', '')[:12]
        super().save(*args, **kwargs)

    def is_active(self):
        """
        Check if the offer is currently active.
        """
        from django.utils.timezone import now
        return self.valid_from <= now() <= self.valid_until

    def __str__(self):
        return self.name

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    razorpay_order_id = models.CharField(max_length=255, unique=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    is_paid = models.BooleanField(default=False)
    offer = models.ForeignKey(Offer, null=True, blank=True, on_delete=models.SET_NULL)  # Add this line
    redeemed_points = models.PositiveIntegerField(default=0)  # Add this line
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.razorpay_order_id} - {'Paid' if self.is_paid else 'Pending'}"
    
User = get_user_model()
class PointTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="point_transactions")
    points = models.IntegerField()  # Can be positive (earned) or negative (spent)
    date = models.DateTimeField(default=now)
    description = models.CharField(max_length=255, blank=True, null=True)  # Optional description

    def __str__(self):
        return f"{self.user.email} - {self.points} points on {self.date}"