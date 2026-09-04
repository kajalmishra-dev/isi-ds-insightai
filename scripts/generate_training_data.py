"""Generate synthetic training data and a held-out upload sample.

Important:
- Training texts and sample_upload texts are DISJOINT (no overlap).
- Timestamps use real datetime arithmetic (resolved_at >= created_at).
- Data is synthetic / hand-authored for demos — not production customer data.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

DATA_DIR = Path("data")
TRAIN_OUT = DATA_DIR / "complaints.csv"
SAMPLE_OUT = DATA_DIR / "sample_upload.csv"

# Training set (labeled)
TRAIN = [
    # technical
    ("App crashes on login screen", "technical"),
    ("Cannot reset my password", "technical"),
    ("Dashboard keeps showing error 500", "technical"),
    ("Mobile app freezes after update", "technical"),
    ("Two factor authentication not working", "technical"),
    ("Server timeout during file upload", "technical"),
    ("API integration returns invalid token", "technical"),
    ("Notification emails not being sent", "technical"),
    ("Session expires immediately after login", "technical"),
    ("Search results never load on the portal", "technical"),
    ("Push notifications duplicate every minute", "technical"),
    ("Dark mode breaks the settings page layout", "technical"),
    ("OTP code never arrives on my phone", "technical"),
    ("Profile photo upload fails with network error", "technical"),
    ("Websocket disconnects during live chat", "technical"),
    ("Report export downloads a corrupted file", "technical"),
    ("SSO login redirects to a blank page", "technical"),
    ("Browser console shows CORS failures", "technical"),
    ("Keyboard shortcuts stop working after refresh", "technical"),
    ("Attachment preview is stuck on loading spinner", "technical"),
    ("Calendar sync fails with Google account", "technical"),
    ("App crashes when switching workspaces", "technical"),
    ("Form submit button remains disabled forever", "technical"),
    ("Infinite redirect loop on admin console", "technical"),
    ("Latency spikes make the UI unusable", "technical"),
    # billing
    ("Payment failed but money was deducted", "billing"),
    ("Invoice amount is incorrect", "billing"),
    ("Charged twice for same subscription", "billing"),
    ("Promo code did not apply at checkout", "billing"),
    ("Tax was calculated incorrectly", "billing"),
    ("Annual plan renewed without notice", "billing"),
    ("Refund still pending after 10 days", "billing"),
    ("Card declined despite sufficient balance", "billing"),
    ("Wrong currency shown on my invoice", "billing"),
    ("Discount disappeared after trial ended", "billing"),
    ("Proration credit missing after downgrade", "billing"),
    ("VAT ID was not accepted at checkout", "billing"),
    ("Subscription cancelled but still billed", "billing"),
    ("Payment method update keeps failing", "billing"),
    ("Receipt email has the wrong company name", "billing"),
    ("Seat count billed higher than active users", "billing"),
    ("Chargeback opened for unrecognized payment", "billing"),
    ("Invoice PDF is missing line items", "billing"),
    ("Auto-renew charged after cancellation request", "billing"),
    ("Wallet balance not applied to the order", "billing"),
    ("Partial refund never posted to my card", "billing"),
    ("Price increased mid-contract without consent", "billing"),
    ("Billing address cannot be edited", "billing"),
    ("Duplicate tax applied on international order", "billing"),
    ("Credits expired earlier than stated policy", "billing"),
    # shipping
    ("Delivery arrived two days late", "shipping"),
    ("Package marked delivered but missing", "shipping"),
    ("Wrong item shipped to my address", "shipping"),
    ("Tracking number never updated", "shipping"),
    ("Courier left package in rain", "shipping"),
    ("Address update not reflected in order", "shipping"),
    ("Express shipping took five days", "shipping"),
    ("Parcel damaged on arrival", "shipping"),
    ("Label created but package not picked up", "shipping"),
    ("Wrong warehouse fulfilled my order", "shipping"),
    ("Customs delay with no status update", "shipping"),
    ("Delivery attempted without doorbell ring", "shipping"),
    ("Returned to sender without my request", "shipping"),
    ("Fragile sticker ignored, item broken", "shipping"),
    ("Split shipment arrived incomplete", "shipping"),
    ("Pickup point closed when I arrived", "shipping"),
    ("Driver refused to wait for signature", "shipping"),
    ("Box opened and resealed before delivery", "shipping"),
    ("Shipping estimate jumped after payment", "shipping"),
    ("Order stuck in transit for two weeks", "shipping"),
    ("Wrong size variant packed in the box", "shipping"),
    ("Missing accessories in the package", "shipping"),
    ("Overnight shipping delivered next week", "shipping"),
    ("Tracking shows delivered to wrong city", "shipping"),
    ("Carrier lost the package mid-route", "shipping"),
    # service
    ("Support agent was rude on call", "service"),
    ("Long hold time with no resolution", "service"),
    ("Refund request ignored for a week", "service"),
    ("Chat support disconnected repeatedly", "service"),
    ("Escalation ticket closed without fix", "service"),
    ("Agent promised callback but never called", "service"),
    ("Complaint marked resolved but issue remains", "service"),
    ("No response to priority support email", "service"),
    ("Ticket reassigned five times with no owner", "service"),
    ("Knowledge base article is outdated", "service"),
    ("Support refused to escalate to engineering", "service"),
    ("Agent asked me to repeat details three times", "service"),
    ("Case closed after automated reply only", "service"),
    ("Weekend support is unavailable despite plan", "service"),
    ("Chatbot loops and never opens a human ticket", "service"),
    ("Manager review promised but never scheduled", "service"),
    ("SLA breached with no apology or update", "service"),
    ("Agent shared incorrect troubleshooting steps", "service"),
    ("Phone menu has no option for billing help", "service"),
    ("Support language pack missing for my region", "service"),
    ("Follow-up email bounced from support alias", "service"),
    ("Priority queue still waited over four hours", "service"),
    ("Agent hung up during active troubleshooting", "service"),
    ("Community forum moderation ignored report", "service"),
    ("Onboarding specialist missed the scheduled call", "service"),
]

# Held-out demo upload texts — intentionally NOT in TRAIN
HELD_OUT = [
    ("The mobile client dies whenever I open Settings", "technical"),
    ("Password reset link says it is already expired", "technical"),
    ("Admin console throws a 502 after I save changes", "technical"),
    ("Face ID unlock fails after the latest release", "technical"),
    ("Webhook signatures keep validating as invalid", "technical"),
    ("CSV import stalls at ninety percent forever", "technical"),
    ("I was billed twice for January already", "billing"),
    ("My statement shows a fee I never approved", "billing"),
    ("Coupon worked yesterday but fails today", "billing"),
    ("Sales tax line looks wrong for my state", "billing"),
    ("Cancellation still shows active and charging", "billing"),
    ("Wire transfer refund has not landed yet", "billing"),
    ("My parcel shows delivered to a neighbor I do not know", "shipping"),
    ("Tracking froze after leaving the depot", "shipping"),
    ("Box arrived crushed and wet inside", "shipping"),
    ("I ordered blue but received green", "shipping"),
    ("Priority overnight took four business days", "shipping"),
    ("Pickup locker code never arrived by SMS", "shipping"),
    ("The agent dismissed my issue without reading it", "service"),
    ("I waited on hold for almost two hours", "service"),
    ("My VIP ticket got closed with a canned reply", "service"),
    ("Nobody called back after promising a manager review", "service"),
    ("Live chat ended while I was typing the details", "service"),
    ("Support said it was fixed but nothing changed", "service"),
]

LAG_HOURS = [2, 5, 12, 20, 30, 48, 72, 120]


def _stamp_rows(pairs: list[tuple[str, str]], start: datetime) -> list[dict]:
    rows: list[dict] = []
    for idx, (text, category) in enumerate(pairs):
        created = start + timedelta(hours=idx * 5)
        lag = timedelta(hours=LAG_HOURS[idx % len(LAG_HOURS)])
        resolved = created + lag
        rows.append(
            {
                "text": text,
                "category": category,
                "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
                "resolved_at": resolved.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return rows


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    train_texts = {t.casefold() for t, _ in TRAIN}
    held_texts = {t.casefold() for t, _ in HELD_OUT}
    overlap = train_texts & held_texts
    if overlap:
        raise SystemExit(f"Train/held-out overlap detected: {sorted(overlap)[:5]}")

    train_df = pd.DataFrame(_stamp_rows(TRAIN, datetime(2026, 1, 2, 9, 0, 0)))
    sample_df = pd.DataFrame(_stamp_rows(HELD_OUT, datetime(2026, 3, 1, 10, 0, 0)))

    # Guard: resolved_at must never precede created_at
    for name, frame in (("train", train_df), ("sample", sample_df)):
        created = pd.to_datetime(frame["created_at"])
        resolved = pd.to_datetime(frame["resolved_at"])
        bad = int((resolved < created).sum())
        if bad:
            raise SystemExit(f"{name}: {bad} rows have resolved_at < created_at")

    train_df.to_csv(TRAIN_OUT, index=False)
    sample_df[["text", "created_at", "resolved_at"]].to_csv(SAMPLE_OUT, index=False)

    print(f"Wrote {len(train_df)} training rows -> {TRAIN_OUT}")
    print(train_df["category"].value_counts().to_string())
    print(f"Wrote {len(sample_df)} held-out upload rows -> {SAMPLE_OUT}")
    print("Overlap check: OK (0 shared texts)")


if __name__ == "__main__":
    main()
