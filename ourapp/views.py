from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User 
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import EmailForm, OTPVerificationForm, FinalSignupForm, CustomUserLoginForm, ResetPasswordForm
from django.core.mail import send_mail
from django.core.cache import cache
from django.conf import settings
import random
from django.http import HttpResponse
from .models import Product, Cart, CartItem, Order, PointTransaction
import razorpay
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from .models import Offer
from django.utils.timezone import now
from decimal import Decimal
from PIL import Image, ImageDraw, ImageFont
import io
from reportlab.pdfgen import canvas

def send_email_otp(email, otp):
    subject = "Your OTP for easy2pay Password Reset"
    message = f"Your OTP for resetting your password is {otp}. Please do not share it with anyone."
    from_email = settings.EMAIL_HOST_USER
    try:
        send_mail(subject, message, from_email, [email])
    except Exception as e:
        raise Exception("Failed to send OTP. Please try again later.")

def forgot_password_view(request):
    if request.method == 'POST':
        step = request.session.get('forgot_password_step', 1)

        if step == 1:
            form = EmailForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                User = get_user_model()
                if not User.objects.filter(email=email).exists():
                    messages.error(request, "Email not found.")
                    return render(request, 'auth.html', {'form': form, 'form_title': 'Forgot Password', 'button_text': 'Next'})
                
                otp = random.randint(100000, 999999)
                cache.set(f"otp_{email}", otp, timeout=300)
                try:
                    send_email_otp(email, otp)
                except Exception as e:
                    messages.error(request, str(e))
                    return render(request, 'auth.html', {'form': form, 'form_title': 'Forgot Password', 'button_text': 'Next'})
                
                request.session['email'] = email
                request.session['forgot_password_step'] = 2
                return redirect('passreset')

        elif step == 2:
            form = OTPVerificationForm(request.POST)
            if form.is_valid():
                email = request.session.get('email')
                entered_otp = form.cleaned_data['otp']
                cached_otp = cache.get(f"otp_{email}")
                
                if str(entered_otp) == str(cached_otp):
                    request.session['forgot_password_step'] = 3
                    return redirect('passreset')
                else:
                    messages.error(request, "Invalid OTP. Please try again.")
        
        elif step == 3:
            form = ResetPasswordForm(request.POST)
            if form.is_valid():
                email = request.session.get('email')
                new_password = form.cleaned_data['password']
                User = get_user_model()
                user = User.objects.get(email=email)
                user.password = make_password(new_password)
                user.save()
                
                request.session.pop('forgot_password_step', None)
                request.session.pop('email', None)
                messages.success(request, "Password reset successfully. You can now log in.")
                return redirect('login')
    
    else:
        step = request.session.get('forgot_password_step', 1)
        form = EmailForm() if step == 1 else OTPVerificationForm() if step == 2 else ResetPasswordForm()
    
    return render(request, 'auth.html', {
        'form': form,
        'form_title': 'Forgot Password',
        'button_text': 'Next' if step < 3 else 'Reset Password',
        'toggle_text': 'Remembered your password? Login',
        'toggle_url': '/easy2pay/login/',
    })


