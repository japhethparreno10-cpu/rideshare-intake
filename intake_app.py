import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from io import BytesIO
import os

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
# EXCEL ENGINE DETECTION (safe fallback)
# =========================
try:
    import xlsxwriter as _tmp_xlsxwriter  # noqa: F401
    XLSX_ENGINE = "xlsxwriter"
except Exception:
    try:
        import openpyxl as _tmp_openpyxl  # noqa: F401
        XLSX_ENGINE = "openpyxl"
    except Exception:
        XLSX_ENGINE = None

# =========================
# BASE SOL TABLE (General tort SOL per your list)
# =========================
TORT_SOL = {
    # 1 year
    "Kentucky": 1, "Louisiana": 1, "Tennessee": 1,

    # 2 years
    "Alabama": 2, "Alaska": 2, "Arizona": 2, "California": 2, "Colorado": 2, "Connecticut": 2, "Delaware": 2,
    "Georgia": 2, "Hawaii": 2, "Idaho": 2, "Illinois": 2, "Indiana": 2, "Iowa": 2, "Kansas": 2, "Minnesota": 2,
    "Nevada": 2, "New Jersey": 2, "Ohio": 2, "Oklahoma": 2, "Oregon": 2, "Pennsylvania": 2, "Texas": 2,
    "Virginia": 2, "West Virginia": 2,

    # 3 years
    "Arkansas": 3, "D.C.": 3, "Maryland": 3, "Massachusetts": 3, "Michigan": 3, "Mississippi": 3, "Montana": 3,
    "New Hampshire": 3, "New Mexico": 3, "New York": 3, "North Carolina": 3, "Rhode Island": 3, "South Carolina": 3,
    "South Dakota": 3, "Vermont": 3, "Washington": 3, "Wisconsin": 3,

    # 4 years
    "Florida": 4, "Nebraska": 4, "Utah": 4, "Wyoming": 4,

    # 5 years
    "Missouri": 5,

    # 6 years
    "Maine": 6, "North Dakota": 6,
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
    if not text: 
        return
    st.markdown(f"<div class='script'>{text}</div>", unsafe_allow_html=True)

def badge(ok: bool, label: str):
    css = "badge-ok" if ok else "badge-no"
    st.markdown(f"<div class='{css}'>{label}</div>", unsafe_allow_html=True)

def fmt_date(dt): 
    return dt.strftime("%Y-%m-%d") if dt else "—"

def fmt_dt(dt): 
    return dt.strftime("%Y-%m-%d %H:%M") if dt else "—"

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
    if aggr_kidnap: 
        aggr.append("Kidnapping w/ threats")
    if aggr_imprison: 
        aggr.append("False imprisonment w/ threats")
    if t1: 
        base = "Tier 1"
    elif t2: 
        base = "Tier 2"
    else: 
        base = "Unclear"
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
    if flags.get("Rape/Penetration"): 
        buckets.append("rape/penetration")
    if flags.get("Forced Oral/Forced Touching"): 
        buckets.append("forced oral/forced touching")
    if flags.get("Touching/Kissing w/o Consent"): 
        buckets.append("unwanted touching/kissing")
    if flags.get("Indecent Exposure"): 
        buckets.append("indecent exposure")
    if flags.get("Masturbation Observed"): 
        buckets.append("masturbation observed")
    if flags.get("Kidnapping Off-Route w/ Threats"): 
        buckets.append("kidnapping off-route w/ threats")
    if flags.get("False Imprisonment w/ Threats"): 
        buckets.append("false imprisonment w/ threats")
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
    # Story & First-Level Qualification
    # =========================
    st.markdown("### 1) Story & First-Level Qualification")

    # Q1
    st.markdown("**Q1. In your own words, please feel free to describe what happened during the ride.**")
    narr = st.text_area("Caller narrative", key="q1_narr")
    if narr.strip():
        script_block(
            "“Thank you for trusting me with that. What you’ve shared is painful and important. "
            "You’re in control of this conversation, and we’ll move at your pace. "
            "If anything feels hard to say, we can take a moment and continue when you’re ready.”"
        )

    # Q2
    st.markdown("**Q2. Which rideshare platform was it?**")
    company = st.selectbox("Select platform", ["Uber", "Lyft", "Other"], key="q2_company")
    if company:
        script_block(f"“Thanks for confirming it was {company}. That helps us pull the right records and policies.”")

    # EXTENSION just below Q2 — Pickup / Drop-off
    st.markdown("**Pickup / Drop-off (extension to Q2)**")
    st.caption("Let’s anchor the timeline and route.")
    pickup = st.text_input("Pickup location (address/description)", key="pickup")
    dropoff = st.text_input("Drop-off location (address/description)", key="dropoff")
    if pickup.strip() or dropoff.strip():
        script_block(
            "“That’s helpful — pickup and drop-off lock in the route and jurisdiction. "
            "If you remember landmarks or cross-streets, we can add those too. You’re doing great.”"
        )

    # Q3
    st.markdown("**Q3. Do you have a receipt for the ride (in-app or email)?**")
    receipt = st.toggle("Receipt provided (email/app/PDF)", value=False, key="q3_receipt_toggle")

    # Receipt evidence (engaging + conversational)
    st.markdown("**What can you provide as receipt evidence?**")
    st.caption("Whatever is easiest for you is fine — we can work with any of these.")
    receipt_evidence = st.multiselect(
        "Select all that apply",
        ["PDF", "Email", "Screenshot of Receipt", "In-App Receipt (screenshot)", "Other"],
        key="receipt_evidence"
    )
    receipt_evidence_other = st.text_input("If Other, describe", key="receipt_evidence_other")
    if receipt_evidence_other and "Other" not in receipt_evidence:
        receipt_evidence.append(f"Other: {receipt_evidence_other.strip()}")

    if receipt or receipt_evidence:
        script_block(
            "“Perfect — receipts and screenshots directly link the ride to your account and timestamp the trip. "
            "Thanks for pulling those together.”"
        )
    else:
        st.markdown(
            "<div class='callout'><b>Text to send:</b><br>"
            "<span class='copy'>Forward your receipt to <b>jay@advocaterightscenter.com</b> by selecting the ride in Ride History and choosing “Resend Receipt.”"
            "<br>(Msg Rates Apply. Txt STOP to cancel/HELP for help)</span></div>",
            unsafe_allow_html=True
        )

    # Documentation options + uploader WITH Q3 (as requested)
    st.markdown("**How would you like to send documentation (receipts/screenshots/ID/therapy notes/prescriptions)? (Skip if already given)**")
    proof_methods = st.multiselect(
        "Choose options",
        ["Secure camera link (we text you a link)", "Email to jay@advocaterightscenter.com", "FedEx/UPS scan/fax from store"],
        key="proof_methods"
    )
    if proof_methods:
        script_block("“Great — we’ll keep it simple and secure to share your documents.”")

    if "Email to jay@advocaterightscenter.com" in proof_methods:
        st.markdown(
            "<div class='callout'><b>Email Instructions</b><br>"
            "<span class='copy'>Send photos/PDFs to <b>jay@advocaterightscenter.com</b>. "
            "In the rideshare app: Ride History → select ride → “Resend Receipt.”</span></div>",
            unsafe_allow_html=True
        )
    if "Secure camera link (we text you a link)" in proof_methods:
        st.markdown("<div class='note-muted'>We’ll text a one-time secure link that opens your phone’s camera to capture documents.</div>", unsafe_allow_html=True)
        st.button("Send secure upload link (placeholder)")
    if "FedEx/UPS scan/fax from store" in proof_methods:
        st.markdown("<div class='note-muted'>Ask staff to scan/fax to <b>jay@advocaterightscenter.com</b>. Keep the receipt for your records.</div>", unsafe_allow_html=True)

    proof_uploads = st.file_uploader(
        "Upload proof now (ride receipt, therapy/medical note, police confirmation, audio/video) — images, PDFs, audio, or video",
        type=["pdf", "png", "jpg", "jpeg", "heic", "mp4", "mov", "m4a", "mp3", "wav"],
        accept_multiple_files=True,
        key="proof_uploads"
    )
    uploaded_files = proof_uploads or []
    uploaded_names = [f.name for f in uploaded_files]
    any_pdf_uploaded = any(n.lower().endswith(".pdf") for n in uploaded_names)
    any_av_uploaded = any(n.lower().endswith(ext) for n in uploaded_names for ext in (".mp4",".mov",".m4a",".mp3",".wav"))
    if uploaded_names:
        script_block("“Thanks for those uploads — I see them here and will attach them to your file.”")

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
    # Second-Level Qualification (Reporting & Location)
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
    st.caption("Choose everything that applies — even telling a trusted person helps build the timeline.")
    reported_to = st.multiselect(
        "Select all that apply",
        ["Rideshare Company","Physician","Friend or Family Member","Therapist","Police Department","NO (DQ, UNLESS TIER 1 OR MINOR)"],
        key="q5_reported"
    )
    if reported_to:
        script_block(f"“Thank you — noting {', '.join(reported_to)} helps us build a reliable timeline for your case.”")

    # Per-channel details
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
        "Jay: “____, what’s especially troubling is that Uber and Lyft have had knowledge of these dangers since at least 2014.\n"
        "That year, Uber introduced a $1 ‘Safe Rides Fee’ — claiming it funded driver checks and safety upgrades. "
        "But investigations found that most of the $500 million collected went to profit, not safety.\n"
        "They later just renamed it a ‘booking fee.’ Survivors were paying for safety that never arrived.”"
    )

    st.markdown("---")

    # =========================
    # Acts for Tiering (VISIBLE)
    # =========================
    st.subheader("Acts (check all that apply)")
    rape = st.checkbox("Rape/Penetration", key="act_rape")
    forced_oral = st.checkbox("Forced Oral/Forced Touching", key="act_forced_oral")
    touching = st.checkbox("Touching/Kissing w/o Consent", key="act_touch")
    exposure = st.checkbox("Indecent Exposure", key="act_exposure")
    masturb = st.checkbox("Masturbation Observed", key="act_masturb")
    kidnap = st.checkbox("Kidnapping Off-Route w/ Threats (Tier-3 aggravator; must have Tier 1 or 2)", key="act_kidnap")
    imprison = st.checkbox("False Imprisonment w/ Threats (Tier-3 aggravator; must have Tier 1 or 2)", key="act_imprison")

    act_flags = {
        "Rape/Penetration": rape,
        "Forced Oral/Forced Touching": forced_oral,
        "Touching/Kissing w/o Consent": touching,
        "Indecent Exposure": exposure,
        "Masturbation Observed": masturb,
        "Kidnapping Off-Route w/ Threats": kidnap,
        "False Imprisonment w/ Threats": imprison
    }
    tier_label, aggr_list = tier_and_aggravators(act_flags)
    base_tier_ok = ("Tier 1" in tier_label) or ("Tier 2" in tier_label)

    # =========================
    # Injury & Case-Support
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
    therapy_toggle = st.toggle("Add therapy start date", key="therapy_toggle", value=False)
    therapy_start = st.date_input("Therapy start date (if any)", value=TODAY.date(), key="therapy_start") if therapy_toggle else None
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
        "Jay: “____, based on what you’ve told me, you Might have a valid case. Here’s how pursuing a settlement works:\n"
        "You hire the law firm on a contingency basis — no upfront costs, no out-of-pocket fees. You only owe if they win you a recovery.\n"
        "We are the intake center for The Wagstaff Law Firm. Their attorneys are nationally recognized — many named Super Lawyers (top 5% of all attorneys). "
        "Judges across the country have appointed them to nine national Plaintiff Steering Committees, reserved for the top trial lawyers in corporate negligence cases.\n"
        "They’re now applying that same leadership to hold Uber and Lyft accountable for failing survivors like you.”"
    )

    st.markdown("---")

    # =========================
    # Contact & Incident State + Screening
    # =========================
    st.markdown("### Contact & Screening")
    caller_phone = st.text_input("Best phone number", key="caller_phone")
    caller_email = st.text_input("Best email", key="caller_email")
    state = st.selectbox("Incident state", STATES, index=(STATES.index("California") if "California" in STATES else 0), key="q_state")

    st.markdown("**Rideshare submission & response (if any)**")
    rs_submit_how = st.text_input("How did you submit to Uber/Lyft? (email/app/other)", key="q8_submit_how")
    rs_received_response = st.toggle("Company responded", value=False, key="q9_resp_toggle")
    rs_response_detail = st.text_input("If yes, what did they say? (optional)", key="q9_resp_detail")

    st.markdown("**Standard Screening**")
    gov_id = st.toggle("Government ID provided", value=False, key="elig_id")
    female_rider = st.toggle("Female rider", value=False, key="elig_female")
    rider_not_driver = st.toggle("Caller was the rider (not the driver)", value=True, key="elig_rider_not_driver")
    has_atty = st.toggle("Already has an attorney", value=False, key="elig_atty")
    script_block("This will not affect your case, So the law firm can be prepared for any character issues, do you have any felonies or criminal history?")
    felony_answer = st.radio("Please select one", ["No", "Yes"], horizontal=True, key="q10_felony")
    felony = (felony_answer == "Yes")

    st.markdown("---")

    # =========================
    # Settlement Process + Education #4
    # =========================
    st.markdown("### Settlement Process")
    script_block(
        "Here’s what to expect: after discovery, the court schedules four bellwether test trials — real trials that guide settlement ranges for everyone else.\n"
        "That means you won’t have to retell your story in court. Your records and documents will speak for you, and your settlement will be based on your individual experience."
    )
    script_block(
        "Education Insert #4 — Timeline for Settlement Distribution\n"
        "Jay: “____, once the bellwether trials conclude, those results usually spark settlement negotiations. "
        "That’s when distributions begin — survivors don’t have to wait for every trial to finish. "
        "The test results give both sides the framework to resolve cases sooner.”"
    )

    # =========================
    # Identity for Records (Optional)
    # =========================
    st.markdown("### Identity for Records (Optional)")
    script_block(
        "Some providers require identity verification before releasing medical records. "
        "If you prefer, you can share just the **last 4 digits**; those are often enough for HIPAA releases."
    )
    ssn_last4 = st.text_input("SSN last 4 (optional)", max_chars=4, key="ssn_last4")
    full_ssn_on_file = st.checkbox("Full SSN on file", value=False, key="full_ssn_on_file")

    # ========= Derived/Calculations =========
    used_date = incident_date or TODAY.date()
    incident_dt = datetime.combine(used_date, incident_time)

    # SA category & SOL rule
    category = sa_category(act_flags)  # 'penetration' | 'other' | None
    sol_state = STATE_ALIAS.get(state, state)
    sol_years, sol_rule_text, used_sa = sol_rule_for(sol_state, category)

    # Compute SOL end / timing OK
    if sol_years is None:
        sol_end = None
        file_by_deadline = None
        sol_time_ok = True
    else:
        sol_end = incident_dt + relativedelta(years=+int(sol_years))
        file_by_deadline = sol_end - timedelta(days=45)
        sol_time_ok = TODAY <= sol_end

    # Reporting timing
    all_dates = [d for d in report_dates.values() if d]
    if family_report_dt:
        all_dates.append(family_report_dt.date())
    earliest_report_date = min(all_dates) if all_dates else None
    delta_days = (earliest_report_date - incident_dt.date()).days if earliest_report_date else None

    # Which channel produced earliest report?
    earliest_channels = []
    if earliest_report_date:
        for k, v in report_dates.items():
            if v == earliest_report_date:
                earliest_channels.append(k)
    earliest_is_family = (earliest_channels == ["Family/Friends"]) or (set(earliest_channels) == {"Family/Friends"})

    # ===== Eligibility Rules =====
    # Common disqualifiers
    verbal_only = False  # explicit toggles no longer separate; infer from acts: no Tier1/2 acts -> not eligible
    attempt_only = False  # not separately collected; if no Tier 1/2, it's effectively "not enough"

    # WAGSTAFF
    # Must be reported to allowed channel OR audio/video evidence
    wag_allowed_channels = {"Rideshare company", "Police", "Therapist", "Physician", "Family/Friends"}
    has_allowed_report = any(ch in report_dates for ch in ["Rideshare company","Police","Therapist","Physician"]) \
                         or ("Family/Friends" in report_dates)
    # Family-only must be within 24h (if it's the only report)
    within_24h_family_ok = True
    if set(report_dates.keys()) == {"Family/Friends"}:
        if not family_report_dt:
            within_24h_family_ok = False
        else:
            delta_hours = (family_report_dt - incident_dt).total_seconds() / 3600.0
            within_24h_family_ok = (0 <= delta_hours <= 24.0)

    wag_report_ok = (has_allowed_report and (within_24h_family_ok or not set(report_dates.keys()) == {"Family/Friends"})) or any_av_uploaded

    wag_common_ok = (not has_atty) and inside_near and base_tier_ok and sol_time_ok and (company in ("Uber","Lyft"))
    wag_no_felony = not felony  # Wagstaff disqualifies felony
    wag_ok = wag_common_ok and wag_report_ok and wag_no_felony

    # TRITEN
    # 1) Email or PDF receipt
    triten_receipt_ok = ("Email" in receipt_evidence) or ("PDF" in receipt_evidence) or any_pdf_uploaded
    # 2) Must provide ID
    triten_id_ok = bool(gov_id)
    # 3) Female riders only, no drivers
    triten_gender_ok = bool(female_rider)
    triten_role_ok = bool(rider_not_driver)
    # 4) Reported; if earliest is Family/Friends, must be within 14 days
    triten_report_any = bool(report_dates) or bool(family_report_dt)
    triten_family_14_ok = True
    if triten_report_any and earliest_is_family:
        triten_family_14_ok = (delta_days is not None) and (0 <= delta_days <= 14)
    # 5) Accept felony records (so felony is allowed)
    # 6) No atty
    triten_no_atty = not has_atty
    # 7) Decline if just verbal/attempt — operationalized as: must have Tier 1 or Tier 2 acts (base_tier_ok)
    triten_tier_ok = base_tier_ok
    # Scope and SOL
    triten_scope_ok = inside_near
    triten_sol_ok = sol_time_ok
    triten_company_ok = (company in ("Uber","Lyft"))

    triten_ok = all([
        triten_receipt_ok, triten_id_ok, triten_gender_ok, triten_role_ok,
        triten_report_any, triten_family_14_ok, triten_no_atty, triten_tier_ok,
        triten_scope_ok, triten_sol_ok, triten_company_ok
    ])

    # =========================
    # Eligibility Snapshot (badges)
    # =========================
    st.subheader("Eligibility Snapshot")
    colA, colB, colC = st.columns(3)
    with colA:
        st.markdown("<div class='badge-note'>Tier</div>", unsafe_allow_html=True)
        badge(base_tier_ok, tier_label if tier_label != "Unclear" else "Tier unclear")
    with colB:
        st.markdown("<div class='badge-note'>Wagstaff</div>", unsafe_allow_html=True)
        badge(wag_ok, "Eligible" if wag_ok else "Not Eligible")
    with colC:
        st.markdown("<div class='badge-note'>Triten</div>", unsafe_allow_html=True)
        badge(triten_ok, "Eligible" if triten_ok else "Not Eligible")

    # =========================
    # Assign Law Firm (defaults to eligible one)
    # =========================
    st.subheader("Assign Law Firm")
    firm_options = ["Wagstaff Law Firm", "Triten Law Group", "Other (type name)"]
    if wag_ok:
        default_idx = 0
    elif triten_ok:
        default_idx = 1
    else:
        default_idx = 2
    assigned_firm_choice = st.selectbox("Choose firm for this PC", firm_options, index=default_idx, key="assigned_firm_choice")
    custom_firm_name = ""
    if assigned_firm_choice == "Other (type name)":
        custom_firm_name = st.text_input("Enter firm name", key="custom_firm_name").strip()

    def firm_header_and_short(choice, custom):
        if choice == "Wagstaff Law Firm":
            return "RIDESHARE Waggy | Retained", "Waggy", "Wagstaff Law Firm"
        if choice == "Triten Law Group":
            return "RIDESHARE Triten | Retained", "Triten", "Triten Law Group"
        name = custom or "Other Firm"
        return f"RIDESHARE {name} | Retained", name, name

    note_header, firm_short, assigned_firm_name = firm_header_and_short(assigned_firm_choice, custom_firm_name)

    # =========================
    # Diagnostics
    # =========================
    st.subheader("Diagnostics")

    st.markdown("#### Wagstaff")
    wag_lines = []
    wag_lines.append(f"• Tier = {tier_label}.")
    wag_lines.append(f"• Report OK? {'Yes' if wag_report_ok else 'No'} (allowed channels or audio/video evidence).")
    if set(report_dates.keys()) == {"Family/Friends"}:
        if family_report_dt:
            delta_hours = (family_report_dt - incident_dt).total_seconds() / 3600.0
            wag_lines.append(f"• Family-only report delta: {delta_hours:.1f} hours → {'OK (≤24h)' if within_24h_family_ok else 'Not OK (>24h)'}")
        else:
            wag_lines.append("• Family-only selected but time not provided.")
    wag_lines.append(f"• No attorney: {not has_atty}")
    wag_lines.append(f"• Inside/near scope: {inside_near}")
    wag_lines.append(f"• Felony: {'No' if not felony else 'Yes (DQ)'}")
    wag_lines.append(f"• Company: {company}")
    if sol_years is None:
        wag_lines.append(f"• SOL: No SOL per SA extension ({sol_rule_text}) → timing OK.")
    else:
        if sol_time_ok:
            wag_lines.append(f"• SOL open until {fmt_dt(sol_end)} ({sol_rule_text}).")
        else:
            wag_lines.append(f"• SOL passed — {fmt_dt(sol_end)} ({sol_rule_text}).")
    st.markdown("<div class='kv'>" + "\n".join(wag_lines) + "</div>", unsafe_allow_html=True)

    st.markdown("#### Triten")
    tri_lines = []
    tri_lines.append(f"• Tier = {tier_label}.")
    tri_lines.append(f"• Receipt (Email/PDF): {'Yes' if triten_receipt_ok else 'No'}")
    tri_lines.append(f"• Government ID: {'Yes' if triten_id_ok else 'No'}")
    tri_lines.append(f"• Female rider: {'Yes' if triten_gender_ok else 'No'}")
    tri_lines.append(f"• Rider (not driver): {'Yes' if triten_role_ok else 'No'}")
    if triten_report_any:
        if earliest_is_family:
            tri_lines.append(f"• Earliest report via Family/Friends; Δ days = {delta_days} → {'OK (≤14d)' if triten_family_14_ok else 'Not OK'}")
        else:
            tri_lines.append("• Report present via accepted channel.")
    else:
        tri_lines.append("• No report captured.")
    tri_lines.append(f"• No attorney: {'Yes' if triten_no_atty else 'No'}")
    tri_lines.append(f"• Scope inside/near: {'Yes' if triten_scope_ok else 'No'}")
    tri_lines.append(f"• SOL OK: {'Yes' if triten_sol_ok else 'No'}")
    tri_lines.append(f"• Company: {company}")
    st.markdown("<div class='kv'>" + "\n".join(tri_lines) + "</div>", unsafe_allow_html=True)

    # =========================
    # Summary
    # =========================
    st.subheader("Summary")
    sol_end_str = ("No SOL" if sol_years is None else (fmt_dt(sol_end) if sol_end else "—"))
    file_by_str = ("N/A (No SOL)" if sol_years is None else (fmt_dt(file_by_deadline) if file_by_deadline else "—"))
    report_dates_str = "; ".join([f"{k}: {fmt_date(v)}" for k, v in report_dates.items()]) if report_dates else "—"
    family_dt_str = fmt_dt(family_report_dt) if family_report_dt else "—"

    decision = {
        "Assigned Firm": assigned_firm_name,
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
        "File-by (SOL-45d)": file_by_str,
        "Reported Dates": report_dates_str,
        "Family/Friends Report (DateTime)": family_dt_str,
        "Wagstaff Eligible?": "Eligible" if wag_ok else "Not Eligible",
        "Triten Eligible?": "Eligible" if triten_ok else "Not Eligible",
    }
    st.dataframe(pd.DataFrame([decision]), use_container_width=True, height=360)

    # =========================
    # Detailed Report — Elements of Statement of the Case
    # =========================
    st.subheader("Detailed Report — Elements of Statement of the Case for RIDESHARE")

    acts_selected = [k for k, v in act_flags.items() if v and k not in ("Kidnapping Off-Route w/ Threats", "False Imprisonment w/ Threats")]
    aggr_selected = [k for k in ("Kidnapping Off-Route w/ Threats","False Imprisonment w/ Threats") if act_flags.get(k)]

    line_items = []
    def add_line(num, text): 
        line_items.append(f"{num}. {text}")

    add_line(1,  f"Caller Full / Legal: {caller_full_name or '—'} / {caller_legal_name or '—'}")
    add_line(2,  f"Assigned Firm: {assigned_firm_name}")
    add_line(3,  f"Platform: {company}")
    add_line(4,  f"Receipt Provided: {'Yes' if receipt else 'No'} | Evidence: {join_list(receipt_evidence)} | Files: {', '.join(uploaded_names) if uploaded_names else '—'}")
    add_line(5,  f"Incident Date/Time: {(fmt_date(incident_date) if incident_date else 'UNKNOWN')} {incident_time.strftime('%H:%M') if incident_time else ''}")
    add_line(6,  f"Reported to: {join_list(reported_to)} | Dates: {', '.join([f'{k}: {fmt_date(v)}' for k,v in report_dates.items()]) if report_dates else '—'}")
    if "Friend or Family Member" in reported_to:
        add_line(6.1, f"Family/Friend Contact: {(fam_first or '—')} {(fam_last or '')} | Phone: {fam_phone or '—'}")
    if "Physician" in reported_to:
        add_line(6.2, f"Physician: {phys_name or '—'} | Clinic/Hospital: {phys_fac or '—'} | Address: {phys_addr or '—'}")
    if "Therapist" in reported_to:
        add_line(6.3, f"Therapist: {ther_name or '—'} | Clinic/Hospital: {ther_fac or '—'} | Address: {ther_addr or '—'}")
    if "Police Department" in reported_to:
        add_line(6.4, f"Police Station: {police_station or '—'} | Address: {police_addr or '—'}")
    if "Rideshare Company" in reported_to:
        add_line(6.5, f"Rideshare Company (reported): {rep_rs_company or '—'}")
    add_line(7,  f"Where it happened (scope): {scope_choice}")
    add_line(8,  f"Pickup → Drop-off: {pickup or '—'} → {dropoff or '—'} | State: {state}")
    add_line(9,  f"Injuries — Physical: {'Yes' if injury_physical else 'No'}, Emotional: {'Yes' if injury_emotional else 'No'} | Details: {injuries_summary or '—'}")
    add_line(10, f"Provider: {provider_name or '—'} | Facility: {provider_facility or '—'} | Therapy start: {fmt_date(therapy_start) if therapy_start else '—'}")
    add_line(11, f"Medication: {medication_name or '—'} | Pharmacy: {pharmacy_name or '—'}")
    add_line(12, f"Rideshare submission: {rs_submit_how or '—'} | Company responded: {'Yes' if rs_received_response else 'No'} | Detail: {rs_response_detail or '—'}")
    add_line(13, f"Phone / Email: {caller_phone or '—'} / {caller_email or '—'}")
    add_line(14, f"Screen — Gov ID: {'Yes' if gov_id else 'No'} | Female: {'Yes' if female_rider else 'No'} | Rider (not driver): {'Yes' if rider_not_driver else 'No'} | Felony: {'Yes' if felony else 'No'} | Has Atty: {'Yes' if has_atty else 'No'}")
    add_line(15, f"Acts selected: {join_list(acts_selected)} | Aggravators: {join_list(aggr_selected)}")
    add_line(16, f"Tier: {tier_label}")
    add_line(17, f"SOL rule applied: {sol_rule_text} | SOL end: {('No SOL' if sol_years is None else fmt_dt(sol_end))} | File-by (SOL−45d): {file_by_str}")
    if earliest_report_date is not None:
        add_line(18, f"Earliest report: {fmt_date(earliest_report_date)} via {join_list(earliest_channels)} (Δ = {delta_days} day[s])")
    else:
        add_line(18, "Earliest report: —")
    add_line(19, f"Wagstaff Eligibility: {'Eligible' if wag_ok else 'Not Eligible'}")
    add_line(20, f"Triten Eligibility: {'Eligible' if triten_ok else 'Not Eligible'}")

    elements = "\n".join([str(x) for x in line_items])
    st.markdown(f"<div class='copy'>{elements}</div>", unsafe_allow_html=True)

    # =========================
    # Law Firm Note (Copy & Send)
    # =========================
    st.subheader("Law Firm Note (Copy & Send)")
    marketing_source = st.text_input("Marketing Source", value="", key="marketing_source")
    note_gdrive = st.text_input("GDrive URL", value="", key="note_gdrive")
    note_plaid_passed = st.checkbox("Plaid Passed", value=False, key="note_plaid_passed")
    note_receipt_pdf = st.checkbox(
        "Uber/Lyft PDF Receipt and screenshot",
        value=("PDF" in receipt_evidence and any("Screenshot" in x for x in receipt_evidence)),
        key="note_receipt_pdf"
    )
    note_state_id = st.checkbox("State ID", value=gov_id, key="note_state_id")
    note_extra = st.text_area("Additional note", value="", key="note_extra")

    tier_case_str = "Unclear"
    if tier_label.startswith("Tier 1"):
        tier_case_str = "1 Case"
    elif tier_label.startswith("Tier 2"):
        tier_case_str = "2 Case"

    created_str = TODAY.strftime("%B %d, %Y")
    company_upper = (company or "").upper()

    note_lines = [
        f"{note_header}",
        f"{caller_full_name or ''}".strip(),
        f"Phone number: {caller_phone or ''}".strip(),
        f"Email: {caller_email or ''}".strip(),
        f"Rideshare : {company_upper}",
        f"Tier: {tier_case_str}",
        f"Marketing Source: {marketing_source or ''}",
        f"Created: {created_str}",
    ]
    if full_ssn_on_file:
        note_lines.append(":white_check_mark:Full SSN")
    if note_receipt_pdf:
        note_lines.append(":white_check_mark:Uber/Lyft PDF Receipt and screenshot")
    if note_state_id:
        note_lines.append(":white_check_mark:State ID")
    if note_plaid_passed:
        note_lines.append(":white_check_mark:Plaid Passed")
    if note_gdrive:
        note_lines.append(f"Gdrive: {note_gdrive}")
    if note_extra:
        note_lines.append(f"Note: {note_extra}")

    lawfirm_note = "\n".join(note_lines)
    st.markdown(f"<div class='copy'>{lawfirm_note}</div>", unsafe_allow_html=True)

    st.download_button(
        "Download Law Firm Note (.txt)",
        data=lawfirm_note.encode("utf-8"),
        file_name="lawfirm_note.txt",
        mime="text/plain"
    )

    # Notepad-friendly Detailed Report
    detailed_report_txt = "Detailed Report — Elements of Statement of the Case for RIDESHARE\n\n" + elements
    st.download_button(
        "Download Detailed Report (.txt)",
        data=detailed_report_txt.encode("utf-8"),
        file_name="statement_of_case.txt",
        mime="text/plain"
    )

    # =========================
    # Export (XLSX if engine available + CSV)
    # =========================
    st.subheader("Export")

    # Earliest channels (string)
    earliest_channels_str = ", ".join(earliest_channels) if earliest_channels else ""

    export_payload = {
        # Assignment
        "AssignedFirm": assigned_firm_name,
        "AssignedFirmShort": firm_short,
        "LawFirmNoteHeader": note_header,

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
        "ReceiptEvidence": ", ".join(receipt_evidence) if receipt_evidence else "",
        "ReceiptEvidenceOther": receipt_evidence_other or "",
        "UploadedFiles": ", ".join(uploaded_names) if uploaded_names else "",

        # Reporting channels & details
        "ReportedTo": ", ".join(reported_to) if reported_to else "",
        "ReportDates": "; ".join([f"{k}: {fmt_date(v)}" for k, v in report_dates.items()]) if report_dates else "",
        "FamilyReportDateTime": (fmt_dt(family_report_dt) if family_report_dt else "—"),
        "FamilyFirstName": fam_first,
        "FamilyLastName": fam_last,
        "FamilyPhone": fam_phone,
        "PhysicianName": phys_name,
        "PhysicianClinicHospital": phys_fac,
        "PhysicianAddress": phys_addr,
        "TherapistName": ther_name,
        "TherapistClinicHospital": ther_fac,
        "TherapistAddress": ther_addr,
        "PoliceStation": police_station,
        "PoliceAddress": police_addr,
        "ReportedRideshareCompany": rep_rs_company,

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
        "FullSSN_OnFile": full_ssn_on_file,

        # Screening
        "GovIDProvided": gov_id,
        "FemaleRider": female_rider,
        "RiderNotDriver": rider_not_driver,
        "HasAttorney": has_atty,
        "Felony": felony,

        # Acts
        "Acts_RapePenetration": rape,
        "Acts_ForcedOralForcedTouch": forced_oral,
        "Acts_TouchingKissing": touching,
        "Acts_Exposure": exposure,
        "Acts_Masturbation": masturb,
        "Agg_Kidnap": kidnap,
        "Agg_Imprison": imprison,
        "Acts_Selected": ", ".join(acts_selected) if acts_selected else "",
        "Aggravators_Selected": ", ".join(aggr_selected) if aggr_selected else "",

        # SOL Calculations
        "SA_Category": category or "—",
        "SA_Extension_Used": (sol_state in SA_EXT) and bool(category),
        "SOL_Rule_Text": sol_rule_text,
        "SOL_Years": ("No SOL" if sol_years is None else sol_years),
        "SOL_End": ("No SOL" if sol_years is None else fmt_dt(sol_end)),
        "FileBy": ("N/A (No SOL)" if sol_years is None else fmt_dt(file_by_deadline)),
        "Earliest_Report_Date": (fmt_date(earliest_report_date) if earliest_report_date else "—"),
        "Earliest_Report_DeltaDays": (None if delta_days is None else int(delta_days)),
        "Earliest_Report_Channels": earliest_channels_str,
        "Earliest_Is_Family": earliest_is_family,

        # Eligibility
        "Eligibility_Wagstaff": "Eligible" if wag_ok else "Not Eligible",
        "Eligibility_Triten": "Eligible" if triten_ok else "Not Eligible",

        # Notes & Marketing
        "LawFirmNote": lawfirm_note,
        "MarketingSource": marketing_source,

        # Full text report
        "Elements_Report": elements.strip()
    }

    df_export = pd.DataFrame([export_payload])

    # Try formatted Excel
    xlsx_data = None
    xlsx_msg = ""
    if XLSX_ENGINE:
        try:
            xlsx_buf = BytesIO()
            with pd.ExcelWriter(xlsx_buf, engine=XLSX_ENGINE) as writer:
                df_export.to_excel(writer, index=False, sheet_name="Intake")
                if XLSX_ENGINE == "xlsxwriter":
                    workbook  = writer.book
                    worksheet = writer.sheets["Intake"]
                    fmt = workbook.add_format({"align": "center", "valign": "top", "text_wrap": True})
                    for col_idx in range(len(df_export.columns)):
                        worksheet.set_column(col_idx, col_idx, 28, fmt)
                    worksheet.freeze_panes(1, 0)
                elif XLSX_ENGINE == "openpyxl":
                    ws = writer.sheets["Intake"]
                    from openpyxl.styles import Alignment
                    alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)
                    for col_cells in ws.columns:
                        for cell in col_cells:
                            cell.alignment = alignment
                    for col in ws.columns:
                        col_letter = col[0].column_letter
                        ws.column_dimensions[col_letter].width = 28
                    ws.freeze_panes = "A2"
            xlsx_data = xlsx_buf.getvalue()
        except Exception as e:
            xlsx_msg = f"Excel export temporarily unavailable ({type(e).__name__}). Use TXT or CSV."
    else:
        xlsx_msg = "Excel engine not installed. Add 'xlsxwriter' or 'openpyxl' to requirements.txt to enable formatted Excel."

    if xlsx_data:
        st.download_button(
            "Download Excel (formatted .xlsx)",
            data=xlsx_data,
            file_name="intake_decision.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info(xlsx_msg)

    # Always provide CSV
    st.download_button(
        "Download CSV (legacy)",
        data=df_export.to_csv(index=False).encode("utf-8"),
        file_name="intake_decision.csv",
        mime="text/csv"
    )

render()
