import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta

# =========================
# PAGE SETUP & STYLES
# =========================
st.set_page_config(page_title="Rideshare Intake Qualifier", layout="wide")

st.markdown("""
<style>
h1 {font-size: 2.0rem !important;}
h2 {font-size: 1.5rem !important; margin-top: 0.6rem;}
.section {padding: 0.5rem 0 0.25rem 0;}
.badge-ok   {background:#16a34a; color:white; padding:12px 16px; border-radius:12px; font-size:22px; text-align:center;}
.badge-no   {background:#dc2626; color:white; padding:12px 16px; border-radius:12px; font-size:22px; text-align:center;}
.badge-note {background:#1f2937; color:#f9fafb; padding:8px 12px; border-radius:10px; font-size:14px; display:inline-block;}
.note-wag {border:1px solid #c7f0d2; border-left:8px solid #16a34a; border-radius:8px; padding:10px 12px; margin:8px 0; background:#f0fdf4; color:#064e3b;}
.note-tri {border:1px solid #cfe8ff; border-left:8px solid #2563eb; border-radius:8px; padding:10px 12px; margin:8px 0; background:#eff6ff; color:#1e3a8a;}
.note-muted {border:1px dashed #d1d5db; border-radius:8px; padding:10px 12px; margin:8px 0; background:#f9fafb; color:#374151;}
.script {border-left:4px solid #9ca3af; background:#f3f4f6; color:#111827; padding:12px 14px; border-radius:8px; margin:8px 0 12px 0; font-size:0.97rem;}
.callout {border-left:6px solid #2563eb; background:#eef2ff; color:#1e3a8a; padding:12px 14px; border-radius:8px; margin:8px 0 12px 0;}
.small {font-size: 0.9rem; color:#4b5563;}
hr {border:0; border-top:1px solid #e5e7eb; margin:12px 0;}
[data-testid="stDataFrame"] div, [data-testid="stTable"] div {font-size: 1rem;}
.copy {font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; white-space:pre-wrap;}
.kv {font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;}
</style>
""", unsafe_allow_html=True)

TODAY = datetime.now()

# =========================
# BASE SOL TABLE (general tort)
# =========================
TORT_SOL = {
    "Kentucky":1,"Louisiana":1,"Tennessee":1,
    "Alabama":2,"Alaska":2,"Arizona":2,"California":2,"Colorado":2,"Connecticut":2,"Delaware":2,"Georgia":2,
    "Hawaii":2,"Idaho":2,"Illinois":2,"Indiana":2,"Iowa":2,"Kansas":2,"Minnesota":2,"Nevada":2,"New Jersey":2,
    "Ohio":2,"Oklahoma":2,"Oregon":2,"Pennsylvania":2,"Texas":2,"Virginia":2,"West Virginia":2,
    "Arkansas":3,"D.C.":3,"Maryland":3,"Massachusetts":3,"Michigan":3,"Mississippi":3,"Montana":3,"New Hampshire":3,
    "New Mexico":3,"New York":3,"North Carolina":3,"Rhode Island":3,"South Carolina":3,"South Dakota":3,"Vermont":3,
    "Washington":3,"Wisconsin":3,
    "Florida":4,"Nebraska":4,"Utah":4,"Wyoming":4,
    "Missouri":5,
    "Maine":6,"North Dakota":6,
}

STATE_ALIAS = {"Washington DC": "D.C.", "District of Columbia": "D.C."}
STATES = sorted(set(list(TORT_SOL.keys()) + ["D.C."]))

# =========================
# SEXUAL-ASSAULT EXTENSIONS (years=None means "No SOL")
# =========================
SA_EXT = {
    "California":   {"penetration": None, "other": None,
                     "summary": "No SOL for touching of sexual body parts, rape, digital penetration, oral penetration, vaginal penetration, anal penetration, etc."},
    "New York":     {"penetration": 10,   "other": 10,
                     "summary": "10-year SOL for touching of sexual body parts, rape, digital penetration, oral penetration, vaginal penetration, anal penetration, etc."},
    "Texas":        {"penetration": 5,    "other": 2,
                     "summary": "5-year SOL for rape/penetration of mouth, anus, or vagina; 2-year SOL for all other conduct."},
    "Illinois":     {"penetration": None, "other": 2,
                     "summary": "No SOL for rape/penetration of mouth, anus, or vagina; 2-year SOL for all other conduct."},
    "Connecticut":  {"penetration": None, "other": 2,
                     "summary": "No SOL for rape/penetration of mouth, anus, or vagina; 2-year SOL for all other conduct."},
}

# =========================
# HELPERS
# =========================
def script_block(text: str):
    if not text: return
    st.markdown(f"<div class='script'>{text}</div>", unsafe_allow_html=True)

def badge(ok: bool, label: str):
    css = "badge-ok" if ok else "badge-no"
    st.markdown(f"<div class='{css}'>{label}</div>", unsafe_allow_html=True)

