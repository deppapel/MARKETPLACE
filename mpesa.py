from flask import Blueprint, request, jsonify, current_app
from models import db, User, Order, Transaction, TransactionQuery
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
        status='pending',
        checkout_request_id=result.get('CheckoutRequestID')
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
    data = request.get_json()
    print("="*50)
    print("CALLBACK RECEIVED")
    print("Raw data:", data)
    print("="*50)

    if not data or 'Body' not in data or 'stkCallback' not in data['Body']:
        print("Invalid callback structure")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Invalid callback'})

    callback_data = data['Body']['stkCallback']
    result_code = callback_data.get('ResultCode')
    result_desc = callback_data.get('ResultDesc')
    checkout_request_id = callback_data.get('CheckoutRequestID')
    print(f"ResultCode: {result_code}, ResultDesc: {result_desc}, CheckoutRequestID: {checkout_request_id}")

    mpesa_receipt = None
    if result_code == 0 and 'CallbackMetadata' in callback_data:
        for item in callback_data['CallbackMetadata']['Item']:
            if item.get('Name') == 'MpesaReceiptNumber':
                mpesa_receipt = item.get('Value')
                print("MpesaReceiptNumber found:", mpesa_receipt)
                break

    # Look for the pending transaction using CheckoutRequestID
    if checkout_request_id:
        trans = Transaction.query.filter_by(checkout_request_id=checkout_request_id, status='pending').first()
        if trans:
            print(f"Found pending transaction: {trans.id} for {trans.transaction_type}")
            if result_code == 0 and mpesa_receipt:
                # Payment successful
                trans.status = 'completed'
                trans.mpesa_receipt = mpesa_receipt
                trans.completed_at = datetime.utcnow()
                if trans.transaction_type == 'registration':
                    user = User.query.get(trans.user_id)
                    if user:
                        user.registration_fee_paid = True
                        print(f"User {user.id} registration fee marked paid.")
                elif trans.transaction_type == 'order':
                    order = Order.query.get(trans.order_id)
                    if order:
                        order.status = 'paid'
                        print(f"Order {order.id} marked paid.")
                db.session.commit()
                print("Transaction updated.")
            else:
                # Payment failed – mark transaction as failed
                trans.status = 'failed'
                db.session.commit()
                print("Transaction marked as failed.")
        else:
            print(f"No pending transaction found for CheckoutRequestID: {checkout_request_id}")
            # Optional fallback to account_ref logic
            account_ref = callback_data.get('AccountReference')
            if account_ref and account_ref.startswith('REG-'):
                user_id = int(account_ref.split('-')[1])
                user = User.query.get(user_id)
                if user:
                    user.registration_fee_paid = True
                    # Optionally create a transaction record if missing
                    trans = Transaction(
                        user_id=user.id,
                        amount=1,
                        mpesa_receipt=mpesa_receipt,
                        status='completed',
                        transaction_type='registration',
                        completed_at=datetime.utcnow(),
                        checkout_request_id=checkout_request_id
                    )
                    db.session.add(trans)
                    db.session.commit()
                    print(f"Fallback: User {user.id} registration fee marked paid.")
            # Similarly for ORD-...
    else:
        print("No CheckoutRequestID in callback")

    return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'})
@mpesa.route('/status-results', methods=['POST'])
def status_results():
    #this is an endpoint to process status results, check if the transaction was successful and update the user's account if needed
    data = request.get_json()
    print("Status result received:", data)

    if not data or 'Result' not in data:
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Invalid data'})
    result = data['Result']
    result_code = result.get('ResultCode')
    resultDesc = result.get('ResultDesc')
    originator_conversation_id = result.get('OriginatorConversationID')
    transaction_id = result.get('TransactionID')

    #findming the pending query requests
    query = Transaction.query.filter_by(originator_conversation_id=originator_conversation_id, status='pending').first()
    if not query:
        print(f"No pending transaction found for OriginatorConversationID: {originator_conversation_id}")
        return jsonify({'ResultCode': 0, 'ResultDesc': 'Transaction not found'})
    if result_code == 0:
        #Activate user account or mark order as paid
        user = User.query.get(query.user_id)
        if user and not user.registration_fee_paid:
            user.registration_fee_paid = True
            #Create and update the transaction record
            trans = Transaction(
                user_id=user.id,
                amount=query.amount,
                mpesa_receipt=transaction_id,
                status='completed',
                transaction_type=query.transaction_type,
                completed_at=datetime.utcnow(),
                originator_conversation_id=originator_conversation_id
            )
            db.session.add(trans)
        db.session.commit()    
        query.status = 'completed'
        query.completed_at = datetime.utcnow()
        db.session.commit()
        print(f"User {user.username} activated manually.")
    else:
        query.status = 'failed'    
        db.session.commit()
        print(f"Query failed: {resultDesc}")

    return jsonify({'success': 0, 'ResultDesc': 'Failed'})
@mpesa.route('/status-timeout', methods=['POST'])
def status_timout():
    #this is an endpoint to process status timeouts, log the error and notify admin
    data = request.get_json()
    print("Status timeout received:", data)
    # Log the timeout, maybe mark the query as failed
    if data and 'OriginatorConversationID' in data:
        query = TransactionQuery.query.filter_by(originator_conversation_id=data['OriginatorConversationID']).first()
        if query:
            query.status = 'failed'
            db.session.commit()
    return jsonify({'ResultCode': 0, 'ResultDesc': 'Success'})