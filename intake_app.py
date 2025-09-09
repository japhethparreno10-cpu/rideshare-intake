import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from io import BytesIO

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
.note-muted {border:1px dashed #d1d5db; border-radius:8px; padding:10px 12px; margin:8px 0; background:#f9fafb; color:#374151;}
.script {border-left:4px solid #9ca3af; background:#f3f4f6; color:#111827; padding:12px 14px; border-radius:8px; margin:8px 0 12px 0; font-size:0.97rem;}
.callout {border-left:6px solid #2563eb; background:#eef2ff; color:#1e3a8a; padding:12px 14px; border-radius:12px; margin:8px 0 12px 0;}
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
    # ---------- INTRODUCTION ----------
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
    # Story & First-Level Qualification (Vertical Q1-Q3)
    # =========================
    st.markdown("### 1) Story & First-Level Qualification")

    # Q1
    st.markdown("**Q1. In your own words, please feel free to describe what happened during the ride.**")
    narr = st.text_area("Caller narrative", key="q1_narr")

    # Rapport after Q1 (enhanced)
    if narr.strip():
        script_block(
            "“Thank you for sharing that. What you’ve described is extremely difficult, and your feelings are valid. "
            "You’re not alone here. I’m here to listen, to move at your pace, and to protect your story. "
            "If anything is hard to say, take your time—we can pause whenever you need.”"
        )

    # Q2
    st.markdown("**Q2. Which rideshare platform was it?**")
    company = st.selectbox("Select platform", ["Uber", "Lyft", "Other"], key="q2_company")
    if company:
        script_block(f"“Thanks for confirming it was {company}. That helps us pull the right records and policies.”")

    # EXTENSION just below Q2 — Pickup / Drop-off
    st.markdown("**Pickup / Drop-off (extension to Q2)**")
    pickup = st.text_input("Pickup location (address/description)", key="pickup")
    dropoff = st.text_input("Drop-off location (address/description)", key="dropoff")

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
    if receipt_evidence:
        script_block(
            f"“Appreciate you gathering those: {', '.join(receipt_evidence)}. "
            "Receipts and screenshots are powerful evidence linking the ride to your account.”"
        )

    if not receipt:
        st.markdown(
            "<div class='callout'><b>Text to send:</b><br>"
            "<span class='copy'>Forward your receipt to <b>jay@advocaterightscenter.com</b> by selecting the ride in Ride History and choosing “Resend Receipt.”"
            "<br>(Msg Rates Apply. Txt STOP to cancel/HELP for help)</span></div>",
            unsafe_allow_html=True
        )

    # ---- EDUCATION #1 ----
    script_block(
        "HOW THIS HAPPENED →  EDUCATE CLIENT / SAFETY ZONE\n"
        "Well, let me tell you what people have uncovered about Rideshares and why people like you are coming forward. "
        "And again, I appreciate you trusting us with this.\n\n"
        "Uber & Lyft have been exposed for improperly screening drivers, failing to remove dangerous drivers, and misrepresenting its safety practices.\n\n"
        "For example, the New York Times uncovered sealed court documents showing that over 400,000 incidents of sexual assault and misconduct were reported to Uber between 2017 and 2022 . . . which is about 1 incident every 8 minutes.\n\n"
        "[[ Now when you consider that Uber originally only reported about 12,500 incidents during that same period, you can argue the company has been seriously misleading the level of safety it offers passengers. ]]\n\n"
        "Now, we know many people don’t report these incidents. So, coming forward helps you and others obtain justice and compensation. "
        "[[ And, it truly does help force Uber & Lyft to pay for their negligence, and provide real safety measures so these incidents stop happening.]]"
    )

    st.markdown("---")

    # =========================
    # Second-Level Qualification (Q4-Q6)
    # =========================
    st.markdown("### 3) Second-Level Qualification (Reporting & Location)")

    # Q4
    st.markdown("**Q4. Do you remember the date this happened?**")
    has_incident_date = st.toggle("Caller confirms they know the date", value=False, key="q4_hasdate")
    incident_date = st.date_input("Select Incident Date", value=TODAY.date(), key="q4_date") if has_incident_date else None
    incident_time = st.time_input("Incident Time (for timing rules)", value=time(21, 0), key="time_for_calc")
    if has_incident_date and incident_date:
        script_block("“Thanks — the specific date lets the attorneys verify deadlines and request the correct records.”")

    # Q5
    st.markdown("**Q5. Did you report the incident to anyone?** (Uber/Lyft, Police, Physician, Therapist, Family/Friend)")
    reported_to = st.multiselect(
        "Select all that apply",
        ["Rideshare Company","Physician","Friend or Family Member","Therapist","Police Department","NO (DQ, UNLESS TIER 1 OR MINOR)"],
        key="q5_reported"
    )
    if reported_to:
        script_block(f"“Thank you — noting {', '.join(reported_to)} helps build a reliable timeline for the case.”")

    # Per-channel details containers
    report_dates = {}
    family_report_dt = None

    # Friend / Family details
    fam_first = fam_last = fam_phone = ""
    if "Friend or Family Member" in reported_to:
        st.markdown("**Family/Friend Contact Details**")
        fam_first = st.text_input("First name (Family/Friend)", key="fam_first")
        fam_last  = st.text_input("Last name (Family/Friend)", key="fam_last")
        fam_phone = st.text_input("Phone number (Family/Friend)", key="fam_phone")
        ff_date = st.date_input("Date informed Family/Friend", value=TODAY.date(), key="q5a_dt_ff")
        ff_time = st.time_input("Time informed Family/Friend", value=time(21,0), key="q5a_tm_ff")
        report_dates["Family/Friends"] = ff_date
        family_report_dt = datetime.combine(ff_date, ff_time)

    # Physician details
    phys_name = phys_fac = phys_addr = ""
    if "Physician" in reported_to:
        st.markdown("**Physician Details**")
        phys_name = st.text_input("Physician Name", key="phys_name")
        phys_fac  = st.text_input("Clinic/Hospital Name", key="phys_fac")
        phys_addr = st.text_input("Clinic/Hospital Address", key="phys_addr")
        report_dates["Physician"] = st.date_input("Date reported to Physician", value=TODAY.date(), key="q5a_dt_phys")

    # Therapist details
    ther_name = ther_fac = ther_addr = ""
    if "Therapist" in reported_to:
        st.markdown("**Therapist Details**")
        ther_name = st.text_input("Therapist Name", key="ther_name")
        ther_fac  = st.text_input("Clinic/Hospital Name", key="ther_fac")
        ther_addr = st.text_input("Clinic/Hospital Address", key="ther_addr")
        report_dates["Therapist"] = st.date_input("Date reported to Therapist", value=TODAY.date(), key="q5a_dt_ther")

    # Police details
    police_station = police_addr = ""
    if "Police Department" in reported_to:
        st.markdown("**Police Details**")
        police_station = st.text_input("Name of Police Station", key="police_station")
        police_addr    = st.text_input("Police Station Address", key="police_addr")
        report_dates["Police"] = st.date_input("Date reported to Police", value=TODAY.date(), key="q5a_dt_police")

    # Rideshare Company details (reported channel)
    rep_rs_company = ""
    if "Rideshare Company" in reported_to:
        st.markdown("**Rideshare Company (reported)**")
        rep_rs_company = st.selectbox("Which company did you report to?", ["Uber", "Lyft"], key="rep_rs_company")
        report_dates["Rideshare company"] = st.date_input("Date reported to Rideshare company", value=TODAY.date(), key="q5a_dt_rs")

    # Q6
    st.markdown("**Q6. Did the incident happen inside the car, just outside, or did it continue after you exited?**")
    scope_choice = st.selectbox(
        "Select scope",
        ["Inside the car", "Just outside the car", "Furtherance from the car", "Unclear"],
        key="scope_choice"
    )
    inside_near = scope_choice in ["Inside the car", "Just outside the car", "Furtherance from the car"]
    if scope_choice and scope_choice != "Unclear":
        script_block(f"“Got it — {scope_choice.lower()}. That helps confirm it occurred within the rideshare’s safety responsibility.”")

    # ---- EDUCATION #2 ----
    script_block(
        "Education Insert #2 — “Safe Rides Fee”\n"
        "Jay: “____, what’s especially troubling is that Uber and Lyft have had knowledge of these dangers since at least 2014. \n"
        "That year, Uber introduced a $1 ‘Safe Rides Fee’ — claiming it funded driver checks and safety upgrades. "
        "But investigations found that most of the $500 million collected went to profit, not safety.\n"
        "They later just renamed it a ‘booking fee.’ Survivors were paying for safety that never arrived.”"
    )

    st.markdown("---")

    # =========================
    # Injury & Case-Support (Q7-Q9)
    # =========================
    st.markdown("### 5) Injury & Case-Support Questions")

    # Q7
    st.markdown("**Q7. Were you injured physically, or have you experienced emotional effects afterward?**")
    injury_physical = st.checkbox("Physical injury", key="inj_physical")
    injury_emotional = st.checkbox("Emotional effects (anxiety, nightmares, etc.)", key="inj_emotional")
    injuries_summary = st.text_area("If comfortable, briefly describe injuries/effects", key="injuries_summary")
    if injury_physical or injury_emotional or injuries_summary.strip():
        script_block("“I’m sorry you’re dealing with these effects. Your health matters, and we’ll reflect this in the case.”")

    # Q8
    st.markdown("**Q8. Have you spoken to a doctor, therapist, or counselor?**")
    provider_name = st.text_input("Provider name (optional)", key="provider_name")
    provider_facility = st.text_input("Facility/Clinic (optional)", key="provider_facility")
    therapy_start = st.date_input("Therapy start date (if any)", value=TODAY.date(), key="therapy_start") if st.toggle("Add therapy start date", key="therapy_toggle", value=False) else None
    if provider_name.strip() or provider_facility.strip() or therapy_start:
        script_block("“Thank you — treatment notes are strong, objective support for your experience.”")

    # Q9
    st.markdown("**Q9. Do you take any medications related to this?**")
    medication_name = st.text_input("Medication (optional)", key="medication_name")
    pharmacy_name = st.text_input("Pharmacy (optional)", key="pharmacy_name")
    if medication_name.strip() or pharmacy_name.strip():
        script_block("“Understood. Pharmacy records help connect treatment to what you went through.”")

    # ---- EDUCATION #3 ----
    script_block(
        "Education Insert #3 — Law Firm & Contingency\n"
        "Jay: “____, based on what you’ve told me, you Might have a valid case. Here’s how pursuing a settlement works: \n"
        "You hire the law firm on a contingency basis — no upfront costs, no out-of-pocket fees. You only owe if they win you a recovery.\n"
        "We are the intake center for The Wagstaff Law Firm. Their attorneys are nationally recognized — many named Super Lawyers (top 5% of all attorneys). "
        "Judges across the country have appointed them to nine national Plaintiff Steering Committees, reserved for the top trial lawyers in corporate negligence cases.\n"
        "They’re now applying that same leadership to hold Uber and Lyft accountable for failing survivors like you.”"
    )

    st.markdown("---")

    # =========================
    # Contact & Incident State
    # =========================
    st.markdown("### Contact & Incident State")
    caller_phone = st.text_input("Best phone number", key="caller_phone")
    caller_email = st.text_input("Best email", key="caller_email")
    state = st.selectbox("Incident state", STATES, index=(STATES.index("California") if "California" in STATES else 0), key="q_state")

    st.markdown("**Rideshare submission & response (if any)**")
    rs_submit_how = st.text_input("How did you submit to Uber/Lyft? (email/app/other)", key="q8_submit_how")
    rs_received_response = st.toggle("Company responded", value=False, key="q9_resp_toggle")
    rs_response_detail = st.text_input("If yes, what did they say? (optional)", key="q9_resp_detail")

    # =========================
    # Standard Screening (verbatim)
    # =========================
    st.markdown("**Standard Screening**")
    script_block("This will not affect your case, So the law firm can be prepared for any character issues, do you have any felonies or criminal history?")
    felony_answer = st.radio("Please select one", ["No", "Yes"], horizontal=True, key="q10_felony")
    felony = (felony_answer == "Yes")

    # =========================
    # Settlement Process & Proof
    # =========================
    st.markdown("### Settlement Process & Request for Proof")

    script_block(
        "Here’s what to expect: after discovery, the court schedules four bellwether test trials — real trials that guide settlement ranges for everyone else.\n"
        "That means you won’t have to retell your story in court. Your records and documents will speak for you, and your settlement will be based on your individual experience."
    )

    proof_methods = st.multiselect(
        "How would you like to send documentation (receipts/screenshots/ID/therapy notes/prescriptions)? (Skip if already given)",
        ["Secure camera link (we text you a link)", "Email to jay@advocaterightscenter.com", "FedEx/UPS scan/fax from store"],
        key="proof_methods"
    )
    if proof_methods:
        script_block("“Perfect — we’ll make it easy and secure to share those documents.”")

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

    # ---- EDUCATION #4 ----
    script_block(
        "Jay: “____, once the bellwether trials conclude, those results usually spark settlement negotiations. "
        "That’s when distributions begin — survivors don’t have to wait for every trial to finish. "
        "The test results give both sides the framework to resolve cases sooner.”"
    )

    # =========================
    # Identity for Records (Optional)
    # =========================
    st.markdown("### Identity for Records (Optional)")
    script_block(
        "One final step: some providers require identity verification before releasing medical records. "
        "For that, the firm usually asks for a Social Security number. If you’d prefer, you can share just the **last 4 digits**; "
        "those are often enough for HIPAA releases."
    )
    ssn_last4 = st.text_input("SSN last 4 (optional)", max_chars=4, key="ssn_last4")
    full_ssn_on_file = st.checkbox("Full SSN on file", value=False, key="full_ssn_on_file")

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

    # SA category & SOL rule
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

    # Triten earliest report <= 14d
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

    # Core must-haves
    female_rider_val = 'female_rider' in locals() and female_rider
    gov_id_val = 'gov_id' in locals() and gov_id
    has_atty_val = 'has_atty' in locals() and has_atty
    common_ok = bool(female_rider_val and receipt and gov_id_val and inside_near and (not has_atty_val))

    # Wagstaff accepts Uber & Lyft
    wag_ok_core = common_ok and wagstaff_time_ok and within_24h_family_ok and base_tier_ok and (not wag_disq)
    wag_ok = wag_ok_core and (company in ("Uber", "Lyft"))

    # Triten logic
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
        st.markdown("<div class='badge-note'>Tier</div>", unsafe_allow_html=True)
        badge(True, tier_label if tier_label != "Unclear" else "Tier unclear")
    with b2:
        st.markdown("<div class='badge-note'>Wagstaff</div>", unsafe_allow_html=True)
        badge(wag_ok, "Eligible" if wag_ok else "Not Eligible")
    with b3:
        st.markdown("<div class='badge-note'>Triten</div>", unsafe_allow_html=True)
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
        wag_lines.append(
            f"• Wagstaff file-by (SOL − 45 days): {fmt_dt(wagstaff_deadline)} → "
            f"{'OK' if wagstaff_time_ok else 'Not OK'}"
        )

    if set(reported_to) == {"Friend or Family Member"} and family_report_dt:
        delta_hours = (family_report_dt - incident_dt).total_seconds() / 3600.0
        wag_lines.append(
            f"• Family/Friends-only report delta: {delta_hours:.1f} hours → "
            f"{'OK (≤24h)' if within_24h_family_ok else 'Not OK (>24h)'}"
        )

    st.markdown("<div class='kv'>" + "\n".join(wag_lines) + "</div>", unsafe_allow_html=True)

    # Triten diagnostics
    st.markdown("#### Triten")
    tri_lines = []
    if tier_label == "Unclear":
        tri_lines.append("• Tier unclear (needs Tier 1 or Tier 2 acts).")
    else:
        tri_lines.append(f"• Tier = {tier_label}.")
    tri_lines.append(
        f"• Common requirements: female={bool(female_rider_val)}, receipt={bool(receipt)}, "
        f"id={bool(gov_id_val)}, scope={bool(inside_near)}, has_atty={bool(has_atty_val)}."
    )
    if earliest_report_date:
        tri_lines.append(
            f"• Earliest report date = {fmt_date(earliest_report_date)}; "
            f"incident = {fmt_date(incident_dt.date())}; Δ = {delta_days} day(s) → "
            f"{'OK (≤14 days)' if triten_report_ok else 'Not OK (>14 days or negative)'}"
        )
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
    # Reported to + per-channel details
    add_line(5,  f"Reported to: {join_list(reported_to)} | Dates: {', '.join([f'{k}: {fmt_date(v)}' for k,v in report_dates.items()]) if report_dates else '—'}")
    if "Friend or Family Member" in reported_to:
        add_line(5.1, f"Family/Friend Contact: {fam_first or '—'} {fam_last or ''} | Phone: {fam_phone or '—'}")
    if "Physician" in reported_to:
        add_line(5.2, f"Physician: {phys_name or '—'} | Clinic/Hospital: {phys_fac or '—'} | Address: {phys_addr or '—'}")
    if "Therapist" in reported_to:
        add_line(5.3, f"Therapist: {ther_name or '—'} | Clinic/Hospital: {ther_fac or '—'} | Address: {ther_addr or '—'}")
    if "Police Department" in reported_to:
        add_line(5.4, f"Police Station: {police_station or '—'} | Address: {police_addr or '—'}")
    if "Rideshare Company" in reported_to:
        add_line(5.5, f"Rideshare Company (reported): {rep_rs_company or '—'}")

    add_line(6,  f"Where it happened (scope): {scope_choice}")
    add_line(7,  f"Pickup → Drop-off: {pickup or '—'} → {dropoff or '—'} | State: {state}")
    add_line(8,  f"Injuries — Physical: {'Yes' if injury_physical else 'No'}, Emotional: {'Yes' if injury_emotional else 'No'} | Details: {injuries_summary or '—'}")
    add_line(9,  f"Provider: {provider_name or '—'} | Facility: {provider_facility or '—'} | Therapy start: {fmt_date(therapy_start) if therapy_start else '—'}")
    add_line(10, f"Medication: {medication_name or '—'} | Pharmacy: {pharmacy_name or '—'}")
    add_line(11, f"Rideshare submission: {rs_submit_how or '—'} | Company responded: {'Yes' if rs_received_response else 'No'} | Detail: {rs_response_detail or '—'}")
    add_line(12, f"Phone / Email: {caller_phone or '—'} / {caller_email or '—'}")
    add_line(13, f"Standard screen — Felony/Criminal history: {'Yes' if felony else 'No'}")
    add_line(14, f"Acts selected: {join_list(acts_selected)} | Aggravators: {join_list(aggr_selected)}")
    add_line(15, f"Tier: {tier_label}")
    add_line(16, f"SOL rule applied: {sol_rule_text} | SOL end: {('No SOL' if sol_years is None else fmt_dt(sol_end))}")
    add_line(17, f"Wagstaff file-by (SOL−45d): {('N/A (No SOL)' if sol_years is None else fmt_dt(wagstaff_deadline))}")
    add_line(18, f"Triten 14-day check: {'OK (≤14 days)' if triten_report_ok else ('Not OK' if earliest_report_date else 'Unknown')}")
   
