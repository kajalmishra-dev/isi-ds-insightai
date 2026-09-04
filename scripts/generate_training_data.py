"""Generate stronger synthetic training + held-out upload data.

Goals:
- Balanced classes with distinctive vocabulary (helps TF-IDF confidence)
- Train and sample_upload texts are DISJOINT
- Timestamps use real datetime arithmetic (resolved_at >= created_at)
- Synthetic / hand-authored for demos — not production customer data
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

DATA_DIR = Path("data")
TRAIN_OUT = DATA_DIR / "complaints.csv"
SAMPLE_OUT = DATA_DIR / "sample_upload.csv"

# ~60 per class — clearer keyword separation for classical ML demos
TRAIN: list[tuple[str, str]] = [
    # technical
    ("App crashes on the login screen every time", "technical"),
    ("Cannot reset my password from the account page", "technical"),
    ("Dashboard keeps showing HTTP error 500", "technical"),
    ("Mobile app freezes after the latest update", "technical"),
    ("Two factor authentication code never validates", "technical"),
    ("Server timeout during large file upload", "technical"),
    ("API integration returns an invalid OAuth token", "technical"),
    ("Notification emails are not being sent at all", "technical"),
    ("Session expires immediately after successful login", "technical"),
    ("Search results never load on the customer portal", "technical"),
    ("Push notifications duplicate every single minute", "technical"),
    ("Dark mode breaks the settings page layout", "technical"),
    ("OTP SMS code never arrives on my phone", "technical"),
    ("Profile photo upload fails with a network error", "technical"),
    ("Websocket disconnects during live support chat", "technical"),
    ("Report export downloads a corrupted ZIP file", "technical"),
    ("SSO login redirects to a blank white page", "technical"),
    ("Browser console shows repeated CORS failures", "technical"),
    ("Keyboard shortcuts stop working after refresh", "technical"),
    ("Attachment preview is stuck on loading spinner", "technical"),
    ("Calendar sync fails with my Google Workspace account", "technical"),
    ("App crashes when switching between workspaces", "technical"),
    ("Form submit button remains disabled forever", "technical"),
    ("Infinite redirect loop on the admin console", "technical"),
    ("Latency spikes make the entire UI unusable", "technical"),
    ("Database query times out on the reports screen", "technical"),
    ("Mobile crash dump appears after opening Messages", "technical"),
    ("Feature flag toggle does not persist after reload", "technical"),
    ("GraphQL endpoint returns 401 for valid API keys", "technical"),
    ("iOS build crashes on launch after MDM install", "technical"),
    ("Android app black screens on biometric unlock", "technical"),
    ("CSV mapper throws a schema validation exception", "technical"),
    ("Background job worker keeps restarting with OOM", "technical"),
    ("SSL certificate warning blocks the secure portal", "technical"),
    ("Webhook retries exhaust and never deliver events", "technical"),
    ("Search index is stale and missing new tickets", "technical"),
    ("PDF renderer fails for multi-page invoices", "technical"),
    ("Desktop client cannot reconnect after sleep mode", "technical"),
    ("Rate limiter blocks legitimate automation scripts", "technical"),
    ("Image OCR pipeline returns empty text results", "technical"),
    ("Audit log viewer throws a JavaScript TypeError", "technical"),
    ("SAML assertion clock skew rejects my IdP login", "technical"),
    ("CDN cache serves an outdated JavaScript bundle", "technical"),
    ("Pagination API skips pages when sorting by date", "technical"),
    ("File virus scanner false-positives every upload", "technical"),
    ("Mobile deep link opens the wrong product screen", "technical"),
    ("Telemetry SDK crashes the app in airplane mode", "technical"),
    ("Admin role permission check returns false negatives", "technical"),
    ("Websocket backlog causes delayed live metrics", "technical"),
    ("Python SDK example fails against the v2 API", "technical"),
    ("Passwordless magic link lands on a 404 route", "technical"),
    ("Browser extension conflicts and breaks autofill", "technical"),
    ("GPU acceleration toggle freezes the canvas editor", "technical"),
    ("Health check endpoint flaps every few minutes", "technical"),
    ("Message queue consumer stalls and stops processing", "technical"),
    ("Local cache corruption forces a full reinstall", "technical"),
    ("Timezone conversion bug shifts meeting times by hours", "technical"),
    ("Drag and drop upload never finishes on Safari", "technical"),
    ("CLI login device flow hangs waiting for approval", "technical"),
    ("Hotfix deploy left the frontend on a blank route", "technical"),
    # billing
    ("Payment failed but the money was still deducted", "billing"),
    ("Invoice amount is incorrect on my latest bill", "billing"),
    ("I was charged twice for the same subscription", "billing"),
    ("Promo code did not apply at checkout", "billing"),
    ("Sales tax was calculated incorrectly on my order", "billing"),
    ("Annual plan renewed without any prior notice", "billing"),
    ("Refund is still pending after ten business days", "billing"),
    ("Card was declined despite sufficient balance", "billing"),
    ("Wrong currency is shown on my invoice PDF", "billing"),
    ("Discount disappeared right after the trial ended", "billing"),
    ("Proration credit is missing after my downgrade", "billing"),
    ("VAT ID was not accepted at checkout", "billing"),
    ("Subscription was cancelled but I am still billed", "billing"),
    ("Payment method update keeps failing with decline", "billing"),
    ("Receipt email has the wrong company legal name", "billing"),
    ("Seat count billed higher than active users", "billing"),
    ("Chargeback opened for an unrecognized payment", "billing"),
    ("Invoice PDF is missing several line items", "billing"),
    ("Auto-renew charged after my cancellation request", "billing"),
    ("Wallet balance was not applied to the order total", "billing"),
    ("Partial refund never posted back to my card", "billing"),
    ("Price increased mid-contract without my consent", "billing"),
    ("Billing address cannot be edited in account settings", "billing"),
    ("Duplicate tax applied on an international order", "billing"),
    ("Store credits expired earlier than the stated policy", "billing"),
    ("I need a corrected invoice for accounting close", "billing"),
    ("ACH payment shows pending for over a week", "billing"),
    ("Wire transfer fee was added without disclosure", "billing"),
    ("Usage overage charges look inflated this month", "billing"),
    ("Coupon stacking rules blocked a valid partner code", "billing"),
    ("Finance asked for a W-9 but the portal upload fails", "billing"),
    ("Monthly statement does not match my bank charges", "billing"),
    ("Free tier limit triggered a surprise paid upgrade", "billing"),
    ("Credit memo was promised but never issued", "billing"),
    ("Billing contact email cannot be changed by admin", "billing"),
    ("Trial conversion charged before the trial end date", "billing"),
    ("Multi-year discount was removed on renewal", "billing"),
    ("Payment intent succeeded twice for one checkout", "billing"),
    ("Currency conversion rate looks outdated on invoice", "billing"),
    ("I was billed for seats of deactivated teammates", "billing"),
    ("Late fee appeared even though payment was on time", "billing"),
    ("Purchase order number is missing from the invoice", "billing"),
    ("Refund went to an old expired card on file", "billing"),
    ("Net-30 terms were ignored and charged immediately", "billing"),
    ("Tax exempt certificate upload keeps getting rejected", "billing"),
    ("Invoice numbering skipped and broke our audit trail", "billing"),
    ("Add-on SKU was billed after we removed the feature", "billing"),
    ("Minimum commit overage was calculated incorrectly", "billing"),
    ("Dunning emails say past due but portal shows paid", "billing"),
    ("I need to split one invoice across two cost centers", "billing"),
    ("Prepaid credits were double-consumed on one invoice", "billing"),
    ("Billing cycle changed from monthly to annual silently", "billing"),
    ("Card verification hold never released after signup", "billing"),
    ("Marketplace fee line item was unexpected on payout", "billing"),
    ("Pro-rated refund math does not match the policy page", "billing"),
    ("I was charged for a region I never enabled", "billing"),
    ("Invoice still lists a cancelled add-on product", "billing"),
    ("Payment failed retry charged me three times overnight", "billing"),
    ("Finance needs a VAT breakdown by country on the bill", "billing"),
    ("Account credit from goodwill never appeared", "billing"),
    # shipping
    ("Delivery arrived two days later than promised", "shipping"),
    ("Package marked delivered but it is still missing", "shipping"),
    ("Wrong item was shipped to my delivery address", "shipping"),
    ("Tracking number never updated after label creation", "shipping"),
    ("Courier left the package outside in the rain", "shipping"),
    ("Address update was not reflected on the shipment", "shipping"),
    ("Express shipping still took five calendar days", "shipping"),
    ("Parcel arrived visibly damaged on arrival", "shipping"),
    ("Label created but the carrier never picked it up", "shipping"),
    ("Wrong warehouse fulfilled and delayed my order", "shipping"),
    ("Customs delay with no status update for a week", "shipping"),
    ("Delivery attempted without ringing the doorbell", "shipping"),
    ("Shipment returned to sender without my request", "shipping"),
    ("Fragile sticker was ignored and the item broke", "shipping"),
    ("Split shipment arrived incomplete missing pieces", "shipping"),
    ("Pickup point was closed when I arrived tonight", "shipping"),
    ("Driver refused to wait for a signature confirmation", "shipping"),
    ("Box was opened and resealed before final delivery", "shipping"),
    ("Shipping estimate jumped right after I paid", "shipping"),
    ("Order stuck in transit for more than two weeks", "shipping"),
    ("Wrong size variant was packed inside the box", "shipping"),
    ("Missing accessories were not included in the package", "shipping"),
    ("Overnight shipping actually delivered next week", "shipping"),
    ("Tracking shows delivered to the wrong city", "shipping"),
    ("Carrier lost the package somewhere mid-route", "shipping"),
    ("My pallet shipment arrived with broken shrink wrap", "shipping"),
    ("Last-mile courier scanned delivered at the depot", "shipping"),
    ("Temperature-controlled shipment arrived warm", "shipping"),
    ("I need a proof of delivery photo for this parcel", "shipping"),
    ("Freight invoice weight does not match the label", "shipping"),
    ("Return label QR code will not scan at the drop-off", "shipping"),
    ("Hazmat package was refused at the shipping counter", "shipping"),
    ("Appointment delivery window was missed by hours", "shipping"),
    ("International airway bill number is invalid", "shipping"),
    ("Carton count on BOL does not match what arrived", "shipping"),
    ("Liftgate service was charged but never provided", "shipping"),
    ("Warehouse short-shipped two units from the order", "shipping"),
    ("Tracking shows out for delivery for three days", "shipping"),
    ("I requested hold at location but it was ignored", "shipping"),
    ("Parcel locker bay was full and returned the box", "shipping"),
    ("Signature required package left without a signature", "shipping"),
    ("Shipping address validation rejected a valid ZIP", "shipping"),
    ("Carrier rerouted my overnight to ground service", "shipping"),
    ("Damaged carton claim needs photos and packing list", "shipping"),
    ("Cross-dock delay added four days with no alert", "shipping"),
    ("I never received the SMS with pickup locker PIN", "shipping"),
    ("Pallet was delivered to the wrong loading dock", "shipping"),
    ("Return RMA shipment is stuck at origin scan", "shipping"),
    ("White-glove delivery team never showed up", "shipping"),
    ("Package dimensions on label caused surcharge dispute", "shipping"),
    ("Same-day courier marked attempt while I was home", "shipping"),
    ("Ocean freight container arrived with wet damage", "shipping"),
    ("I need to change the delivery date before dispatch", "shipping"),
    ("Blind shipment exposed my supplier on the label", "shipping"),
    ("Carrier website tracking conflicts with email updates", "shipping"),
    ("Multi-piece shipment is missing one carton", "shipping"),
    ("Residential surcharge applied to a commercial site", "shipping"),
    ("Delivery photo shows a different building entrance", "shipping"),
    ("My backordered line shipped without the main item", "shipping"),
    ("Customs broker asked for documents we already sent", "shipping"),
    # service
    ("Support agent was rude during the phone call", "service"),
    ("Long hold time with no useful resolution", "service"),
    ("Refund request was ignored for an entire week", "service"),
    ("Chat support disconnected on me repeatedly", "service"),
    ("Escalation ticket was closed without any fix", "service"),
    ("Agent promised a callback but never called back", "service"),
    ("Complaint marked resolved but the issue remains", "service"),
    ("No response to my priority support email", "service"),
    ("Ticket reassigned five times with no clear owner", "service"),
    ("Knowledge base article is outdated and wrong", "service"),
    ("Support refused to escalate to engineering", "service"),
    ("Agent asked me to repeat details three times", "service"),
    ("Case closed after an automated reply only", "service"),
    ("Weekend support is unavailable despite my plan", "service"),
    ("Chatbot loops and never opens a human ticket", "service"),
    ("Manager review was promised but never scheduled", "service"),
    ("SLA was breached with no apology or update", "service"),
    ("Agent shared incorrect troubleshooting steps", "service"),
    ("Phone menu has no option for billing help", "service"),
    ("Support language pack is missing for my region", "service"),
    ("Follow-up email bounced from the support alias", "service"),
    ("Priority queue still waited over four hours", "service"),
    ("Agent hung up during active troubleshooting", "service"),
    ("Community forum moderation ignored my report", "service"),
    ("Onboarding specialist missed the scheduled call", "service"),
    ("I need a named account manager for this severity", "service"),
    ("Support transcript was never emailed as promised", "service"),
    ("Customer success ignored my renewal risk email", "service"),
    ("Help desk closed my case as duplicate incorrectly", "service"),
    ("I was told to post publicly instead of private help", "service"),
    ("Tier-2 engineer never joined the bridge call", "service"),
    ("Support rating survey arrived before any fix", "service"),
    ("Agent could not find my account with the CRM ID", "service"),
    ("I asked for a supervisor and was put on mute", "service"),
    ("Ticket status says waiting on customer incorrectly", "service"),
    ("Concierge onboarding checklist was never shared", "service"),
    ("Support hours listed online do not match reality", "service"),
    ("I received three conflicting answers from agents", "service"),
    ("Escalation path is undocumented for enterprise", "service"),
    ("Live agent transferred me and dropped the chat", "service"),
    ("Support asked for screenshots I already attached", "service"),
    ("My accessibility request was dismissed as low priority", "service"),
    ("Quarterly business review was cancelled last minute", "service"),
    ("Agent read from a script and ignored my question", "service"),
    ("I need a written RCA and only got a verbal apology", "service"),
    ("Support portal search returns irrelevant articles", "service"),
    ("Customer care promised a goodwill credit then denied it", "service"),
    ("My complaint was marked spam by the intake bot", "service"),
    ("Regional support cannot handle my local language", "service"),
    ("I was told to wait 10 business days with no update", "service"),
    ("Agent closed the ticket while I was still typing", "service"),
    ("Enterprise hotline routes to the general queue", "service"),
    ("Support refused screen share for a complex issue", "service"),
    ("I need after-hours emergency support for outage", "service"),
    ("Case notes are empty so every agent starts over", "service"),
    ("Support promised a patch date and then went silent", "service"),
    ("My NPS follow-up call never happened", "service"),
    ("Help desk will not reopen a wrongly closed case", "service"),
    ("I asked for multilingual support and got English only", "service"),
    ("Agent blamed me for a known product defect", "service"),
]

HELD_OUT: list[tuple[str, str]] = [
    # technical
    ("The mobile client dies whenever I open Settings", "technical"),
    ("Password reset link says it is already expired", "technical"),
    ("Admin console throws a 502 after I save changes", "technical"),
    ("Face ID unlock fails after the latest release", "technical"),
    ("Webhook signatures keep validating as invalid", "technical"),
    ("CSV import stalls at ninety percent forever", "technical"),
    ("OAuth refresh token rotation breaks the desktop app", "technical"),
    ("Nightly backup job fails with a disk full error", "technical"),
    ("Safari tabs crash when opening the analytics board", "technical"),
    ("VPN split tunnel blocks access to the internal API", "technical"),
    ("Feature branch preview environment returns 503", "technical"),
    ("Log stream viewer freezes after a few thousand lines", "technical"),
    # billing
    ("I was billed twice for January already", "billing"),
    ("My statement shows a fee I never approved", "billing"),
    ("Coupon worked yesterday but fails today", "billing"),
    ("Sales tax line looks wrong for my state", "billing"),
    ("Cancellation still shows active and charging", "billing"),
    ("Wire transfer refund has not landed yet", "billing"),
    ("Invoice still includes seats for offboarded staff", "billing"),
    ("My prepaid credit balance dropped without usage", "billing"),
    ("Card on file was charged after I removed it", "billing"),
    ("Finance needs a corrected VAT invoice urgently", "billing"),
    ("Annual discount disappeared on silent auto-renew", "billing"),
    ("Payment receipt amount does not match the portal", "billing"),
    # shipping
    ("My parcel shows delivered to a neighbor I do not know", "shipping"),
    ("Tracking froze after leaving the depot", "shipping"),
    ("Box arrived crushed and wet inside", "shipping"),
    ("I ordered blue but received green", "shipping"),
    ("Priority overnight took four business days", "shipping"),
    ("Pickup locker code never arrived by SMS", "shipping"),
    ("Carrier claims delivered but lobby camera shows nothing", "shipping"),
    ("Return package is stuck with no outbound scan", "shipping"),
    ("Freight appointment was missed and storage fees started", "shipping"),
    ("Wrong SKU quantity arrived versus packing slip", "shipping"),
    ("Express label was downgraded without notice", "shipping"),
    ("International shipment held for missing commercial invoice", "shipping"),
    # service
    ("The agent dismissed my issue without reading it", "service"),
    ("I waited on hold for almost two hours", "service"),
    ("My VIP ticket got closed with a canned reply", "service"),
    ("Nobody called back after promising a manager review", "service"),
    ("Live chat ended while I was typing the details", "service"),
    ("Support said it was fixed but nothing changed", "service"),
    ("I asked for escalation and got another FAQ link", "service"),
    ("Account manager skipped our scheduled check-in", "service"),
    ("Support rating was requested before any human replied", "service"),
    ("Ticket bounced between teams with no resolution owner", "service"),
    ("Agent contradicted yesterday's written guidance", "service"),
    ("Emergency outage line routed me to billing IVR", "service"),
]

LAG_HOURS = [3, 6, 10, 16, 22, 28, 36, 48, 60, 72, 96, 120]


def _stamp_rows(pairs: list[tuple[str, str]], start: datetime) -> list[dict]:
    rows: list[dict] = []
    for idx, (text, category) in enumerate(pairs):
        created = start + timedelta(hours=idx * 3)
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


def _assert_unique(pairs: list[tuple[str, str]], label: str) -> None:
    texts = [t.casefold() for t, _ in pairs]
    if len(texts) != len(set(texts)):
        raise SystemExit(f"{label}: duplicate texts detected")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    _assert_unique(TRAIN, "TRAIN")
    _assert_unique(HELD_OUT, "HELD_OUT")

    train_texts = {t.casefold() for t, _ in TRAIN}
    held_texts = {t.casefold() for t, _ in HELD_OUT}
    overlap = train_texts & held_texts
    if overlap:
        raise SystemExit(f"Train/held-out overlap detected: {sorted(overlap)[:5]}")

    train_df = pd.DataFrame(_stamp_rows(TRAIN, datetime(2026, 1, 2, 9, 0, 0)))
    sample_df = pd.DataFrame(_stamp_rows(HELD_OUT, datetime(2026, 3, 1, 10, 0, 0)))

    for name, frame in (("train", train_df), ("sample", sample_df)):
        created = pd.to_datetime(frame["created_at"])
        resolved = pd.to_datetime(frame["resolved_at"])
        bad = int((resolved < created).sum())
        if bad:
            raise SystemExit(f"{name}: {bad} rows have resolved_at < created_at")

    # Balance check
    counts = train_df["category"].value_counts()
    if counts.min() < 40:
        raise SystemExit(f"Training set too thin per class: {counts.to_dict()}")

    train_df.to_csv(TRAIN_OUT, index=False)
    sample_df[["text", "created_at", "resolved_at"]].to_csv(SAMPLE_OUT, index=False)

    print(f"Wrote {len(train_df)} training rows -> {TRAIN_OUT}")
    print(counts.to_string())
    print(f"Wrote {len(sample_df)} held-out upload rows -> {SAMPLE_OUT}")
    print(sample_df.assign(category=[c for _, c in HELD_OUT])["category"].value_counts().to_string())
    print("Overlap check: OK (0 shared texts)")


if __name__ == "__main__":
    main()
