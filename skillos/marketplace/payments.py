"""SkillHub Payments — pricing, purchases, commissions, revenue tracking.

Pricing models:
  - free:     $0, no payment required
  - one_time: one-time purchase, lifetime access + updates
  - subscription: recurring monthly fee, auto-renew

Platform commission: configurable (default 20%)
  - Author gets: price × (1 - commission_rate)
  - Platform gets: price × commission_rate

Payment providers: pluggable interface (mock by default).
"""


import logging
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "skillhub.db"
COMMISSION_RATE = float(os.environ.get("SKILLHUB_COMMISSION", "0.20"))
CURRENCY = os.environ.get("SKILLHUB_CURRENCY", "USD")

_local = threading.local()


class PricingModel(Enum):
    FREE = "free"
    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"


class PurchaseStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


@dataclass
class PricingTier:
    skill_id: str = ""
    model: PricingModel = PricingModel.FREE
    price: float = 0.0          # in USD (or configured currency)
    trial_days: int = 0          # free trial period
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class Purchase:
    purchase_id: str = ""
    skill_id: str = ""
    buyer_id: str = ""
    author_id: str = ""
    model: PricingModel = PricingModel.FREE
    amount: float = 0.0
    commission: float = 0.0
    author_earnings: float = 0.0
    status: PurchaseStatus = PurchaseStatus.PENDING
    payment_method: str = ""
    payment_ref: str = ""       # external payment reference
    created_at: float = 0.0
    completed_at: float = 0.0
    expires_at: float = 0.0     # for subscriptions


def _get_conn() -> sqlite3.Connection:
    """Get thread-local connection via central db.py."""
    if not hasattr(_local, "conn") or _local.conn is None:
        from skillos.db import get_conn
        _local.conn = get_conn("skillhub.db")
        _local.conn.row_factory = sqlite3.Row
        _init_tables(_local.conn)
    return _local.conn


def _init_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS pricing (
            skill_id TEXT PRIMARY KEY,
            model TEXT NOT NULL DEFAULT 'free',
            price REAL NOT NULL DEFAULT 0.0,
            trial_days INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL DEFAULT 0.0,
            updated_at REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY (skill_id) REFERENCES skill_registry(skill_id)
        );

        CREATE TABLE IF NOT EXISTS purchases (
            purchase_id TEXT PRIMARY KEY,
            skill_id TEXT NOT NULL,
            buyer_id TEXT NOT NULL,
            author_id TEXT NOT NULL,
            model TEXT NOT NULL DEFAULT 'free',
            amount REAL NOT NULL DEFAULT 0.0,
            commission REAL NOT NULL DEFAULT 0.0,
            author_earnings REAL NOT NULL DEFAULT 0.0,
            status TEXT NOT NULL DEFAULT 'pending',
            payment_method TEXT NOT NULL DEFAULT '',
            payment_ref TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL DEFAULT 0.0,
            completed_at REAL NOT NULL DEFAULT 0.0,
            expires_at REAL NOT NULL DEFAULT 0.0
        );

        CREATE INDEX IF NOT EXISTS idx_purchases_skill ON purchases(skill_id);
        CREATE INDEX IF NOT EXISTS idx_purchases_buyer ON purchases(buyer_id);
        CREATE INDEX IF NOT EXISTS idx_purchases_author ON purchases(author_id);
        CREATE INDEX IF NOT EXISTS idx_purchases_status ON purchases(status);
    """)
    conn.commit()


# ═══════════════════════════════════════════════════════════════
# Pricing
# ═══════════════════════════════════════════════════════════════

def set_price(skill_id: str, model: str = "free", price: float = 0.0, trial_days: int = 0) -> PricingTier:
    """Set or update pricing for a skill."""
    conn = _get_conn()
    now = time.time()
    existing = conn.execute("SELECT skill_id FROM pricing WHERE skill_id = ?", (skill_id,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE pricing SET model = ?, price = ?, trial_days = ?, updated_at = ? WHERE skill_id = ?",
            (model, price, trial_days, now, skill_id)
        )
    else:
        conn.execute(
            "INSERT INTO pricing (skill_id, model, price, trial_days, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (skill_id, model, price, trial_days, now, now)
        )
    conn.commit()
    return get_price(skill_id)


def get_price(skill_id: str) -> PricingTier:
    """Get pricing for a skill. Defaults to free if not set."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM pricing WHERE skill_id = ?", (skill_id,)).fetchone()
    if not row:
        return PricingTier(skill_id=skill_id, model=PricingModel.FREE)
    def _g(key, default=0):
        try: return row[key]
        except (KeyError, IndexError): return default
    return PricingTier(
        skill_id=row["skill_id"], model=PricingModel(row["model"]),
        price=row["price"], trial_days=_g("trial_days", 0),
        created_at=row["created_at"], updated_at=row["updated_at"],
    )