def signup_view(request):
    if request.method == 'POST':
        step = request.session.get('signup_step', 1)

        if step == 1:
            form = EmailForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                otp = random.randint(100000, 999999)
                cache.set(f"otp_{email}", otp, timeout=300)
                try:
                    send_email_otp(email, otp)
                except Exception as e:
                    messages.error(request, str(e))
                    return render(request, 'auth.html', {
                        'form': form,   
                        'form_title': 'Signup',
                        'button_text': 'Next',
                        'toggle_text': 'Already have an account? Login',
                        'toggle_url': '/easy2pay/login/',
                    })
                request.session['email'] = email
                request.session['signup_step'] = 2
                return redirect('signup')

        elif step == 2:
            form = OTPVerificationForm(request.POST)
            if form.is_valid():
                email = request.session.get('email')
                entered_otp = form.cleaned_data['otp']
                cached_otp = cache.get(f"otp_{email}")

                if str(entered_otp) == str(cached_otp):
                    request.session['signup_step'] = 3
                    return redirect('signup')
                else:
                    messages.error(request, "Invalid OTP. Please try again.")

        elif step == 3:
            form = FinalSignupForm(request.POST)
            if form.is_valid():
                user = form.save(commit=False)
                user.email = request.session.get('email')
                user.set_password(form.cleaned_data['password'])
                user.save()
                login(request, user)
                request.session.pop('signup_step', None)
                request.session.pop('email', None)
                return redirect('home')

    else:
        step = request.session.get('signup_step', 1)
        form = EmailForm() if step == 1 else OTPVerificationForm() if step == 2 else FinalSignupForm()

    return render(request, 'auth.html', {
        'form': form,
        'form_title': 'Signup',
        'button_text': 'Next' if step < 3 else 'Signup',
        'toggle_text': 'Already have an account? Login',
        'toggle_url': '/easy2pay/login/',
    })


def login_view(request):
    if request.method == 'POST':
        login_form = CustomUserLoginForm(data=request.POST)
        if login_form.is_valid():
            email = login_form.cleaned_data['username']
            password = login_form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, "Invalid email or password.")
    else:
        login_form = CustomUserLoginForm()

    return render(request, 'auth.html', {
        'form': login_form,
        'form_title': 'Login',
        'button_text': 'Login',
        'toggle_text': "Don't have an account? Signup",
        'toggle_url': '/easy2pay/signup/',
        't_text' : "Forgotten password?",
        't_url' : '/easy2pay/passreset/',
    })

@login_required
def home_view(request):
    return render(request, 'home.html', {'user': request.user})


@login_required
def scan_qr_view(request):
    return render(request, 'scan.html')


@login_required
def check_qr(request):
    code = request.GET.get('code', None)
    product = None

    if code:
        try:
            product = Product.objects.get(unique_code=code)
        except Product.DoesNotExist:
            product = None

    return render(request, 'product_found.html', {'product': product})


