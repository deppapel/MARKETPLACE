from flask import Blueprint, request, jsonify, current_app
from models import db, User, Order, Transaction
from mpesa_service import MpesaService
from datetime import datetime

mpesa = Blueprint('mpesa', __name__, url_prefix='/mpesa')
mpesa_service = MpesaService()

@mpesa.route('/register-payment', methods=['POST'])
def register_payment():
    """Initiate payment for registration fee (fixed amount 1 KSh)."""
    data = request.get_json()
    user_id = data.get('user_id')
    phone = data.get('phone_number')

    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    if user.registration_fee_paid:
        return jsonify({'success': False, 'message': 'Registration fee already paid'}), 400

    # Initiate STK push with account reference like "REG-<user_id>"
    mpesa_service.init_app(current_app)
    result = mpesa_service.stk_push(phone, 1, f"REG-{user.id}")

    if 'error' in result:
        return jsonify({'success': False, 'message': result['error']}), 500

    # Create a transaction record (pending)
    trans = Transaction(
        user_id=user.id,
        amount=1,
        phone_number=phone,
        transaction_type='registration',
        status='pending'
    )
    db.session.add(trans)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'STK push sent. Please check your phone and enter PIN.',
        'checkout_request_id': result.get('CheckoutRequestID')
    })

@mpesa.route('/order-payment/<int:order_id>', methods=['POST'])
def order_payment(order_id):
    """Initiate payment for an order."""
    data = request.get_json()
    phone = data.get('phone_number')

    order = Order.query.get_or_404(order_id)
    if order.status != 'pending':
        return jsonify({'success': False, 'message': 'Order is not pending payment'}), 400

    mpesa_service.init_app(current_app)
    result = mpesa_service.stk_push(phone, float(order.total_amount), f"ORD-{order.id}")

    if 'error' in result:
        return jsonify({'success': False, 'message': result['error']}), 500

    trans = Transaction(
        user_id=order.buyer_id,
        order_id=order.id,
        amount=order.total_amount,
        phone_number=phone,
        transaction_type='order',
        status='pending'
    )
    db.session.add(trans)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'STK push sent. Please check your phone and enter PIN.',
        'checkout_request_id': result.get('CheckoutRequestID')
    })

@mpesa.route('/callback', methods=['POST'])
def callback():
    """M-Pesa will POST payment results here."""
    data = request.get_json()
    print("Callback received:", data)   # for debugging

    # Safaricom sends data in a nested structure
    if not data or 'Body' not in data or 'stkCallback' not in data['Body']:
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Invalid callback'})

    callback_data = data['Body']['stkCallback']
    result_code = callback_data.get('ResultCode')
    result_desc = callback_data.get('ResultDesc')
    checkout_id = callback_data.get('CheckoutRequestID')
    account_ref = callback_data.get('AccountReference')  # this is what we set (e.g., "REG-1")
    mpesa_receipt = None

    # If successful, extract the receipt number from the callback metadata
    if result_code == 0 and 'CallbackMetadata' in callback_data:
        for item in callback_data['CallbackMetadata']['Item']:
            if item.get('Name') == 'MpesaReceiptNumber':
                mpesa_receipt = item.get('Value')
                break

    # Find the transaction – we need to link it. We'll look up by checkout_id if we stored it,
    # but we didn't. So we'll rely on account_ref to find the user/order and create/update transaction.
    # For simplicity, we'll just log and manually handle for now. In production you'd store checkout_id.

    if result_code == 0 and mpesa_receipt:
        # Payment successful
        if account_ref.startswith('REG-'):
            user_id = int(account_ref.split('-')[1])
            user = User.query.get(user_id)
            if user:
                user.registration_fee_paid = True
                # Create or update transaction record
                trans = Transaction(
                    user_id=user.id,
                    amount=1,
                    mpesa_receipt=mpesa_receipt,
                    status='completed',
                    transaction_type='registration',
                    completed_at=datetime.utcnow()
                )
                db.session.add(trans)
                db.session.commit()
        elif account_ref.startswith('ORD-'):
            order_id = int(account_ref.split('-')[1])
            order = Order.query.get(order_id)
            if order:
                order.status = 'paid'
                trans = Transaction(
                    user_id=order.buyer_id,
                    order_id=order.id,
                    amount=order.total_amount,
                    mpesa_receipt=mpesa_receipt,
                    status='completed',
                    transaction_type='order',
                    completed_at=datetime.utcnow()
                )
                db.session.add(trans)
                db.session.commit()
    else:
        # Payment failed – optionally update a transaction record
        print(f"Payment failed: {result_desc}")

    return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'})