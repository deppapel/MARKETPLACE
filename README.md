# MARKETPLACE
Its like fiverr, allows one to access market and services from home

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