@login_required
def cart_detail(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    total_price = sum(item.total_price() for item in cart_items)
    return render(request, 'cart.html', {'cart': cart_items, 'amount': total_price })


@login_required
def profile_view(request):
    user = request.user
    context = {
        'user_name': user.username,
        'user_email': user.email,
        }
    return render(request, 'profile.html', context)


def logout_view(request):
    logout(request)
    return redirect('login/')


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not item_created:
        cart_item.quantity += 1
        cart_item.save()
    else:
        cart_item.quantity = 1
        cart_item.save()

    messages.success(request, f"{product.name} was added to your cart.")
    return redirect('cart')


razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

import logging
logger = logging.getLogger(__name__)

@csrf_exempt
def create_order(request):
    if request.method == 'POST':
        try:
            # Parse the incoming JSON data
            data = json.loads(request.body)
            print("Received Amount:", data.get('amount'))
            logger.info(f"Received data: {data}")

            # Extract and validate input data
            amount_value = data.get('amount')
            if amount_value is None:
                amount = Decimal(100)  # Default ₹1 if missing
                logger.warning("Amount not provided, using default: %s", amount)
            else:
                try:
                    amount = Decimal(amount_value)
                except (ValueError, TypeError) as e:
                    logger.error("Invalid amount value: %s", amount_value)
                    return JsonResponse({'error': 'Invalid amount value.'}, status=400)

            currency = 'INR'
            user = request.user
            user_cart = Cart.objects.filter(user=user).first()

            if not user_cart:
                logger.warning("User  cart not found for user: %s", user.id)
                return JsonResponse({'error': 'User  cart not found'}, status=400)

            amount = max(amount, Decimal(1))  # Ensure minimum ₹1
            amount_paise = int(amount * 100)  # Convert INR to paise

            # Create Razorpay order
            client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
            order_data = {
                'amount': amount_paise,
                'currency': currency,
                'payment_capture': '1'
            }
            order = client.order.create(data=order_data)
            logger.info(f"Razorpay order created: {order}")

            # Save order details
            new_order = Order.objects.create(
                user=user,
                cart=user_cart,
                razorpay_order_id=order['id'],
                amount=amount,  # INR
                currency=currency
            )
            logger.info(f"Order saved: {new_order.id}")

            return JsonResponse(order)

        except Exception as e:
            logger.error("Error creating order: %s", str(e), exc_info=True)
            return JsonResponse({'error': 'An error occurred while creating the order.'}, status=500)

    logger.warning("Invalid request method: %s", request.method)
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def payment_view(request):
    unique_code = request.GET.get('unique_code')  # Check if a single item is being purchased
    user = request.user

    if unique_code:
        try:
            cart_item = CartItem.objects.get(product__unique_code=unique_code, cart__user=user)
            products_with_details = [{
                'product': cart_item.product,
                'quantity': cart_item.quantity,
                'price': cart_item.product.price,
                'total_price': cart_item.total_price(),
                'unique_code': cart_item.product.unique_code  # Ensure unique_code is passed to template
            }]
            total_price = cart_item.total_price()
        except Cart.DoesNotExist:
            return redirect('cart')  # Redirect back to cart if item not found
    else:
        cart = get_object_or_404(Cart, user=user)
        cart_items = cart.items.all()

        products_with_details = [
            {
                'product': item.product, 
                'quantity': item.quantity, 
                'price': item.product.price, 
                'total_price': item.total_price(),
                'unique_code': item.product.unique_code  # Pass unique_code
            }
            for item in cart_items
        ]

        total_price = sum(item.total_price() for item in cart_items)

    active_offers = Offer.objects.filter(valid_from__lte=now(), valid_until__gte=now())
    user_points = request.user.points

    return render(request, 'payment.html', {
        'products_with_details': products_with_details,
        'total_price': total_price,
        'offers': active_offers,
        'user_points': user_points,
        'unique_code': unique_code
    })



@login_required
@csrf_exempt
def payment_success(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_id = data.get('order_id')
            payment_id = data.get('payment_id')
            total_amount = data.get('amount')
            used_points = data.get('used_points')

            order = Order.objects.get(razorpay_order_id=order_id)
            order.razorpay_payment_id = payment_id
            order.is_paid = True
            order.save()

            user = order.cart.user
            #total_amount_rupees = order.amount / 100
            points_earned = int(total_amount // 25)

            if used_points > 0:
                user.points -= used_points
                PointTransaction.objects.create(
                    user=user, 
                    points=-used_points, 
                    description="Redeemed points for purchase"
                )

            # Add earned points
            if points_earned > 0:
                user.points += points_earned
                PointTransaction.objects.create(
                    user=user, 
                    points=points_earned, 
                    description="Earned points from purchase"
                )
            user.save()

            product_details = []
            if order.cart:
                if order.cart.items.count() == 1:  # Single product purchase
                    cart_item = order.cart.items.first()
                    cart_item.product.is_paid = True
                    cart_item.product.save()
                    product_details.append({
                        'name': cart_item.product.name,
                        'price': float(cart_item.product.price)
                    })
                    cart_item.delete()  # Remove the single item from cart
                else:
                # If buying full cart, mark all items as paid
                    for cart_item in order.cart.items.all():
                        cart_item.product.is_paid = True
                        cart_item.product.save()
                        product_details.append({
                            'name': cart_item.product.name,
                            'price': float(cart_item.product.price)
                        })
                    order.cart.items.all().delete()
                    order.cart.delete()

            context = {
                'user': user,
                'order_id': order_id,
                'payment_id': payment_id,
                'total_amount': total_amount,
                'points_earned': points_earned,
                'total_points': user.points,
                'used_points': used_points,
                'date_time': now(),
                'product_details': product_details
            }
            request.session['product_details'] = product_details

            return JsonResponse({'success': True, 'message': 'Payment successful, points updated', 'points_earned': points_earned, 'total_points': user.points})
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': 'Server error', 'details': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def payment_failure(request):
    return render(request, 'payment_failure.html')

@login_required
def payment_confirm(request):
    product_details = request.session.get('product_details', [])
    order_id = request.GET.get('order_id')
    payment_id = request.GET.get('payment_id')
    total_amount = request.GET.get('amount')
    used_points = request.GET.get('used_points')
    print(f"Looking for order with ID: {order_id}")

    try:
        order = Order.objects.get(razorpay_order_id=order_id)
        user = order.cart.user
        points_earned = int(float(total_amount) // 25) if total_amount else 0


        context = {
            'user': user,
            'order_id': order_id,
            'payment_id': payment_id,
            'total_amount': total_amount,
            'points_earned': points_earned,
            'total_points': user.points,
            'used_points': used_points,
            'date_time': now(),
            'product_details': product_details
        }

        return render(request, 'payment_success.html', context)

    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Server error', 'details': str(e)}, status=500)


def offers_list(request):
    """
    Display all active offers.
    """
    active_offers = Offer.objects.filter(valid_from__lte=now(), valid_until__gte=now())
    return render(request, 'offers.html', {'offers': active_offers})

@login_required
def rdpt(request):
    user_points = request.user.points
    points_history = PointTransaction.objects.filter(user=request.user).order_by('-date')  # Latest first

    return render(request, 'rdpoints.html', {
        'user_points': user_points,
        'points_history': points_history
    })

def generate_profile_image(request, name):
    # Set image size and background color
    img_size = (100, 100)
    bg_color = (0, 128, 128)  # Teal color

    # Create an image
    img = Image.new("RGB", img_size, bg_color)
    draw = ImageDraw.Draw(img)

    # Extract first letter of the name
    initial = name[0].upper() if name else "?"

    # Set font size and type
    font_size = 40
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    # Get text size
    text_size = draw.textbbox((0, 0), initial, font=font)
    text_width = text_size[2] - text_size[0]
    text_height = text_size[3] - text_size[1]

    # Calculate position to center the text
    position = ((img_size[0] - text_width) // 2, (img_size[1] - text_height) // 2)

    # Draw text on image
    draw.text(position, initial, fill="white", font=font)

    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return HttpResponse(img_bytes, content_type="image/png")

@login_required
def generate_receipt(request, order_id):
    try:
        order = Order.objects.get(razorpay_order_id=order_id)
        user = order.cart.user if order.cart else order.user
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt_{order_id}.pdf"'

        p = canvas.Canvas(response)
        p.setFont("Helvetica", 14)
        p.drawString(100, 800, "Payment Receipt")
        p.setFont("Helvetica", 10)
        p.drawString(100, 780, f"Order ID: {order_id}")
        p.drawString(100, 760, f"Payment ID: {order.razorpay_payment_id}")
        p.drawString(100, 740, f"Total Amount: Rs.{order.amount}")
        p.drawString(100, 720, f"Points Used: {order.cart.user.points}")
        p.drawString(100, 700, f"Points Earned: {order.amount // 25}")
        p.drawString(100, 680, f"Date & Time: {now()}")

        p.drawString(100, 650, "Purchased Products:")
        y = 630
        product_details = request.session.get('product_details', [])
        
        for product in product_details:
            p.drawString(100, y, f"- {product['name']}: Rs.{product['price']}")
            y -= 20

        p.showPage()
        p.save()
        return response

    except Order.DoesNotExist:
        return HttpResponse("Order not found", status=404)
    
@login_required
def remove_from_cart(request, item_id):
    if request.method == "POST":
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart_item.delete()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)