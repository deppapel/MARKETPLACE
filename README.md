# MARKETPLACE
Its like fiverr, allows one to access market and services from home

<<<<<<< HEAD
# Marketplace Platform

A multi-vendor marketplace built with Flask where users can register as buyers or sellers, list services, place orders, make payments, leave reviews, and communicate through an internal messaging system. The platform includes full admin management, dispute resolution, and M-Pesa integration for payments.

---

## Table of Contents
1. [Project Structure](#project-structure)
2. [Tech Stack](#tech-stack)
3. [User Roles](#user-roles)
4. [Key Workflows](#key-workflows)
5. [Database Models](#database-models)
6. [Setup Instructions](#setup-instructions)
7. [Environment Variables](#environment-variables)
8. [Running the Application](#running-the-application)
9. [Testing M-Pesa Payments](#testing-m-pesa-payments)
10. [Features by Blueprint](#features-by-blueprint)

---

## Project Structure

| File / Folder | Purpose |
|---------------|---------|
| `app.py` | Application factory; registers blueprints and extensions |
| `models.py` | SQLAlchemy models: User, Category, Service, Order, Review, Message, Notification, Dispute, Transaction |
| `auth.py` | Registration, login, email verification, password reset |
| `main.py` | Home page, profile management, dashboards (buyer, seller, admin) |
| `admin.py` | Admin dashboard, category management, user management |
| `seller.py` | Create, edit, delete services with image uploads |
| `marketplace.py` | Browse services, search/filter, service detail page |
| `cart.py` | Add to cart, update cart, checkout |
| `orders.py` | Order placement, order status, order tracking |
| `reviews.py` | Add, edit, delete reviews |
| `disputes.py` | Raise disputes, dispute messages, status updates |
| `messaging.py` | Conversations, messages, unread notifications |
| `notifications.py` | In-app notification system |
| `mpesa.py` | M-Pesa STK push, payment callbacks, manual activation |
| `mpesa_service.py` | Daraja API integration (token, STK push, transaction status) |
| `utils.py` | Shared decorators like `@payment_required` |
| `forms.py` | All WTForms (registration, login, profile, review, dispute, etc.) |
| `templates/` | All HTML templates (Bootstrap 5) |
| `static/` | Custom CSS, images |
| `uploads/` | Uploaded service images |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3, Flask, Flask-SQLAlchemy, Flask-Login, Flask-Mail |
| **Frontend** | HTML5, Jinja2, Bootstrap 5, Font Awesome |
| **Database** | PostgreSQL |
| **Payments** | M-Pesa Daraja API (STK Push, Transaction Status) |
| **Authentication** | Email verification (OTP), password hashing (Werkzeug) |
| **File Uploads** | Secure filename handling, image storage (binary in DB) |
| **Deployment** | Gunicorn, PostgreSQL (production) |

---

## User Roles

The platform defines three roles. A user can only have one role.

| Role | Permissions |
|------|-------------|
| **Buyer** | Browse services, add to cart, place orders, leave reviews, send messages |
| **Seller** | Create/edit/delete services, manage orders received, reply to reviews, send messages |
| **Admin** | Manage categories, manage users, view all orders, manage disputes, manual account activation |

### Registration Fee Requirement

- New users must pay a **1 KSh registration fee** before accessing any paid feature.
- Unpaid users can only browse the marketplace and view their profile.
- The `@payment_required` decorator (in `utils.py`) protects all sensitive routes.
- Admins can manually activate users via the **Manual Activation** page.

---

## Key Workflows

### User Registration & Activation
1. User fills registration form → receives OTP via email.
2. After OTP verification, account is created but **inactive**.
3. User pays the 1 KSh registration fee via M-Pesa STK Push.
4. Payment callback updates `registration_fee_paid = True` → account fully activated.

### Selling a Service
1. Seller logs in and goes to Seller Dashboard.
2. Clicks "Add Service" → fills title, description, price, delivery time, etc.
3. Uploads images (JPEG/PNG) → service slug generated automatically.
4. Service is saved with `status='draft'` or `'published'`.

### Buying a Service
1. Buyer browses services → clicks "View Details".
2. Clicks "Add to Cart" → item added.
3. Checks out → order created with `status='pending'`.
4. Buyer is prompted to pay via M-Pesa STK Push.
5. Payment callback updates order `status='paid'` and records transaction.

### Order Completion & Payout
1. Seller views order → updates item status from `pending` → `in_progress` → `completed`.
2. After all items are `completed`, the order status becomes `completed`.
3. Seller's earnings are tracked (future: automatic payout via B2C).

### Dispute Resolution
1. Buyer or seller clicks "Raise Dispute" on an order item.
2. Reason dropdown changes based on role (buyer‑fault vs seller‑fault reasons).
3. Dispute is created with `status='open'`.
4. Both parties can exchange public messages; admin can send private messages.
5. Admin updates status to `under_review`, `resolved`, or `escalated`.

### Messaging
- Conversations are linked to an order.
- Participants: buyer + all sellers of items in that order.
- Notifications are created when a new message arrives.
- Unread message count appears in the navbar.

---

## Database Models

The following ER diagram shows the core tables and their relationships.
=======
## User Flow

```mermaid
flowchart TD
    Start([User visits Marketplace]) --> CheckAuth{Logged in?}
    CheckAuth -->|No| LoginPage[Login / Register]
    LoginPage --> Register[Register → OTP verification → Pay reg fee]
    Register --> PayFee[Pay 1 KSh fee via M-Pesa]
    PayFee --> CallbackFee{Callback received?}
    CallbackFee -->|Yes| Active[Account active]
    CallbackFee -->|No| ManualActivation[Admin manually activates]
    ManualActivation --> Active

    Active --> ChooseRole{User role?}

    %% Buyer Flow
    ChooseRole -->|Buyer| BuyerDashboard[Buyer Dashboard]
    BuyerDashboard --> BrowseServices[Browse marketplace]
    BrowseServices --> ViewService[View service details]
    ViewService --> AddToCart[Add to cart]
    AddToCart --> Cart[View cart]
    Cart --> Checkout[Checkout]
    Checkout --> CreateOrder[Create order with status='pending']
    CreateOrder --> PayOrder[Pay via M-Pesa STK Push]
    PayOrder --> CallbackOrder{Callback received?}
    CallbackOrder -->|Yes| OrderPaid[Order status = 'paid']
    CallbackOrder -->|No| AdminOrderActivation[Admin manually verifies transaction]
    AdminOrderActivation --> OrderPaid
    OrderPaid --> WaitCompletion[Wait for seller to complete]
    WaitCompletion --> SellerCompletes[Seller marks item as completed]
    SellerCompletes --> OrderCompleted[Order status = 'completed']
    OrderCompleted --> LeaveReview[Leave review]
    LeaveReview --> EndBuyer([Buyer journey ends])

    %% Seller Flow
    ChooseRole -->|Seller| SellerDashboard[Seller Dashboard]
    SellerDashboard --> CreateService[Create service]
    CreateService --> PublishService[Publish service]
    PublishService --> ViewOrders[View orders received]
    ViewOrders --> UpdateStatus[Update item status: pending → in_progress → completed]
    UpdateStatus --> NotifyBuyer[Buyer notified]
    NotifyBuyer --> Earnings[Earnings accrued]
    Earnings --> RequestPayout[Admin processes payout via B2C]
    RequestPayout --> EndSeller([Seller journey ends])

    %% Admin Flow
    ChooseRole -->|Admin| AdminDashboard[Admin Dashboard]
    AdminDashboard --> ManageCategories[Manage categories]
    AdminDashboard --> ManageUsers[Manage users: suspend/activate]
    AdminDashboard --> ViewAllOrders[View all orders]
    AdminDashboard --> ManageDisputes[Manage disputes]
    AdminDashboard --> ManualActivationPage[Manual account activation]
    ManualActivationPage --> EnterReceipt[Enter receipt number]
    EnterReceipt --> QueryAPI[Call Transaction Status API]
    QueryAPI --> ActivateUser[Activate user]
    ActivateUser --> EndAdmin([Admin action ends])

    %% Dispute Flow (shared)
    OrderPaid --> RaiseDispute[Buyer or seller raises dispute]
    RaiseDispute --> DisputeOpen[Dispute status = 'open']
    DisputeOpen --> AdminDispute[Admin reviews dispute]
    AdminDispute --> DisputeResolved[Dispute resolved]
    DisputeResolved --> OrderCompleted

    %% Messaging Flow (shared)
    OrderPaid --> StartConversation[Start conversation]
    StartConversation --> SendMessages[Send messages]
    SendMessages --> Notify[Notifications created]
    Notify --> ReadMessages[Recipients read messages]

    %% Styling
    style Start fill:#f9f,stroke:#333,stroke-width:2px
    style LoginPage fill:#bbf,stroke:#333
    style PayFee fill:#f96,stroke:#333
    style CallbackFee fill:#f96,stroke:#333
    style ManualActivation fill:#f96,stroke:#333
    style Active fill:#9f9,stroke:#333
    style OrderCompleted fill:#9f9,stroke:#333
```

## Entity Relationship Diagram
>>>>>>> 0662a926d9715a869f3b84252f0bce6e07845032

```mermaid
erDiagram
    User {
        int id PK
        string username
        string email
        string role
        boolean registration_fee_paid
        boolean email_verified
        bytea avatar_data
    }
    Category {
        int id PK
        string name
        int parent_id FK
    }
    Service {
        int id PK
        int seller_id FK
        int category_id FK
        string title
        numeric price
        string status
    }
    ServiceImage {
        int id PK
        int service_id FK
        string image_url
    }
    Order {
        int id PK
        int buyer_id FK
        string order_number
        string status
        numeric total_amount
    }
    OrderItem {
        int id PK
        int order_id FK
        int service_id FK
        int seller_id FK
        string status
    }
    Review {
        int id PK
        int order_item_id FK
        int rating
        text comment
    }
    Dispute {
        int id PK
        int order_item_id FK
        int raised_by_id FK
        int against_id FK
        string status
    }
    Transaction {
        int id PK
        int user_id FK
        int order_id FK
        numeric amount
        string mpesa_receipt
        string status
    }
    Conversation {
        int id PK
        int order_id FK
    }
    Message {
        int id PK
        int conversation_id FK
        int sender_id FK
        text content
    }
    Notification {
        int id PK
        int user_id FK
        string type
        text content
        boolean is_read
    }

    User ||--o{ Service : "sells"
    User ||--o{ Order : "buys"
    User ||--o{ Transaction : "has"
    User ||--o{ Notification : "receives"
    Service ||--o{ ServiceImage : "has"
    Service ||--o{ OrderItem : "appears in"
    Category ||--o{ Service : "contains"
    Order ||--o{ OrderItem : "contains"
    OrderItem ||--|| Review : "has one"
    OrderItem ||--o{ Dispute : "may have"
    Order ||--o{ Conversation : "linked to"
<<<<<<< HEAD
    Conversation ||--o{ Message : "contains"
=======
    Conversation ||--o{ Message : "contains"
```
>>>>>>> 0662a926d9715a869f3b84252f0bce6e07845032