# ═══════════════════════════════════════════════════════════════
# Purchases
# ═══════════════════════════════════════════════════════════════

def create_purchase(
    skill_id: str,
    buyer_id: str,
    author_id: str = "",
    payment_method: str = "mock",
) -> Purchase:
    """Create a purchase record and process payment (mock by default)."""
    pricing = get_price(skill_id)
    amount = pricing.price
    commission = round(amount * COMMISSION_RATE, 2)
    earnings = round(amount - commission, 2)

    purchase_id = "pur_" + uuid.uuid4().hex[:12]
    now = time.time()

    # Calculate expiry for subscriptions
    expires_at = 0.0
    if pricing.model == PricingModel.SUBSCRIPTION:
        expires_at = now + 30 * 86400  # 30 days

    # Mock payment processing
    payment_ref = _process_payment(amount, payment_method)

    conn = _get_conn()
    conn.execute("""
        INSERT INTO purchases (purchase_id, skill_id, buyer_id, author_id,
            model, amount, commission, author_earnings, status,
            payment_method, payment_ref, created_at, completed_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        purchase_id, skill_id, buyer_id, author_id,
        pricing.model.value, amount, commission, earnings,
        PurchaseStatus.COMPLETED.value if payment_ref else PurchaseStatus.PENDING.value,
        payment_method, payment_ref, now, now if payment_ref else 0.0, expires_at,
    ))
    conn.commit()

    _log.info("Purchase: %s skill=%s buyer=%s amount=%.2f status=%s",
              purchase_id, skill_id, buyer_id, amount, "completed" if payment_ref else "pending")

    return get_purchase(purchase_id)


def get_purchase(purchase_id: str) -> Purchase | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM purchases WHERE purchase_id = ?", (purchase_id,)).fetchone()
    return _row_to_purchase(row) if row else None


def has_purchased(buyer_id: str, skill_id: str) -> bool:
    """Check if a buyer has an active purchase for this skill."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT purchase_id FROM purchases WHERE buyer_id = ? AND skill_id = ? AND status = 'completed' AND (expires_at = 0 OR expires_at > ?)",
        (buyer_id, skill_id, time.time())
    ).fetchone()
    return row is not None


def get_user_purchases(user_id: str) -> list[Purchase]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM purchases WHERE buyer_id = ? ORDER BY created_at DESC", (user_id,)
    ).fetchall()
    return [_row_to_purchase(r) for r in rows]


# ═══════════════════════════════════════════════════════════════
# Revenue
# ═══════════════════════════════════════════════════════════════