def fmt_date(dt): return dt.strftime("%Y-%m-%d") if dt else "—"
def fmt_dt(dt): return dt.strftime("%Y-%m-%d %H:%M") if dt else "—"

def join_list(values, dash_if_empty=True):
    if not values:
        return "—" if dash_if_empty else ""
    return ", ".join([str(v) for v in values])

def tier_and_aggravators(flags):
    t1 = bool(flags.get("Rape/Penetration") or flags.get("Forced Oral/Forced Touching"))
    t2 = bool(flags.get("Touching/Kissing w/o Consent") or flags.get("Indecent Exposure") or flags.get("Masturbation Observed"))
    aggr_kidnap = bool(flags.get("Kidnapping Off-Route w/ Threats"))
    aggr_imprison = bool(flags.get("False Imprisonment w/ Threats"))
    aggr = []
    if aggr_kidnap: aggr.append("Kidnapping w/ threats")
    if aggr_imprison: aggr.append("False imprisonment w/ threats")
    if t1: base = "Tier 1"
    elif t2: base = "Tier 2"
    else: base = "Unclear"
    label = f"{base} (+ Aggravators: {', '.join(aggr)})" if base in ("Tier 1","Tier 2") and aggr else base
    return label, aggr

def sa_category(flags):
    if flags.get("Rape/Penetration") or flags.get("Forced Oral/Forced Touching"):
        return "penetration"
    if flags.get("Touching/Kissing w/o Consent") or flags.get("Indecent Exposure") or flags.get("Masturbation Observed"):
        return "other"
    return None

def sol_rule_for(state, category):
    if category and state in SA_EXT:
        data = SA_EXT[state]
        years = data[category]
        summary = data["summary"]
        return years, f"{state}: {summary}", True
    years = TORT_SOL.get(state)
    return years, f"{state}: General tort SOL = {years} year(s).", False

def categorical_brief(flags):
    buckets = []
    if flags.get("Rape/Penetration"): buckets.append("rape/penetration")
    if flags.get("Forced Oral/Forced Touching"): buckets.append("forced oral/forced touching")
    if flags.get("Touching/Kissing w/o Consent"): buckets.append("unwanted touching/kissing")
    if flags.get("Indecent Exposure"): buckets.append("indecent exposure")
    if flags.get("Masturbation Observed"): buckets.append("masturbation observed")
    if flags.get("Kidnapping Off-Route w/ Threats"): buckets.append("kidnapping off-route w/ threats")
    if flags.get("False Imprisonment w/ Threats"): buckets.append("false imprisonment w/ threats")
    return ", ".join(buckets) if buckets else "—"

# =========================
# APP
# =========================
st.title("Rideshare Intake Qualifier · Script-Calibrated (Vertical)")

