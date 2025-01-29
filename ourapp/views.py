from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import EmailForm, OTPVerificationForm, FinalSignupForm, CustomUserLoginForm
from django.core.mail import send_mail
from django.core.cache import cache
from django.conf import settings
import random
from django.http import HttpResponse
from .models import Product, Cart, CartItem,Order
from .utils import add_to_cart
import razorpay
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

def send_email_otp(email, otp):
    subject = "Your OTP for easy2pay Signup"
    message = f"Your OTP for easy2pay signup is {otp}. Please do not share it with anyone."
    from_email = settings.EMAIL_HOST_USER

    try:
        send_mail(subject, message, from_email, [email])
    except Exception as e:
        raise Exception("Failed to send OTP. Please try again later.")

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
        form = CustomUserLoginForm(data=request.POST)
        if form.is_valid():
            email = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = CustomUserLoginForm()

    return render(request, 'auth.html', {
        'form': form,
        'form_title': 'Login',
        'button_text': 'Login',
        'toggle_text': "Don't have an account? Signup",
        'toggle_url': '/easy2pay/signup/',
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
    # Get the cart associated with the logged-in user
    cart = request.user.cart
    
    # Get all items in the cart
    cart_items = cart.items.all()  # Fetch related CartItem objects
    
    # Calculate the total price of items in the cart
    total_price = sum(item.total_price() for item in cart_items)  # Use cart_items instead of self.items.all()
    
    # Convert total price to cents (integer)
    amount = int(total_price * 100)
    
    # Pass cart items and calculated amount to the template
    return render(request, 'cart.html', {'cart': cart_items, 'amount': amount})

@login_required
def profile_view(request):
    # Example user data (you can replace this with actual data from the database)
    user = request.user  # Get the logged-in user
    context = {
        'user_name': user.username,  # Correctly access the username as an attribute
    }
    return render(request, 'profile.html', context)

def logout_view(request):
    logout(request)
    return redirect('login/')  # Replace 'login' with your login URL name


@login_required
def add_to_cart(request, product_id):
    # Get the product
    product = get_object_or_404(Product, id=product_id)
    
    # Get or create the user's cart
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Check if the product is already in the cart
    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        product=product
    )
    
    if not item_created:
        # If the product is already in the cart, increase the quantity
        cart_item.quantity += 1
        cart_item.save()
    else:
        # If it's a new item, ensure the quantity starts at 1
        cart_item.quantity = 1
        cart_item.save()

    # Add a success message
    mes = messages.success(request, f"{product.name} was added to your cart.")
    
    return redirect('cart')
    # Redirect to the same page or another relevant page
    return HttpResponse(mes)  # Replace 'product_list' with the name of your desired URL.

# Razorpay client instance
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

@csrf_exempt
def create_order(request):
    if request.method == 'POST':
        # Load the JSON data from the request body
        data = json.loads(request.body)
        amount = data.get('amount')  # Amount in paise
        currency = 'INR'  # Currency code

        # Initialize Razorpay client
        client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
        
        # Prepare order data
        order_data = {
            'amount': amount,  # Amount in paise
            'currency': currency,
            'payment_capture': '1'  # Auto capture
        }
        
        # Create the order
        order = client.order.create(data=order_data)
        user_cart = Cart.objects.get(user=request.user)

        # Create an Order entry in the database
        new_order = Order.objects.create(
            user=request.user,
            cart=user_cart,
            razorpay_order_id=order['id'],
            amount=amount / 100,  # Convert paise to INR
            currency=currency
        )
        
        # Return the order details as a JSON response
        return JsonResponse(order)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@csrf_exempt
def payment_success(request):
    if request.method == 'POST':
        try:
            # Parse the incoming payment data
            data = json.loads(request.body)
            order_id = data.get('order_id')
            payment_id = data.get('payment_id')

            # Retrieve the order
            order = Order.objects.get(razorpay_order_id=order_id)
            order.razorpay_payment_id = payment_id
            order.is_paid = True
            order.save()

            # Get the user from the order
            user = order.cart.user  # Assuming order is linked to a cart and cart has a user

            # Calculate total amount spent in rupees
            total_amount_rupees = order.amount / 100  # Convert paise to rupees
            
            # Calculate points earned (1 point per ₹25 spent)
            points_earned = int(total_amount_rupees // 25)  # Floor division to get whole points
            
            # Update user's points
            user.points += points_earned
            user.save()

            # Mark all products in the cart as paid
            for cart_item in order.cart.items.all():
                cart_item.product.is_paid = True
                cart_item.product.save()

            return JsonResponse({
                'success': True, 
                'message': 'Payment successful, all products marked as paid, and points updated',
                'points_earned': points_earned,
                'total_points': user.points
            })

        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': 'Server error', 'details': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def payment_failure(request):
    # Handle failed payment here
    return render(request, 'payment_failure.html')