def get_author_revenue(author_id: str) -> dict:
    """Revenue summary for a skill author."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT model, COUNT(*) as cnt, SUM(amount) as total_amount, SUM(author_earnings) as total_earnings FROM purchases WHERE author_id = ? AND status = 'completed' GROUP BY model",
        (author_id,)
    ).fetchall()

    by_model = {}
    total_revenue = 0.0
    total_earnings = 0.0
    total_sales = 0
    for r in rows:
        m = r["model"]
        by_model[m] = {"sales": r["cnt"], "revenue": round(r["total_amount"] or 0, 2),
                       "earnings": round(r["total_earnings"] or 0, 2)}
        total_revenue += r["total_amount"] or 0
        total_earnings += r["total_earnings"] or 0
        total_sales += r["cnt"]

    # Recent transactions
    recent = conn.execute(
        "SELECT * FROM purchases WHERE author_id = ? AND status = 'completed' ORDER BY created_at DESC LIMIT 20",
        (author_id,)
    ).fetchall()

    return {
        "author_id": author_id,
        "total_sales": total_sales,
        "total_revenue": round(total_revenue, 2),
        "total_earnings": round(total_earnings, 2),
        "commission_rate": COMMISSION_RATE,
        "currency": CURRENCY,
        "by_model": by_model,
        "recent_purchases": [
            {"purchase_id": r["purchase_id"], "skill_id": r["skill_id"],
             "amount": r["amount"], "earnings": r["author_earnings"],
             "model": r["model"], "created_at": r["completed_at"]}
            for r in recent
        ],
    }


def get_platform_revenue() -> dict:
    """Platform-wide revenue summary."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT model, COUNT(*) as cnt, SUM(amount) as total_amount, SUM(commission) as total_commission FROM purchases WHERE status = 'completed' GROUP BY model"
    ).fetchall()

    by_model = {}
    total_revenue = 0.0
    total_commission = 0.0
    total_sales = 0
    for r in rows:
        m = r["model"]
        by_model[m] = {"sales": r["cnt"], "revenue": round(r["total_amount"] or 0, 2),
                       "commission": round(r["total_commission"] or 0, 2)}
        total_revenue += r["total_amount"] or 0
        total_commission += r["total_commission"] or 0
        total_sales += r["cnt"]

    # Top earning skills
    top_skills = conn.execute(
        "SELECT skill_id, COUNT(*) as cnt, SUM(author_earnings) as earnings FROM purchases WHERE status = 'completed' GROUP BY skill_id ORDER BY earnings DESC LIMIT 10"
    ).fetchall()

    # Monthly breakdown
    monthly = conn.execute(
        "SELECT strftime('%Y-%m', datetime(completed_at, 'unixepoch')) as month, COUNT(*) as cnt, SUM(amount) as revenue, SUM(commission) as commission FROM purchases WHERE status = 'completed' AND completed_at > 0 GROUP BY month ORDER BY month DESC LIMIT 12"
    ).fetchall()

    return {
        "total_sales": total_sales,
        "total_revenue": round(total_revenue, 2),
        "total_commission": round(total_commission, 2),
        "commission_rate": COMMISSION_RATE,
        "currency": CURRENCY,
        "by_model": by_model,
        "top_skills": [{"skill_id": r["skill_id"], "sales": r["cnt"],
                        "earnings": round(r["earnings"] or 0, 2)} for r in top_skills],
        "monthly": [{"month": r["month"], "sales": r["cnt"],
                     "revenue": round(r["revenue"] or 0, 2),
                     "commission": round(r["commission"] or 0, 2)} for r in monthly],
    }


# ═══════════════════════════════════════════════════════════════
# Payment Provider (pluggable)
# ═══════════════════════════════════════════════════════════════

def _process_payment(amount: float, method: str = "mock") -> str:
    """Process a payment. Returns payment reference or empty string on failure.

    Plug in real payment providers here:
      - Stripe: stripe.PaymentIntent.create(amount=amount, currency='usd')
      - Alipay: alipay.api.create_payment(...)
      - WeChat Pay: wechatpay.api.unified_order(...)

    For now, mock always succeeds for free/$0 purchases and simulates
    success for paid purchases (generates a mock reference).
    """
    if amount <= 0:
        return "mock_free_" + uuid.uuid4().hex[:8]

    # In production, replace this with real payment gateway call
    if method == "mock":
        return "mock_pay_" + uuid.uuid4().hex[:8]

    # For real payment providers, return the transaction ID
    # For now, simulate success
    return "sim_" + uuid.uuid4().hex[:8]


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _row_to_purchase(row: sqlite3.Row) -> Purchase:
    def _g(key, default=""):
        try: return row[key]
        except (KeyError, IndexError): return default
    return Purchase(
        purchase_id=row["purchase_id"], skill_id=row["skill_id"],
        buyer_id=row["buyer_id"], author_id=row["author_id"],
        model=PricingModel(row["model"]),
        amount=row["amount"], commission=row["commission"],
        author_earnings=row["author_earnings"],
        status=PurchaseStatus(row["status"]),
        payment_method=_g("payment_method", ""), payment_ref=_g("payment_ref", ""),
        created_at=row["created_at"], completed_at=_g("completed_at", 0.0),
        expires_at=_g("expires_at", 0.0),
    )


def format_price(amount: float) -> str:
    """Format price for display."""
    symbol = {"USD": "$", "CNY": "¥", "EUR": "€"}.get(CURRENCY, "$")
    if amount == 0:
        return "Free"
    if amount == int(amount):
        return f"{symbol}{int(amount)}"
    return f"{symbol}{amount:.2f}"