def render():
    # ---------- INTRODUCTION (0) ----------
    script_block(
        "INTRODUCTION\n"
        "Thank you for calling the Advocate Rights Center, this is **[Your Name]**. How are you doing today?\n\n"
        "May I have your **full name**, and then your **full legal name** exactly as it appears on your ID?\n\n"
        "Before we continue, may I have your **permission to record** this call for legal and training purposes? "
        "It will remain private and confidential, and it’s never filed publicly unless you approve and a case goes to court. "
        "Fewer than 1 in 1,000 cases ever do, since most resolve through settlement."
    )
    caller_full_name = st.text_input("Full name (as provided verbally)", key="caller_full_name")
    caller_legal_name = st.text_input("Full legal name (exact on ID)", key="caller_legal_name")
    consent_recording = st.toggle("Permission to record (private & confidential)", value=False, key="consent_recording")

    st.markdown("---")

    # =========================
    # Q1–Q3 (vertical)
    # =========================
    st.markdown("### 1) Story & First-Level Qualification")

    # Q1
    st.markdown("**Q1. Describe what happened during your ride.**")
    narr = st.text_area("Caller narrative", key="q1_narr")
    script_block(
        "Rapport: That must have been terrifying. I’m so sorry you experienced that. "
        "Thank you for trusting me with your story."
    )

    # Q2
    st.markdown("**Q2. Which rideshare platform was it?**")
    company = st.selectbox("Select platform", ["Uber", "Lyft", "Other"], key="q2_company")

    # Q3
    st.markdown("**Q3. Do you have a receipt for the ride (in-app or email)?**")
    receipt = st.toggle("Receipt provided (email/app/PDF)", value=False, key="q3_receipt_toggle")
    receipt_evidence = st.multiselect(
        "What can you provide as receipt evidence?",
        ["PDF", "Screenshot of Receipt", "Email", "In-App Receipt (screenshot)", "Other"],
        key="receipt_evidence"
    )
    receipt_evidence_other = st.text_input("If Other, describe", key="receipt_evidence_other")
    if receipt_evidence_other and "Other" not in receipt_evidence:
        receipt_evidence.append(f"Other: {receipt_evidence_other.strip()}")

    if not receipt:
        st.markdown(
            "<div class='callout'><b>Text to send:</b><br>"
            "<span class='copy'>Forward your receipt to <b>jay@advocaterightscenter.com</b> by selecting the ride in Ride History and choosing “Resend Receipt.”"
            "<br>(Msg Rates Apply. Txt STOP to cancel/HELP for help)</span></div>",
            unsafe_allow_html=True
        )

    # ---- Education Insert #1 (after Q1–Q3) ----
    script_block(
        "EDUCATION #1 — How This Happened\n"
        "Uber and Lyft have been exposed for failing to screen drivers, ignoring complaints, and misleading riders about safety. "
        "The New York Times reported sealed court records showing **over 400,000** sexual assault/misconduct reports to Uber from 2017–2022 "
        "— about **one every 8 minutes** — while Uber publicly admitted only a small fraction of that. "
        "By stepping forward, survivors help hold these companies accountable and make rides safer."
    )

    st.markdown("---")

    # =========================
    # Q4–Q6
    # =========================
    st.markdown("### 3) Second-Level Qualification (Reporting & Location)")

    # Q4
    st.markdown("**Q4. Do you remember the date this happened?**")
    has_incident_date = st.toggle("Caller confirms they know the date", value=False, key="q4_hasdate")
    incident_date = st.date_input("Select Incident Date", value=TODAY.date(), key="q4_date") if has_incident_date else None
    incident_time = st.time_input("Incident Time (for timing rules)", value=time(21, 0), key="time_for_calc")

    # Q5
    st.markdown("**Q5. Did you report the incident to anyone?** (Uber/Lyft, Police, Physician, Therapist, Family/Friend)")
    reported_to = st.multiselect(
        "Select all that apply",
        ["Rideshare Company","Physician","Friend or Family Member","Therapist","Police Department","NO (DQ, UNLESS TIER 1 OR MINOR)"],
        key="q5_reported"
    )

    report_dates = {}
    family_report_dt = None
    if "Rideshare Company" in reported_to:
        report_dates["Rideshare company"] = st.date_input("Date reported to Rideshare company", value=TODAY.date(), key="q5a_dt_rs")
    if "Police Department" in reported_to:
        report_dates["Police"] = st.date_input("Date reported to Police", value=TODAY.date(), key="q5a_dt_police")
    if "Therapist" in reported_to:
        report_dates["Therapist"] = st.date_input("Date reported to Therapist", value=TODAY.date(), key="q5a_dt_ther")
    if "Physician" in reported_to:
        report_dates["Physician"] = st.date_input("Date reported to Physician", value=TODAY.date(), key="q5a_dt_phys")
    if "Friend or Family Member" in reported_to:
        ff_date = st.date_input("Date informed Family/Friend", value=TODAY.date(), key="q5a_dt_ff")
        ff_time = st.time_input("Time informed Family/Friend", value=time(21,0), key="q5a_tm_ff")
        report_dates["Family/Friends"] = ff_date
        family_report_dt = datetime.combine(ff_date, ff_time)

    # Q6
    st.markdown("**Q6. Where did it happen?**")
    scope_choice = st.selectbox(
        "Inside the car, just outside, or in furtherance after exiting?",
        ["Inside the car", "Just outside the car", "Furtherance from the car", "Unclear"],
        key="scope_choice"
    )
    inside_near = scope_choice in ["Inside the car", "Just outside the car", "Furtherance from the car"]

    # ---- Education Insert #2 (after Q4–Q6) ----
    script_block(
        "EDUCATION #2 — The “Safe Rides Fee”\n"
        "Uber introduced a $1 **Safe Rides Fee** years ago, claiming it funded safety initiatives like background checks and technology upgrades. "
        "Investigations later found much of the estimated **$500 million** collected wasn’t directly used for those improvements. "
        "The fee was eventually renamed the **“booking fee.”** Survivors were paying for safety that often didn’t materialize."
    )

    st.markdown("---")

    # =========================
    # Q7–Q9
    # =========================
    st.markdown("### 5) Injury & Case-Support Questions")

    # Q7
    st.markdown("**Q7. Were you injured physically, or have you experienced emotional effects afterward?**")
    injury_physical = st.checkbox("Physical injury", key="inj_physical")
    injury_emotional = st.checkbox("Emotional effects (anxiety, nightmares, etc.)", key="inj_emotional")
    injuries_summary = st.text_area("If comfortable, briefly describe injuries/effects", key="injuries_summary")

    # Q8
    st.markdown("**Q8. Have you spoken to a doctor, therapist, or counselor?**")
    provider_name = st.text_input("Provider name (optional)", key="provider_name")
    provider_facility = st.text_input("Facility/Clinic (optional)", key="provider_facility")
    therapy_start = st.date_input("Therapy start date (if any)", value=TODAY.date(), key="therapy_start") if st.toggle("Add therapy start date", key="therapy_toggle", value=False) else None

    # Q9
    st.markdown("**Q9. Do you take any medications related to this?**")
    medication_name = st.text_input("Medication (optional)", key="medication_name")
    pharmacy_name = st.text_input("Pharmacy (optional)", key="pharmacy_name")

    # ---- Education Insert #3 (after Q7–Q9) ----
    script_block(
        "EDUCATION #3 — Law Firm & Contingency\n"
        "You may have a valid case. You hire the law firm on **contingency** — no upfront costs, no out-of-pocket fees; "
        "you only owe if there’s a recovery. We are the intake center for **The Wagstaff Law Firm**. Their attorneys are nationally recognized "
        "(many named **Super Lawyers**) and have been appointed to multiple **Plaintiff Steering Committees** in major corporate-negligence cases. "
        "They’re applying that leadership to hold Uber and Lyft accountable."
    )

    st.markdown("---")

    # =========================
    # Contact & Ride Details (supporting the script)
    # =========================
    st.markdown("### Contact & Ride Details")

    caller_phone = st.text_input("Best phone number", key="caller_phone")
    caller_email = st.text_input("Best email", key="caller_email")

    st.markdown("**Pickup / Drop-off**")
    pickup = st.text_input("Pickup location (address/description)", key="pickup")
    dropoff = st.text_input("Drop-off location (address/description)", key="dropoff")
    state = st.selectbox("Incident state", STATES, index=(STATES.index("California") if "California" in STATES else 0), key="q_state")

    st.markdown("**Rideshare submission & response (if any)**")
    rs_submit_how = st.text_input("How did you submit to Uber/Lyft? (email/app/other)", key="q8_submit_how")
    rs_received_response = st.toggle("Company responded", value=False, key="q9_resp_toggle")
    rs_response_detail = st.text_input("If yes, what did they say? (optional)", key="q9_resp_detail")

    st.markdown("**Driver information (if available)**")
    driver_profile = st.text_input("Driver name/profile details (optional)", key="driver_profile")

    st.markdown("**Standard screening**")
    felony = st.toggle("Any felony conviction history", value=False, key="q10_felony")

    # =========================
    # Request for Proof & Process
    # =========================
    st.markdown("### Settlement Process & Request for Proof")

    script_block(
        "After discovery, courts schedule **bellwether test trials** — real trials that guide settlement ranges for everyone else. "
        "That means you typically **won’t have to retell your story in court**; your records and documents will speak for you, "
        "and your settlement is based on your **individual** experience."
    )

    proof_methods = st.multiselect(
        "How would you like to send documentation (receipts/screenshots/ID/therapy notes/prescriptions)?",
        ["Secure camera link (we text you a link)", "Email to jay@advocaterightscenter.com", "FedEx/UPS scan/fax from store"],
        key="proof_methods"
    )
    if "Email to jay@advocaterightscenter.com" in proof_methods:
        st.markdown(
            "<div class='callout'><b>Email Instructions</b><br>"
            "<span class='copy'>Send photos/PDFs to <b>jay@advocaterightscenter.com</b>. "
            "In the app: Ride History → select ride → “Resend Receipt.”</span></div>",
            unsafe_allow_html=True
        )
    if "Secure camera link (we text you a link)" in proof_methods:
        st.markdown(
            "<div class='note-muted'>We’ll send a one-time secure link that opens your phone’s camera to capture the document.</div>",
            unsafe_allow_html=True
        )
        st.button("Send secure upload link (placeholder)")
    if "FedEx/UPS scan/fax from store" in proof_methods:
        st.markdown(
            "<div class='note-muted'>Ask staff to scan/fax to <b>jay@advocaterightscenter.com</b>. Keep the receipt for your records.</div>",
            unsafe_allow_html=True
        )

    proof_uploads = st.file_uploader(
        "Upload proof now (ride receipt, therapy/medical note, police confirmation) — images or PDFs",
        type=["pdf", "png", "jpg", "jpeg", "heic"],
        accept_multiple_files=True,
        key="proof_uploads"
    )

    # ---- Education Insert #4 (timeline) ----
    script_block(
        "EDUCATION #4 — Timeline for Settlement Distribution\n"
        "Once bellwether trials conclude, results typically spark **settlement negotiations**. "
        "That’s when **distributions begin** — survivors don’t have to wait for every trial to finish."
    )

    # =========================
    # SSN (last-4 option)
    # =========================
    st.markdown("### Identity for Records (Optional)")
    script_block(
        "Some providers require identity verification before releasing **medical records**. "
        "The firm may ask for your Social Security number. If you prefer, you can share just the **last 4 digits** now; "
        "that is often enough for HIPAA releases."
    )
    ssn_last4 = st.text_input("SSN last 4 (optional)", max_chars=4, key="ssn_last4")

    st.markdown("---")

    # =========================
    # INTERNAL ELIGIBILITY SWITCHES (Agent use)
    # =========================
    with st.expander("Agent-only Eligibility Switches (keep OFF until verified)"):
        colE1, colE2, colE3, colE4 = st.columns(4)
        with colE1:
            female_rider = st.toggle("Female rider", value=False, key="elig_female")
        with colE2:
            gov_id = st.toggle("Government ID provided", value=False, key="elig_id")
        with colE3:
            has_atty = st.toggle("Already has an attorney", value=False, key="elig_atty")
        with colE4:
            purpose = st.text_input("Purpose of ride (optional/internal)", key="purpose")

        colX1, colX2, colX3, colX4 = st.columns(4)
        with colX1:
            driver_weapon = st.selectbox("Driver used/threatened weapon?", ["No","Non-lethal defensive (e.g., pepper spray)","Yes"], key="elig_driver_weapon")
        with colX2:
            client_weapon = st.toggle("Client carried a weapon", value=False, key="elig_client_weapon")
        with colX3:
            verbal_only = st.toggle("Verbal abuse only (no sexual acts)", value=False, key="elig_verbal_only")
        with colX4:
            attempt_only = st.toggle("Attempt/minor contact only", value=False, key="elig_attempt_only")

        st.markdown("**Acts (check all that apply)**")
        rape = st.checkbox("Rape/Penetration", key="act_rape")
        forced_oral = st.checkbox("Forced Oral/Forced Touching", key="act_forced_oral")
        touching = st.checkbox("Touching/Kissing w/o Consent", key="act_touch")
        exposure = st.checkbox("Indecent Exposure", key="act_exposure")
        masturb = st.checkbox("Masturbation Observed", key="act_masturb")
        kidnap = st.checkbox("Kidnapping Off-Route w/ Threats", key="act_kidnap")
        imprison = st.checkbox("False Imprisonment w/ Threats", key="act_imprison")

    # ========= Calculations =========
    used_date = incident_date or TODAY.date()
    incident_dt = datetime.combine(used_date, incident_time)

    act_flags = {
        "Rape/Penetration": 'rape' in locals() and rape,
        "Forced Oral/Forced Touching": 'forced_oral' in locals() and forced_oral,
        "Touching/Kissing w/o Consent": 'touching' in locals() and touching,
        "Indecent Exposure": 'exposure' in locals() and exposure,
        "Masturbation Observed": 'masturb' in locals() and masturb,
        "Kidnapping Off-Route w/ Threats": 'kidnap' in locals() and kidnap,
        "False Imprisonment w/ Threats": 'imprison' in locals() and imprison
    }
    tier_label, aggr_list = tier_and_aggravators(act_flags)
    base_tier_ok = ("Tier 1" in tier_label) or ("Tier 2" in tier_label)

    category = sa_category(act_flags)  # 'penetration' | 'other' | None
    sol_state = STATE_ALIAS.get(state, state)
    sol_years, sol_rule_text, used_sa = sol_rule_for(sol_state, category)

    # Compute SOL end / Wagstaff timing
    if sol_years is None:
        sol_end = None
        wagstaff_deadline = None
        wagstaff_time_ok = True
    else:
        sol_end = incident_dt + relativedelta(years=+int(sol_years))
        wagstaff_deadline = sol_end - timedelta(days=45)
        wagstaff_time_ok = TODAY <= wagstaff_deadline

    # Earliest report <= 14d (for Triten example logic)
    all_dates = [d for d in report_dates.values() if d]
    if family_report_dt: all_dates.append(family_report_dt.date())
    earliest_report_date = min(all_dates) if all_dates else None
    delta_days = (earliest_report_date - incident_dt.date()).days if earliest_report_date else None
    triten_report_ok = (delta_days is not None) and (0 <= delta_days <= 14)

    # Wagstaff disqualifiers
    wag_disq = []
    if felony: wag_disq.append("Felony record → Wagstaff requires no felony history.")
    if ('driver_weapon' in locals()) and driver_weapon == "Yes": wag_disq.append("Weapon involved → disqualified under Wagstaff.")
    if ('client_weapon' in locals()) and client_weapon: wag_disq.append("Victim carrying a weapon → may disqualify.")
    if ('verbal_only' in locals()) and verbal_only: wag_disq.append("Verbal abuse only → does not qualify.")
    if ('attempt_only' in locals()) and attempt_only: wag_disq.append("Attempt/minor contact only → does not qualify.")
    if ('has_atty' in locals()) and has_atty: wag_disq.append("Already has attorney → cannot intake.")

    # Family-only 24h rule
    within_24h_family_ok = True
    if set(reported_to) == {"Friend or Family Member"}:
        if not family_report_dt:
            within_24h_family_ok = False
            wag_disq.append("Family/Friends-only selected but date/time was not provided.")
        else:
            delta = family_report_dt - incident_dt
            within_24h_family_ok = (timedelta(0) <= delta <= timedelta(hours=24))
            if not within_24h_family_ok:
                wag_disq.append("Family/Friends-only report exceeded 24 hours after incident → fails Wagstaff rule.")

    # Core must-haves (some switches may be hidden until expander is opened)
    female_rider_val = 'female_rider' in locals() and female_rider
    gov_id_val = 'gov_id' in locals() and gov_id
    has_atty_val = 'has_atty' in locals() and has_atty
    common_ok = bool(female_rider_val and receipt and gov_id_val and inside_near and (not has_atty_val))

    # === Wagstaff accepts Uber AND Lyft ===
    wag_ok_core = common_ok and wagstaff_time_ok and within_24h_family_ok and base_tier_ok and (not wag_disq)
    wag_ok = wag_ok_core and (company in ("Uber", "Lyft"))

    # Triten example logic
    tri_disq = []
    if ('verbal_only' in locals()) and verbal_only: tri_disq.append("Verbal abuse only → does not qualify.")
    if ('attempt_only' in locals()) and attempt_only: tri_disq.append("Attempt/minor contact only → does not qualify.")
    if earliest_report_date is None: tri_disq.append("No report date provided for any channel.")
    if not triten_report_ok: tri_disq.append("Earliest report not within 2 weeks.")
    if has_atty_val: tri_disq.append("Already has attorney → cannot intake.")
    triten_ok = bool(common_ok and triten_report_ok and base_tier_ok and (not tri_disq))

    # ========= UI: Eligibility badges =========
    st.subheader("Eligibility Snapshot")
    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown(f"<div class='badge-note'>Tier</div>", unsafe_allow_html=True)
        badge(True, tier_label if tier_label!="Unclear" else "Tier unclear")
    with b2:
        st.markdown(f"<div class='badge-note'>Wagstaff</div>", unsafe_allow_html=True)
        badge(wag_ok, "Eligible" if wag_ok else "Not Eligible")
    with b3:
        st.markdown(f"<div class='badge-note'>Triten</div>", unsafe_allow_html=True)
        badge(triten_ok, "Eligible" if triten_ok else "Not Eligible")

    # ========= Diagnostics =========
    st.subheader("Diagnostics")

    # Wagstaff diagnostics
    st.markdown("#### Wagstaff")
    wag_lines = []
    if tier_label == "Unclear":
        wag_lines.append("• Tier unclear (needs Tier 1 or Tier 2 acts).")
    else:
        wag_lines.append(f"• Tier = {tier_label}.")
    if company not in ("Uber", "Lyft"):
        wag_lines.append(f"• Company policy: Wagstaff = Uber & Lyft → selected {company}.")
    if not female_rider_val: wag_lines.append("• Female rider requirement not met.")
    if not receipt: wag_lines.append("• Receipt not provided.")
    if not gov_id_val: wag_lines.append("• ID not provided.")
    if not inside_near: wag_lines.append("• Scope not confirmed as inside/just outside/furtherance from car.")
    if has_atty_val: wag_lines.append("• Already represented by an attorney.")
    wag_lines.extend([f"• {x}" for x in wag_disq])

    if not incident_date:
        wag_lines.append("• Incident date is unknown → SOL timing cannot be verified precisely.")
    if used_sa:
        if sol_years is None:
            wag_lines.append(f"• SOL timing: No SOL per sexual-assault extension — {sol_rule_text} → timing OK.")
        else:
            if TODAY > sol_end:
                wag_lines.append(f"• SOL passed ({sol_rule_text}) — deadline was {fmt_dt(sol_end)}.")
            else:
                wag_lines.append(f"• SOL open until {fmt_dt(sol_end)} ({sol_rule_text}).")
    else:
        if sol_years is None:
            wag_lines.append(f"• SOL timing: No SOL (unexpected for {state}).")
        else:
            if TODAY > (sol_end or TODAY):
                wag_lines.append(f"• SOL passed — general tort rule {sol_years} year(s); deadline was {fmt_dt(sol_end)}.")
            else:
                wag_lines.append(f"• SOL open until {fmt_dt(sol_end)} — general tort rule {sol_years} year(s).")

    if sol_years is None:
        wag_lines.append("• Wagstaff file-by: not applicable (No SOL).")
    else:
        wag_lines.append(f"• Wagstaff file-by (SOL − 45 days): {fmt_dt(wagstaff_deadline)} → {'OK' if wagstaff_time_ok else 'Not OK'}.")

    if set(reported_to) == {"Friend or Family Member"} and family_report_dt:
        delta_hours = (family_report_dt - incident_dt).total_seconds()/3600.0
        wag_lines.append(f"• Family/Friends-only report delta: {delta_hours:.1f} hours → {'OK (≤24h)' if within_24h_family_ok else 'Not OK (>24h)'}.")

    st.markdown("<div class='kv'>" + "\n".join(wag_lines) + "</div>", unsafe_allow_html=True)

    # Triten diagnostics
    st.markdown("#### Triten")
    tri_lines = []
    if tier_label == "Unclear":
        tri_lines.append("• Tier unclear (needs Tier 1 or Tier 2 acts).")
    else:
        tri_lines.append(f"• Tier = {tier_label}.")
    tri_lines.append(f"• Common requirements: female={bool(female_rider_val)}, receipt={bool(receipt)}, id={bool(gov_id_val)}, scope={bool(inside_near)}, has_atty={bool(has_atty_val)}.")
    if earliest_report_date:
        tri_lines.append(f"• Earliest report date = {fmt_date(earliest_report_date)}; incident = {fmt_date(incident_dt.date())}; Δ = {delta_days} day(s) → {'OK (≤14 days)' if triten_report_ok else 'Not OK (>14 days or negative)'}")
    else:
        tri_lines.append("• No earliest report date captured → cannot verify 14-day requirement.")
    tri_lines.extend([f"• {x}" for x in tri_disq])
    st.markdown("<div class='kv'>" + "\n".join(tri_lines) + "</div>", unsafe_allow_html=True)

    # ========= SUMMARY TABLE =========
    st.subheader("Summary")
    sol_end_str = ("No SOL" if sol_years is None else (fmt_dt(sol_end) if sol_end else "—"))
    wag_deadline_str = ("N/A (No SOL)" if sol_years is None else (fmt_dt(wagstaff_deadline) if wagstaff_deadline else "—"))
    report_dates_str = "; ".join([f"{k}: {fmt_date(v)}" for k, v in report_dates.items()]) if report_dates else "—"
    family_dt_str = fmt_dt(family_report_dt) if family_report_dt else "—"

    decision = {
        "Full Name": caller_full_name,
        "Legal Name": caller_legal_name,
        "Consent Recording": consent_recording,
        "Phone": caller_phone,
        "Email": caller_email,
        "Company": company,
        "State": state,
        "Tier": tier_label,
        "SA category for SOL": category or "—",
        "Using SA extension?": "Yes" if (category and sol_state in SA_EXT) else "No (general tort)",
        "SOL rule applied": sol_rule_text,
        "SOL End (est.)": sol_end_str,
        "Wagstaff file-by (SOL-45d)": wag_deadline_str,
        "Reported Dates": report_dates_str,
        "Family/Friends Report (DateTime)": family_dt_str,
        "Wagstaff Eligible?": "Eligible" if wag_ok else "Not Eligible",
        "Triten Eligible?": "Eligible" if triten_ok else "Not Eligible",
    }
    st.dataframe(pd.DataFrame([decision]), use_container_width=True, height=320)

    # ========= DETAILED REPORT =========
    st.subheader("Detailed Report — Elements of Statement of the Case for RIDESHARE")

    earliest_channels = []
    if earliest_report_date:
        for k, v in report_dates.items():
            if v == earliest_report_date:
                earliest_channels.append(k)

    acts_selected = [k for k, v in act_flags.items() if v and k not in ("Kidnapping Off-Route w/ Threats", "False Imprisonment w/ Threats")]
    aggr_selected = [k for k in ("Kidnapping Off-Route w/ Threats","False Imprisonment w/ Threats") if act_flags.get(k)]

    line_items = []
    def add_line(num, text): line_items.append(f"{num}. {text}")

    add_line(1,  f"Caller Full / Legal: {caller_full_name or '—'} / {caller_legal_name or '—'}")
    add_line(2,  f"Platform: {company}")
    add_line(3,  f"Receipt Provided: {'Yes' if receipt else 'No'} | Evidence: {join_list(receipt_evidence)}")
    add_line(4,  f"Incident Date/Time: {(fmt_date(incident_date) if incident_date else 'UNKNOWN')} {incident_time.strftime('%H:%M') if incident_time else ''}")
    add_line(5,  f"Reported to: {join_list(reported_to)} | Dates: {', '.join([f'{k}: {fmt_date(v)}' for k,v in report_dates.items()]) if report_dates else '—'}")
    add_line(6,  f"Where it happened (scope): {scope_choice}")
    add_line(7,  f"Pickup → Drop-off: {pickup or '—'} → {dropoff or '—'} | State: {state}")
    add_line(8,  f"Injuries — Physical: {'Yes' if injury_physical else 'No'}, Emotional: {'Yes' if injury_emotional else 'No'} | Details: {injuries_summary or '—'}")
    add_line(9,  f"Provider: {provider_name or '—'} | Facility: {provider_facility or '—'} | Therapy start: {fmt_date(therapy_start) if therapy_start else '—'}")
    add_line(10, f"Medication: {medication_name or '—'} | Pharmacy: {pharmacy_name or '—'}")
    add_line(11, f"Rideshare submission: {rs_submit_how or '—'} | Company responded: {'Yes' if rs_received_response else 'No'} | Detail: {rs_response_detail or '—'}")
    add_line(12, f"Driver profile (if any): {driver_profile or '—'}")
    add_line(13, f"Phone / Email: {caller_phone or '—'} / {caller_email or '—'}")
    add_line(14, f"Standard screen — Felony: {'Yes' if felony else 'No'}")
    add_line(15, f"Acts selected: {join_list(acts_selected)} | Aggravators: {join_list(aggr_selected)}")
    add_line(16, f"Tier: {tier_label}")
    add_line(17, f"SOL rule applied: {sol_rule_text} | SOL end: {('No SOL' if sol_years is None else fmt_dt(sol_end))}")
    add_line(18, f"Wagstaff file-by (SOL−45d): {('N/A (No SOL)' if sol_years is None else fmt_dt(wagstaff_deadline))}")
    add_line(19, f"Triten 14-day check: {'OK (≤14 days)' if triten_report_ok else ('Not OK' if earliest_report_date else 'Unknown')}")
    add_line(20, f"Company policy note: Wagstaff = Uber & Lyft; Triten = Uber & Lyft")

    uploaded_names = [f.name for f in (proof_uploads or [])]
    add_line(21, f"Proof uploaded now: {', '.join(uploaded_names) if uploaded_names else 'None uploaded'}")
    add_line(22, f"Proof delivery method(s): {join_list(proof_methods)}")
    add_line(23, f"SSN last 4 (optional): {ssn_last4 or '—'}")

    elements = "\n".join(line_items)
    st.markdown(f"<div class='copy'>{elements}</div>", unsafe_allow_html=True)

    # ========= EXPORT =========
    st.subheader("Export")
    export_payload = {
        # Caller
        "FullName": caller_full_name,
        "LegalName": caller_legal_name,
        "ConsentRecording": consent_recording,
        "Phone": caller_phone,
        "Email": caller_email,

        # Ride & Incident
        "Company": company,
        "Pickup": pickup,
        "Dropoff": dropoff,
        "State": state,
        "IncidentDate": fmt_date(incident_date) if incident_date else "UNKNOWN",
        "IncidentTime": incident_time.strftime("%H:%M"),

        # Evidence
        "ReceiptProvided": receipt,
        "ReceiptEvidence": receipt_evidence,
        "ReceiptEvidenceOther": receipt_evidence_other,
        "DriverProfile": driver_profile,

        # Reporting
        "ReportedTo": reported_to,
        "ReportDates": {k: fmt_date(v) for k,v in report_dates.items()},
        "FamilyReportDateTime": (fmt_dt(family_report_dt) if family_report_dt else "—"),

        # Company response
        "SubmittedHow": rs_submit_how,
        "CompanyResponded": rs_received_response,
        "CompanyResponseDetail": rs_response_detail,

        # Injuries / Providers / Meds
        "InjuryPhysical": injury_physical,
        "InjuryEmotional": injury_emotional,
        "InjuriesSummary": injuries_summary,
        "ProviderName": provider_name,
        "ProviderFacility": provider_facility,
        "TherapyStartDate": fmt_date(therapy_start) if therapy_start else "—",
        "Medication": medication_name,
        "Pharmacy": pharmacy_name,

        # Identity
        "SSN_Last4": ssn_last4,

        # Agent Switches
        "FemaleRider": female_rider_val,
        "GovIDProvided": gov_id_val,
        "HasAttorney": has_atty_val,
        "DriverWeapon": (driver_weapon if 'driver_weapon' in locals() else "—"),
        "ClientCarryingWeapon": (client_weapon if 'client_weapon' in locals() else False),
        "VerbalOnly": (verbal_only if 'verbal_only' in locals() else False),
        "AttemptOnly": (attempt_only if 'attempt_only' in locals() else False),

        # Acts
        "Acts_Selected": acts_selected,
        "Aggravators_Selected": aggr_selected,

        # SOL Calculations
        "SA_Category": category or "—",
        "SA_Extension_Used": (sol_state in SA_EXT) and bool(category),
        "SOL_Rule_Text": sol_rule_text,
        "SOL_Years": ("No SOL" if sol_years is None else sol_years),
        "SOL_End": ("No SOL" if sol_years is None else fmt_dt(sol_end)),
        "Wagstaff_FileBy": ("N/A (No SOL)" if sol_years is None else fmt_dt(wagstaff_deadline)),
        "Earliest_Report_Date": (fmt_date(earliest_report_date) if earliest_report_date else "—"),
        "Earliest_Report_DeltaDays": (None if delta_days is None else int(delta_days)),
        "Earliest_Report_Channels": earliest_channels,
        "Triten_14day_OK": triten_report_ok,

        # Eligibility
        "Eligibility_Wagstaff": "Eligible" if wag_ok else "Not Eligible",
        "Eligibility_Triten": "Eligible" if triten_ok else "Not Eligible",

        # Proof
        "Proof_Uploaded_Files": uploaded_names,
        "Proof_Delivery_Methods": proof_methods,

        # Full text report
        "Elements_Report": elements.strip()
    }

    st.download_button(
        "Download CSV (intake + decision + diagnostics + full report)",
        data=pd.DataFrame([export_payload]).to_csv(index=False).encode("utf-8"),
        file_name="intake_decision_with_full_report.csv",
        mime="text/csv"
    )

render()
