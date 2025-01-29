from .models import Cart, CartItem

def add_to_cart(user, product, quantity=1):
    """
    Add a product to the user's cart. Update the quantity if it already exists.
    """
    cart, created = Cart.objects.get_or_create(user=user)
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not item_created:
        # Update quantity if the item already exists
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity

    cart_item.save()
