import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time, date
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
.warn {background:#fff7ed; border-left:6px solid #f97316; color:#7c2d12; padding:10px 12px; border-radius:8px; margin:8px 0;}
.ok {background:#ecfdf5; border-left:6px solid #10b981; color:#065f46; padding:10px 12px; border-radius:8px; margin:8px 0;}
.info {background:#eff6ff; border-left:6px solid #3b82f6; color:#1e3a8a; padding:10px 12px; border-radius:8px; margin:8px 0;}
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
    "Ohio":2,"Oklahoma":2,"Oregon":3,"Pennsylvania":2,"Texas":2,"Virginia":2,"West Virginia":2,
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
# SEXUAL-ASSAULT EXTENSIONS
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
# NON-LETHAL DEFENSIVE ITEMS
# =========================
DEFENSIVE_ITEMS = [
    "Pepper Spray",
    "Personal Alarm",
    "Stun Gun",
    "Taser",
    "Self-Defense Keychain",
    "Tactical Flashlight",
    "Groin Kickers",
    "Personal Safety Apps",
    "Defense Flares",
    "Baton",
    "Kubotan",
    "Umbrella",
    "Whistle",
    "Combat Pen",
    "Pocket Knife",
    "Personal Baton",
    "Nunchaku",
    "Flashbang",
    "Air Horn",
    "Bear Spray",
    "Sticky Foam",
    "Tactical Scarf or Shawl",
    "Self-Defense Ring",
    "Hearing Protection",
]

# items clearly treated as *non-disqualifying* defensive tools
DEFENSIVE_EXEMPT = {
    "Pepper Spray","Bear Spray","Personal Alarm","Whistle","Air Horn",
    "Personal Safety Apps","Tactical Flashlight","Defense Flares","Sticky Foam",
    "Tactical Scarf or Shawl","Self-Defense Keychain","Hearing Protection","Umbrella"
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

def nonlethal_exempt(item):
    return item in DEFENSIVE_EXEMPT

# =========================
# APP
# =========================
st.title("Rideshare Intake Qualifier · with Coach + Deep Diagnostics")

def render():
    # ---------- meta / header ----------
    st.markdown("**Permission to Record (Private & Confidential)**")
    record_ok = st.checkbox("I have the caller’s permission to record this call for legal/training purposes.", value=False, key="perm_record")
    script_block("Thank you — recording helps protect you and your case. It is private and never filed publicly without your approval.")

    # Prior representation question (moved here per request)
    st.markdown("**Prior Representation Check**")
    prior_repr = st.radio(
        "As far as you can remember, have you signed up with any law firm to represent you on this case but then got disqualified for any reason?",
        ["No","Yes","Not sure"], index=0, key="prior_repr"
    )
    if prior_repr == "Yes":
        script_block("Thank you for letting me know. That doesn’t automatically prevent us from helping — it just guides the attorneys on how to proceed carefully.")
    elif prior_repr == "Not sure":
        script_block("Totally fine. If anything comes to mind later, we can note it. This won’t slow us down right now.")

    st.markdown("---")

    # ---------- law firm selection early so notes align ----------
    lawfirm = st.selectbox("Assign to Law Firm", ["— Select —","Wagstaff Law Firm","TriTen Law"], index=1, key="lawfirm_choice")
    st.markdown("<div class='small'>Your Law Firm Note format and export will match this selection.</div>", unsafe_allow_html=True)
    st.markdown("---")

    # ---------- Q1 Narrative ----------
    st.markdown("### Q1. Caller Narrative")
    pc_name = st.text_input("Client full name (PC)", key="client_name")

    narr = st.text_area("In your own words, please feel free to describe what happened during the ride.", key="q1_narr", height=140)
    if narr.strip():
        script_block("That sounds incredibly difficult. Thank you for trusting me with this — you’re not alone, and you’re in a safe space to share only what you’re comfortable sharing.")

    # Acts under narrative
    st.markdown("**Acts (check all that apply)**")
    rape = st.checkbox("Rape/Penetration", key="act_rape")
    forced_oral = st.checkbox("Forced Oral/Forced Touching", key="act_forced_oral")
    touching = st.checkbox("Touching/Kissing w/o Consent", key="act_touch")
    exposure = st.checkbox("Indecent Exposure", key="act_exposure")
    masturb = st.checkbox("Masturbation Observed", key="act_masturb")
    kidnap = st.checkbox("Kidnapping Off-Route w/ Threats", key="act_kidnap")
    imprison = st.checkbox("False Imprisonment w/ Threats", key="act_imprison")

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

    # ---------- Q2 Platform + pickup/dropoff ----------
    st.markdown("### Q2. Which rideshare platform was it?")
    company = st.selectbox("Select platform", ["Uber","Lyft","Other"], key="q2_company")
    script_block("Thanks — that helps us pull the correct records and reporting instructions for that platform.")

    st.markdown("**Pickup / Drop-off (extension to Q2)**")
    pickup = st.text_input("Pickup location (address/description)", key="pickup")
    dropoff = st.text_input("Drop-off location (address/description)", key="dropoff")
    if pickup or dropoff:
        script_block("Got it — thank you. Those locations help establish where the incident falls legally and which records we request. If anything’s approximate, that’s completely fine.")

    # ---------- Q3 Receipt (confident ask) + send method ----------
    st.markdown("### Q3. Ride Receipt")
    st.markdown("**Receipt requirement (read confidently):**")
    pc_display = pc_name.strip() if pc_name else "—"
    st.markdown(
        f"<div class='callout'>"
        f"{pc_display}, we need the ride receipt — both the email copy and the in-app receipt (a screenshot works). "
        f"Please forward them so the firm can verify the trip and lock in the timeline."
        f"</div>", unsafe_allow_html=True
    )

    receipt = st.toggle("Receipt available now (email/app/PDF)", value=False, key="q3_receipt_toggle")
    receipt_evidence = st.multiselect(
        "What can you provide as receipt evidence?",
        ["PDF","Email","Screenshot of Receipt","In-App Receipt (screenshot)","Other"],
        key="receipt_evidence"
    )
    receipt_evidence_other = st.text_input("If Other, describe", key="receipt_evidence_other")
    if receipt_evidence_other and "Other" not in receipt_evidence:
        receipt_evidence.append(f"Other: {receipt_evidence_other.strip()}")

    if receipt_evidence:
        script_block("Thank you — those docs make a huge difference for the attorneys. They’re some of the strongest pieces of proof for rideshare cases.")

    st.markdown("**Delivery method & phone**")
    st.markdown(
        "<div class='info'>I’ll text you my email so you can send the documents now or later. "
        "May I have the mobile number where you receive SMS? If this is also your current/best phone, I’ll reflect it under your contact details.</div>",
        unsafe_allow_html=True
    )
    sms_phone = st.text_input("Mobile number for SMS", key="sms_phone")
    best_phone = st.text_input("Best phone number (will auto-fill from SMS if left blank)", value=sms_phone, key="best_phone")
    doc_send_pref = st.selectbox(
        "How would you like to send documentation (receipts/ID/therapy notes/prescriptions)?",
        ["— Choose —","Texted link to upload photos","Email to jay@advocaterightscenter.com","FedEx/UPS fax"],
        key="doc_send_method"
    )

    # ---------- Q4 Incident date ----------
    st.markdown("### Q4. Do you remember the date this happened?")
    has_incident_date = st.toggle("Mark ON once claimant confirms they know the date", value=False, key="q4_hasdate")
    incident_date = st.date_input("Incident date", value=TODAY.date(), key="q4_date") if has_incident_date else None
    if incident_date:
        script_block("Thank you — this lets the firm check the statute of limitations and file within required timelines.")

    # ---------- Q5 Reporting ----------
    st.markdown("### Q5. Did you report the incident to anyone?")
    reported_to = st.multiselect(
        "Select all that apply",
        ["Rideshare Company","Police Department","Physician","Therapist","Friend or Family Member","NO (none yet)"],
        key="q5_reported"
    )
    report_dates = {}
    family_report_dt = None

    # Per-channel details
    # Rideshare
    if "Rideshare Company" in reported_to:
        report_dates["Rideshare company"] = st.date_input("Date reported to Rideshare company", value=TODAY.date(), key="q5_dt_rs")
        rs_company_select = st.selectbox("Which rideshare did you report to?", ["Uber","Lyft","Other/Unknown"], key="q5_rs_which")
    else:
        # Offer soft prompt to report to platform chosen in Q2
        if company in ("Uber","Lyft"):
            script_block(f"If you’re open to it, the attorney may ask you to report to {company} to strengthen your case. I can send the step-by-step instructions when you’re ready.")

    # Police
    if "Police Department" in reported_to:
        report_dates["Police"] = st.date_input("Date reported to Police", value=TODAY.date(), key="q5_dt_police")
        police_station = st.text_input("Name of Police Station", key="q5_police_name")
        police_address = st.text_input("Police Station Address", key="q5_police_addr")

    # Therapist
    if "Therapist" in reported_to:
        report_dates["Therapist"] = st.date_input("Date reported to Therapist", value=TODAY.date(), key="q5_dt_ther")
        ther_name = st.text_input("Therapist Name", key="q5_ther_name")
        ther_fac = st.text_input("Therapist Clinic/Hospital Name", key="q5_ther_fac")
        ther_addr = st.text_input("Therapist Clinic/Hospital Address", key="q5_ther_addr")

    # Physician
    if "Physician" in reported_to:
        report_dates["Physician"] = st.date_input("Date reported to Physician", value=TODAY.date(), key="q5_dt_phys")
        phys_name = st.text_input("Physician Name", key="q5_phys_name")
        phys_fac = st.text_input("Physician Clinic/Hospital Name", key="q5_phys_fac")
        phys_addr = st.text_input("Physician Clinic/Hospital Address", key="q5_phys_addr")

    # Family/Friend
    if "Friend or Family Member" in reported_to:
        ff_date = st.date_input("Date informed Friend/Family", value=TODAY.date(), key="q5_dt_ff")
        ff_time = st.time_input("Time informed Friend/Family", value=time(21,0), key="q5_tm_ff")
        ff_first = st.text_input("Friend/Family First Name", key="q5_ff_first")
        ff_last = st.text_input("Friend/Family Last Name", key="q5_ff_last")
        ff_phone = st.text_input("Friend/Family Phone Number", key="q5_ff_phone")
        report_dates["Family/Friends"] = ff_date
        family_report_dt = datetime.combine(ff_date, ff_time)

    if reported_to:
        script_block("Thanks — reporting details build a strong timeline. Even one trusted report helps establish credibility.")

    # ---------- Q6 Scope ----------
    st.markdown("### Q6. Did the incident happen inside the car, just outside, or did it continue after you exited?")
    scope_choice = st.selectbox("Location of incident", ["— Select —","Inside the car","Just outside the car","Continued after exit / nearby"], key="q6_scope")
    inside_near = scope_choice in ("Inside the car","Just outside the car","Continued after exit / nearby")
    if inside_near and scope_choice != "— Select —":
        script_block("Understood. That keeps the incident within the rideshare’s safety responsibility. Thank you for clarifying.")

    # ---------- Q7 Injury ----------
    st.markdown("### Q7. Were you injured physically, or have you experienced emotional effects afterward?")
    inj_choice = st.radio("Injury/Effects", ["Yes","No","Prefer not to say"], index=0, key="q7_inj")
    injured_yes = inj_choice == "Yes"
    if inj_choice == "Yes":
        script_block("I’m sorry you’ve been dealing with that. Your experience matters — both physical injuries and emotional trauma are recognized.")
    elif inj_choice == "No":
        script_block("Thank you for confirming. Even without visible injuries, what you went through is serious and deserves attention.")
    else:
        script_block("Thank you — you can share as much or as little as you’re comfortable sharing.")

    # ---------- Q8 Providers (only if injured) ----------
    if injured_yes:
        st.markdown("### Q8. Have you spoken to a doctor, therapist, or counselor?")
        spoke_provider = st.radio("Any medical/mental health provider?", ["Yes","No"], index=1, key="q8_spoke")
        provider_name = ""
        provider_fac = ""
        visit_first = None
        visit_last = None
        if spoke_provider == "Yes":
            provider_name = st.text_input("Provider name (optional)", key="q8_provider_name")
            provider_fac = st.text_input("Facility/Clinic (optional)", key="q8_provider_fac")
            visit_first = st.date_input("Date of the first visit", value=TODAY.date(), key="q8_first_visit")
            visit_last = st.date_input("Date of the last visit", value=TODAY.date(), key="q8_last_visit")
            script_block("Thank you — provider details and dates help the firm request the right records quickly.")
        else:
            script_block("Understood. If you decide to see someone later, we can update the file and help connect you with resources.")
    else:
        spoke_provider = "No"
        provider_name = ""
        provider_fac = ""
        visit_first = None
        visit_last = None

    # ---------- Standard Screening ----------
    st.markdown("### Standard Screening")

    # ID, Female rider, Atty
    female_rider = st.toggle("Female rider", value=False, key="elig_female")
    gov_id = st.toggle("Government ID provided", value=False, key="elig_id")
    if not gov_id:
        script_block("We’ll need a government ID so any settlement is paid to the right person. No banking details now — just identity verification.")
    has_atty = st.toggle("Already has an attorney", value=False, key="elig_atty")

    # Client carrying weapon?
    st.markdown("**Were you carrying a weapon at the time of the assault? (Personal defense tools like pepper spray/mace may not be a weapon)**")
    carried_weapon = st.radio("Carried any item?", ["No","Yes"], index=0, key="elig_client_weapon_radio")
    client_weapon = (carried_weapon == "Yes")
    carried_item = None
    if client_weapon:
        carried_item = st.selectbox("If yes, choose the item you carried", ["— Select —"] + DEFENSIVE_ITEMS, key="elig_client_item")
        if carried_item and carried_item != "— Select —":
            if nonlethal_exempt(carried_item):
                script_block("Thanks for sharing that. Items like these are for safety and don’t count against you here.")
            else:
                script_block("Thank you for your honesty. Based on current guidelines, carrying certain items may impact eligibility with some firms — we’ll handle this carefully.")
        else:
            script_block("Thank you — if you remember the item later, we can add it. Your transparency helps the attorneys prepare.")
    else:
        script_block("Okay, you did not have a weapon with you. That’s all we need on that part — thank you for confirming.")

    # Driver weapon or force?
    st.markdown("**Did the driver threaten to use or actually use any weapons, or use means of force (e.g., gun, knife, choking)?**")
    driver_force = st.radio("Driver used weapon/force?", ["No","Yes"], index=0, key="elig_driver_force")
    driver_force_detail = ""
    if driver_force == "Yes":
        driver_force_detail = st.text_area("Please elaborate on the weapon or force used", key="elig_driver_force_detail")
        script_block("That is very serious. I’m sorry you had to go through that — the details help the attorneys see the full picture.")
    else:
        script_block("Understood — even without a weapon, what happened is serious and does not diminish the impact in any way.")

    # Verbal/attempt-only filters
    verbal_only = st.toggle("Verbal abuse only (no sexual acts)", value=False, key="elig_verbal_only")
    attempt_only = st.toggle("Attempt/minor contact only", value=False, key="elig_attempt_only")

    # Felony question (polite verbatim)
    st.markdown("**Criminal History**")
    felony = st.toggle("This will not affect your case. So the law firm can be prepared for any character issues, do you have any felonies or criminal history?", value=False, key="elig_felony")

    # ---------- Contact & Screening ----------
    st.markdown("### Contact & Screening")
    email = st.text_input("Primary email", key="contact_email")
    if sms_phone and (not best_phone or best_phone.strip() == ""):
        best_phone_val = sms_phone
    else:
        best_phone_val = best_phone

    # ---------- Incident state/time for SOL ----------
    st.markdown("### Incident State & Time")
    state = st.selectbox("Incident State", STATES, index=(STATES.index("California") if "California" in STATES else 0), key="q6_state")
    incident_time = st.time_input("Incident time", value=time(21,0), key="time_for_calc")
    used_date = incident_date or TODAY.date()
    incident_dt = datetime.combine(used_date, incident_time)

    # ---------- SA category & SOL ----------
    category = sa_category(act_flags)  # 'penetration' | 'other' | None
    sol_state = STATE_ALIAS.get(state, state)
    sol_years, sol_rule_text, used_sa = sol_rule_for(sol_state, category)

    if sol_years is None:
        sol_end = None
        wagstaff_deadline = None
        wagstaff_time_ok = True
    else:
        sol_end = incident_dt + relativedelta(years=+int(sol_years))
        wagstaff_deadline = sol_end - timedelta(days=45)
        wagstaff_time_ok = TODAY <= wagstaff_deadline

    # ---------- Reporting timelines ----------
    # gather earliest relevant report date
    all_dates = [d for d in report_dates.values() if d]
    if family_report_dt: all_dates.append(family_report_dt.date())
    earliest_report_date = min(all_dates) if all_dates else None

    # Triten nuance: 14-day rule applies if Friend/Family is the reporting channel *without other channels*
    if "Friend or Family Member" in reported_to and set(reported_to).issubset({"Friend or Family Member"}):
        delta_days = (family_report_dt.date() - incident_dt.date()).days if family_report_dt else None
        triten_report_ok = (delta_days is not None) and (0 <= delta_days <= 14)
    else:
        # reported via company / police / therapist / physician — accept timeline as OK
        triten_report_ok = bool(reported_to and "NO (none yet)" not in reported_to)
        delta_days = (earliest_report_date - incident_dt.date()).days if earliest_report_date else None

    # ---------- Wagstaff disqualifiers & rules ----------
    wag_disq = []
    # Wagstaff requires report to at least one accepted channel, or family/friend within 24h
    wag_report_channels = {"Rideshare company","Police","Therapist","Physician"}
    wag_any_channel = any(k in report_dates for k in wag_report_channels)
    family_only_selected = set(reported_to) == {"Friend or Family Member"}
    within_24h_family_ok = True
    if family_only_selected:
        if not family_report_dt:
            within_24h_family_ok = False
            wag_disq.append("Family/Friends-only selected but date/time was not provided.")
        else:
            delta = family_report_dt - incident_dt
            within_24h_family_ok = (timedelta(0) <= delta <= timedelta(hours=24))
            if not within_24h_family_ok:
                wag_disq.append("Family/Friends-only report exceeded 24 hours after incident (Wagstaff rule).")

    wag_report_ok = wag_any_channel or (family_only_selected and within_24h_family_ok)

    # firm-specific constraints
    if felony:
        wag_disq.append("Felony record — Wagstaff may not accept.")
    if driver_force == "Yes":
        wag_disq.append("Driver weapon/force involved — disqualifies under Wagstaff.")
    if (carried_item and carried_item != "— Select —" and not nonlethal_exempt(carried_item)) or (client_weapon and not carried_item):
        wag_disq.append("Victim carrying a weapon — may disqualify under Wagstaff.")
    if verbal_only:
        wag_disq.append("Verbal abuse only — does not qualify.")
    if attempt_only:
        wag_disq.append("Attempt/minor contact only — does not qualify.")
    if has_atty:
        wag_disq.append("Already has an attorney — cannot intake.")

    common_ok = bool(female_rider and gov_id and inside_near and (not has_atty) and receipt)
    wag_ok_core = common_ok and wagstaff_time_ok and base_tier_ok and wag_report_ok and (not verbal_only) and (not attempt_only)
    wag_ok_company = company in ("Uber","Lyft")  # Wagstaff accepts Uber & Lyft now
    # If carried item is a clearly defensive tool, do not DQ on that basis
    carried_weapon_dq = False
    if client_weapon:
        if carried_item and carried_item != "— Select —":
            carried_weapon_dq = not nonlethal_exempt(carried_item)
        else:
            carried_weapon_dq = True  # said "Yes" but no item provided
    wag_ok = wag_ok_core and wag_ok_company and (driver_force != "Yes") and (not carried_weapon_dq) and (not felony)

    # ---------- Triten rules ----------
    tri_disq = []
    # Receipt must include Email or PDF
    has_required_receipt_type = any(x in receipt_evidence for x in ["PDF","Email"])
    if not receipt or not has_required_receipt_type:
        tri_disq.append("Receipt requirement (Email or PDF) not satisfied.")
    if not gov_id:
        tri_disq.append("Government ID not provided.")
    if not female_rider:
        tri_disq.append("Female rider requirement not met.")
    if has_atty:
        tri_disq.append("Already has an attorney.")
    if verbal_only or attempt_only:
        tri_disq.append("Verbal only or attempt/minor contact — does not qualify.")
    # Triten accepts felony records (no disq)
    if not inside_near:
        tri_disq.append("Incident not confirmed inside/near the vehicle.")
    if not base_tier_ok:
        tri_disq.append("Tier unclear — needs Tier 1 or Tier 2 acts.")
    if not triten_report_ok:
        tri_disq.append("Friend/Family-only reporting exceeded 14 days or missing date.")

    triten_ok = (len(tri_disq) == 0)

    # ---------- Badges ----------
    st.markdown("---")
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

    # ---------- Education Inserts ----------
    st.markdown("---")
    st.subheader("Education Inserts")
    with st.expander("Education #1 — How This Happened"):
        script_block("""Well, let me tell you what people have uncovered about Rideshares and why people like you are coming forward. And again, I appreciate you trusting us with this.

Uber & Lyft have been exposed for improperly screening drivers, failing to remove dangerous drivers, and misrepresenting their safety practices.

For example, the New York Times uncovered sealed court documents showing that over 400,000 incidents of sexual assault and misconduct were reported to Uber between 2017 and 2022 — which is about 1 incident every 8 minutes.

[[ Now when you consider that Uber originally only reported about 12,500 incidents during that same period, you can argue the company has been seriously misleading the level of safety it offers passengers. ]]

Now, we know many people don’t report these incidents. So, coming forward helps you and others obtain justice and compensation. [[ And it truly does help force Uber & Lyft to pay for their negligence, and provide real safety measures so these incidents stop happening. ]]""")

    with st.expander("Education #2 — Safe Rides Fee"):
        name_stub = pc_display if pc_display != "—" else "—"
        script_block(f"""{name_stub}, what’s especially troubling is that Uber and Lyft have had knowledge of these dangers since at least 2014.
That year, Uber introduced a $1 ‘Safe Rides Fee’ — claiming it funded driver checks and safety upgrades. But investigations found that most of the $500 million collected went to profit, not safety.
They later just renamed it a ‘booking fee.’ Survivors were paying for safety that never arrived.""")

    with st.expander("Education #3 — Law Firm & Contingency"):
        script_block(f"""{pc_display}, based on what you’ve told me, you might have a valid case. Here’s how pursuing a settlement works:
You hire the law firm on a contingency basis — no upfront costs, no out-of-pocket fees. You only owe if they win you a recovery.
We are the intake center for The Wagstaff Law Firm. Their attorneys are nationally recognized — many named Super Lawyers (top 5% of all attorneys). Judges across the country have appointed them to nine national Plaintiff Steering Committees, reserved for the top trial lawyers in corporate negligence cases.
They’re now applying that same leadership to hold Uber and Lyft accountable for failing survivors like you.""")

    with st.expander("Education #4 — Timeline for Settlement Distribution"):
        script_block(f"""{pc_display}, once the bellwether trials conclude, those results usually spark settlement negotiations. That’s when distributions begin — survivors don’t have to wait for every trial to finish. The test results give both sides the framework to resolve cases sooner.""")

    # ---------- Diagnostics ----------
    st.markdown("---")
    st.subheader("Diagnostics")

    # Wagstaff diagnostics
    st.markdown("#### Wagstaff")
    wag_lines = []
    wag_lines.append(f"• Tier = {tier_label}.")
    if not common_ok:
        base_reqs = f"female={bool(female_rider)}, receipt={bool(receipt)}, id={bool(gov_id)}, scope={bool(inside_near)}, has_atty={bool(has_atty)}"
        wag_lines.append(f"• Core requirements: {base_reqs}.")
    if not wag_report_ok:
        wag_lines.append("• Reporting rule not satisfied (needs company/police/therapist/physician, or family-only within 24h).")
    if client_weapon:
        if carried_item and nonlethal_exempt(carried_item):
            wag_lines.append("• Carried defensive item (non-disqualifying).")
        else:
            wag_lines.append("• Carried weapon (potential disqualifier).")
    if driver_force == "Yes":
        wag_lines.append("• Driver weapon/force involved → disqualifier for Wagstaff.")
    if felony:
        wag_lines.append("• Felony record → disqualifier for Wagstaff.")
    if verbal_only:
        wag_lines.append("• Verbal only.")
    if attempt_only:
        wag_lines.append("• Attempt/minor contact only.")
    if incident_date:
        if sol_years is None:
            wag_lines.append(f"• SOL timing: No SOL per sexual-assault extension — {sol_rule_text} → timing OK.")
        else:
            if TODAY > sol_end:
                wag_lines.append(f"• SOL passed ({sol_rule_text}) — deadline was {fmt_dt(sol_end)}.")
            else:
                wag_lines.append(f"• SOL open until {fmt_dt(sol_end)} ({sol_rule_text}).")
    else:
        wag_lines.append("• Incident date unknown → SOL timing cannot be verified precisely.")
    if sol_years is None:
        wag_lines.append("• Wagstaff file-by: not applicable (No SOL).")
    else:
        wag_lines.append(f"• Wagstaff file-by (SOL − 45 days): {fmt_dt(wagstaff_deadline)} → {'OK' if wagstaff_time_ok else 'Not OK'}.")
    if family_report_dt:
        delta_hours = (family_report_dt - incident_dt).total_seconds()/3600.0
        wag_lines.append(f"• Family/Friends-only report delta: {delta_hours:.1f} hours → {'OK (≤24h)' if within_24h_family_ok else 'Not OK (>24h)'}.")

    st.markdown("<div class='kv'>" + "\n".join(wag_lines) + "</div>", unsafe_allow_html=True)

    # Triten diagnostics
    st.markdown("#### Triten")
    tri_lines = []
    tri_lines.append(f"• Tier = {tier_label}.")
    tri_lines.append(f"• Receipt provided: {bool(receipt)}; Required type (Email/PDF) satisfied: {bool(has_required_receipt_type)}.")
    tri_lines.append(f"• ID provided: {bool(gov_id)}; Female: {bool(female_rider)}; Has atty: {bool(has_atty)}.")
    if "Friend or Family Member" in reported_to and set(reported_to).issubset({"Friend or Family Member"}):
        tri_lines.append(f"• Friend/Family reporting path with 14-day rule → {'OK' if triten_report_ok else 'Not OK'}.")
    else:
        tri_lines.append("• Reported to company/police/therapist/physician → timeline accepted.")
    if verbal_only or attempt_only:
        tri_lines.append("• Verbal/attempt-only → disqualifier.")
    if not inside_near:
        tri_lines.append("• Scope not confirmed.")
    if not base_tier_ok:
        tri_lines.append("• Tier unclear.")
    if tri_disq:
        tri_lines.extend([f"• {x}" for x in tri_disq])

    st.markdown("<div class='kv'>" + "\n".join(tri_lines) + "</div>", unsafe_allow_html=True)

    # ---------- Summary Table ----------
    st.markdown("---")
    st.subheader("Summary")
    sol_end_str = ("No SOL" if sol_years is None else (fmt_dt(sol_end) if sol_end else "—"))
    wag_deadline_str = ("N/A (No SOL)" if sol_years is None else (fmt_dt(wagstaff_deadline) if wagstaff_deadline else "—"))
    report_dates_str = "; ".join([f"{k}: {fmt_date(v)}" for k, v in report_dates.items()]) if report_dates else "—"
    family_dt_str = fmt_dt(family_report_dt) if family_report_dt else "—"
    decision = {
        "Company": company,
        "State": state,
        "Tier": tier_label,
        "SA category for SOL": category or "—",
        "Using SA extension?": "Yes" if (category and sol_state in SA_EXT) else "No (general tort)",
        "SOL rule applied": sol_rule_text,
        "SOL End (est.)": sol_end_str,
        "Wagstaff file-by (SOL-45d)": wag_deadline_str,
        "Reported Dates": report_dates_str,
        "Friend/Family Report (DateTime)": family_dt_str,
        "Wagstaff Eligible?": "Eligible" if wag_ok else "Not Eligible",
        "Triten Eligible?": "Eligible" if triten_ok else "Not Eligible",
    }
    st.dataframe(pd.DataFrame([decision]), use_container_width=True, height=280)

    # ---------- Law Firm Note (Copy & Send) ----------
    st.markdown("---")
    st.subheader("Law Firm Note (Copy & Send)")

    marketing_source = st.text_input("Marketing Source", key="marketing_source")
    created_str = TODAY.strftime("%B %d, %Y")
    tier_simple = "Tier 1 Case" if "Tier 1" in tier_label else ("Tier 2 Case" if "Tier 2" in tier_label else "Tier Unclear")

    # Build Note body
    checks = []
    if gov_id: checks.append("State ID")
    if receipt and receipt_evidence: checks.append("Receipt docs")
    if sms_phone: checks.append("SMS on file")
    ssn_full = st.text_input("Social Security Number (Full preferred; last 4 if declining full)", key="ssn_full_or_last4")
    if ssn_full.strip():
        checks.append("SSN on file")

    gdrive_link = st.text_input("GDrive (optional)", key="gdrive_link")

    note_header = f"RIDESHARE {('Waggy' if lawfirm=='Wagstaff Law Firm' else 'TriTen')} | {'Retained' if (wag_ok or triten_ok) else 'Intake'}"
    note_lines = [
        note_header,
        pc_display,
        f"Phone number: {best_phone_val or '—'}",
        f"Email: {email or '—'}",
        f"Rideshare: {company}",
        f"Tier: {tier_simple}",
        f"Marketing Source: {marketing_source or '—'}",
        f"Created: {created_str}",
    ]
    # checkmarks
    for c in checks:
        note_lines.append(f":white_check_mark:{c}")
    if gdrive_link:
        note_lines.append(f"Gdrive: {gdrive_link}")
    note_lines.append("Note: (add any context here)")
    law_note_text = "\n".join(note_lines)

    st.text_area("Final Note (editable)", value=law_note_text, key="final_note", height=200)

    st.download_button(
        "Download Note as .txt (Notepad-friendly)",
        data=st.session_state["final_note"].encode("utf-8"),
        file_name="law_firm_note.txt",
        mime="text/plain"
    )

    # ---------- Detailed Report (monospace) ----------
    st.markdown("---")
    st.subheader("Detailed Report — Elements of Statement of the Case for RIDESHARE (monospace)")

    acts_selected = [k for k, v in act_flags.items() if v and k not in ("Kidnapping Off-Route w/ Threats", "False Imprisonment w/ Threats")]
    aggr_selected = [k for k in ("Kidnapping Off-Route w/ Threats","False Imprisonment w/ Threats") if act_flags.get(k)]

    # Reporting channels summary
    earliest_channels = []
    if earliest_report_date:
        for k, v in report_dates.items():
            if v == earliest_report_date:
                earliest_channels.append(k)

    elements = []
    def add_line(num, text): elements.append(f"{num}. {text}")

    add_line(1, f"Date of ride: {fmt_date(incident_date) if incident_date else 'UNKNOWN'}")
    add_line(2, f"Name of PC: {pc_display if pc_display!='—' else 'UNKNOWN'}")
    add_line(3, f"Reserved a ride with: {company}")
    add_line(4, f"Pick-up → Drop-off: {pickup or 'UNKNOWN'} → {dropoff or 'UNKNOWN'}")
    add_line(5, f"Brief/categorical description: {categorical_brief(act_flags)}")
    add_line(6, f"Person/entities PC reported incident: {join_list(reported_to)}")
    add_line(7, f"Receipt Provided: {'Yes' if receipt else 'No'}")
    add_line(8, f"Receipt Evidence: {join_list(receipt_evidence)}")
    add_line(9, f"Female rider: {'Yes' if female_rider else 'No'}; Government ID: {'Yes' if gov_id else 'No'}")
    add_line(10, f"Scope inside/near vehicle: {'Confirmed' if inside_near else 'Not confirmed'}")
    add_line(11, f"Acts selected: {join_list(acts_selected)}")
    add_line(12, f"Aggravators selected: {join_list(aggr_selected)}")
    add_line(13, f"Tier result: {tier_label}")
    add_line(14, f"Incident state: {state}")
    add_line(15, f"Incident time: {incident_time.strftime('%H:%M')}")
    add_line(16, f"Reporting channels & dates: {', '.join([f'{k}: {fmt_date(v)}' for k,v in report_dates.items()]) if report_dates else '—'}")
    if earliest_report_date:
        add_line(17, f"Earliest report: {fmt_date(earliest_report_date)} via {join_list(earliest_channels)}")
    else:
        add_line(17, "Earliest report: —")
    if family_report_dt:
        delta_hours = (family_report_dt - incident_dt).total_seconds()/3600.0
        add_line(18, f"Family/Friends report DateTime: {fmt_dt(family_report_dt)} (Δ ≈ {delta_hours:.1f} hours)")
    else:
        add_line(18, "Family/Friends report DateTime: —")
    add_line(19, f"SOL rule applied: {sol_rule_text}")
    add_line(20, f"SOL end (if applicable): {('No SOL' if sol_years is None else fmt_dt(sol_end))}")
    add_line(21, f"Wagstaff file-by (SOL − 45d): {('N/A (No SOL)' if sol_years is None else fmt_dt(wagstaff_deadline))}")
    add_line(22, f"Wagstaff Eligibility: {'Eligible' if wag_ok else 'Not Eligible'}")
    add_line(23, f"Triten Eligibility: {'Eligible' if triten_ok else 'Not Eligible'}")

    elements_text = "\n".join(elements)
    st.markdown(f"<div class='copy'>{elements_text}</div>", unsafe_allow_html=True)

    # Exports — CSV and TXT
    st.markdown("#### Export")
    export_payload = {
        "ClientName": pc_display, "Narrative": narr, "Company": company, "State": state,
        "IncidentDate": fmt_date(incident_date) if incident_date else "UNKNOWN",
        "IncidentTime": incident_time.strftime("%H:%M"),
        "Pickup": pickup, "Dropoff": dropoff,
        "Receipt": receipt, "ReceiptEvidence": receipt_evidence, "ReceiptEvidenceOther": receipt_evidence_other,
        "IDProvided": gov_id, "InsideNear": inside_near, "HasAtty": has_atty,
        "FemaleRider": female_rider, "Felony": felony,
        "ClientCarriedWeapon": client_weapon, "ClientCarriedItem": carried_item or "—",
        "DriverWeaponOrForce": driver_force, "DriverForceDetail": driver_force_detail,
        "VerbalOnly": verbal_only, "AttemptOnly": attempt_only,
        "Acts_RapePenetration": rape, "Acts_ForcedOralForcedTouch": forced_oral,
        "Acts_TouchingKissing": touching, "Acts_Exposure": exposure, "Acts_Masturbation": masturb,
        "Agg_Kidnap": kidnap, "Agg_Imprison": imprison,
        "ReportedTo": reported_to, "ReportDates": {k: fmt_date(v) for k,v in report_dates.items()},
        "FamilyReportDateTime": fmt_dt(family_report_dt) if family_report_dt else "—",
        "Tier": tier_label, "SA_Category": category or "—",
        "SOL_Rule_Text": sol_rule_text, "SOL_Years": ("No SOL" if sol_years is None else sol_years),
        "SOL_End": ("No SOL" if sol_years is None else fmt_dt(sol_end)),
        "Wagstaff_FileBy": ("N/A (No SOL)" if sol_years is None else fmt_dt(wagstaff_deadline)),
        "Eligibility_Wagstaff": "Eligible" if wag_ok else "Not Eligible",
        "Eligibility_Triten": "Eligible" if triten_ok else "Not Eligible",
        "LawFirm": lawfirm,
        "MarketingSource": marketing_source or "—",
        "BestPhone": best_phone_val or "—",
        "PrimaryEmail": email or "—",
        "SSN": ssn_full or "—",
        "Elements_Report": elements_text.strip()
    }

    # CSV with basic formatting expectations (Excel)
    csv_bytes = pd.DataFrame([export_payload]).to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV (Excel)", data=csv_bytes, file_name="intake_decision.csv", mime="text/csv")

    # ---------- Firm-Specific Client Contact Details ----------
    st.markdown("---")
    st.subheader("Firm-Specific Client Contact Details")

    if lawfirm == "TriTen Law":
        st.markdown("#### TriTen – Intake CLIENT CONTACT DETAILS")
        tri_first = st.text_input("First Name", key="tri_first")
        tri_middle = st.text_input("Middle Name (optional)", key="tri_mid")
        tri_last = st.text_input("Last Name", key="tri_last")
        tri_maiden = st.text_input("Maiden Name (if applicable)", key="tri_maiden")
        tri_pref_name = st.text_input("Preferred Name (optional)", key="tri_pref")
        tri_email = st.text_input("Primary Email", value=email, key="tri_email")
        tri_address = st.text_input("Mailing Address", key="tri_addr")
        tri_city = st.text_input("City", key="tri_city")
        tri_state = st.selectbox("State", STATES + ["Puerto Rico"], key="tri_state")
        tri_zip = st.text_input("Zip", key="tri_zip")
        tri_home = st.text_input("Home Phone No.", key="tri_home")
        tri_cell = st.text_input("Cell Phone No.", value=best_phone_val, key="tri_cell")
        tri_best_time = st.text_input("Best Time to Contact", key="tri_best_time")
        tri_pref_method = st.selectbox("Preferred Method of Contact", ["Phone","Email","Phone & Email","Text"], index=2, key="tri_pref_method")
        tri_dob = st.date_input("Date of Birth (mm-dd-yyyy)", value=TODAY.date(), key="tri_dob")
        # Auto age from DOB
        def calc_age(dob):
            if not isinstance(dob, date): return "—"
            todayd = TODAY.date()
            years = todayd.year - dob.year - ((todayd.month, todayd.day) < (dob.month, dob.day))
            return years
        tri_age = calc_age(tri_dob)
        st.markdown(f"**Age:** {tri_age}")
        tri_ssn = st.text_input("Social Security No. (full preferred; last 4 if declining full)", value=ssn_full, key="tri_ssn")
        st.markdown(
            "<div class='info'>The hospital must ensure they send the correct information. For legal purposes and proper documentation, we need your full name, address, date of birth, and Social Security number. "
            "I understand sharing SSN can feel sensitive, but it protects your identity and ensures the settlement goes to the right person. If you prefer, you can share just the <b>last 4 digits</b>; those are often enough for HIPAA releases.</div>",
            unsafe_allow_html=True
        )
        tri_claim_for = st.selectbox("Does the claim pertain to you or another person?", ["Myself","Someone else"], key="tri_claim_for")
        tri_marital = st.selectbox("Current marital status", ["Single","Married","Divorced","Widowed"], key="tri_marital")

        st.markdown("**INJURED PARTY DETAILS**")
        tri_inj_name = st.text_input("Injured/Deceased Party's Full Name (First, Middle, Last)", key="tri_inj_name")
        tri_inj_gender = st.selectbox("Injured Party Gender", ["Female","Male","Non-binary","Prefer not to say"], key="tri_inj_gender")
        tri_inj_dob = st.date_input("Injured/Deceased Party's DOB (mm-dd-yyyy)", value=tri_dob, key="tri_inj_dob")

        # Affirmation at the end (as requested)
        st.markdown("---")
        affirm = st.radio(
            "[Having just confirmed all the answers you provided] Do you affirm that the information is true and correct in all respects, including whether you've ever signed up with another law firm?",
            ["Yes","No"], index=0, key="tri_affirm"
        )
        st.markdown("**INTAKE ENDS HERE**")

    elif lawfirm == "Wagstaff Law Firm":
        st.markdown("#### Wagstaff – CLIENT CONTACT DETAILS")
        wag_first = st.text_input("First Name", key="wag_first")
        wag_middle = st.text_input("Middle Name (optional)", key="wag_mid")
        wag_last = st.text_input("Last Name", key="wag_last")
        wag_email_c = st.text_input("Primary Email", value=email, key="wag_email")
        wag_address = st.text_input("Mailing Address", key="wag_addr")
        wag_city = st.text_input("City", key="wag_city")
        wag_state = st.selectbox("State", STATES + ["Puerto Rico"], key="wag_state")
        wag_zip = st.text_input("Zip", key="wag_zip")
        wag_home = st.text_input("Home Phone No.", key="wag_home")
        wag_cell = st.text_input("Cell Phone No.", value=best_phone_val, key="wag_cell")
        wag_best_time = st.text_input("Best Time to Contact", key="wag_best_time")
        wag_pref_method = st.selectbox("Preferred Method of Contact", ["Phone","Email","Phone & Email","Text"], index=2, key="wag_pref_method")
        wag_dob = st.date_input("Date of Birth (mm-dd-yyyy)", value=TODAY.date(), key="wag_dob")
        wag_ssn = st.text_input("Social Security No. (full preferred; last 4 if declining full)", value=ssn_full, key="wag_ssn")
        st.markdown(
            "<div class='info'>The hospital must ensure they send the correct information. For legal purposes and proper documentation, we need your full name, address, date of birth, and Social Security number. "
            "I understand sharing SSN can feel sensitive, but it protects your identity and ensures the settlement goes to the right person. If you prefer, you can share just the <b>last 4 digits</b>; those are often enough for HIPAA releases.</div>",
            unsafe_allow_html=True
        )
        wag_claim_for = st.selectbox("Does the claim pertain to you or another person?", ["Myself","Someone else"], key="wag_claim_for")

    # ---------- Objection Script / Legend / References ----------
    st.markdown("---")
    st.subheader("Objection Script / Legend / References")
    obj = st.selectbox(
        "Choose a quick script or reference",
        [
            "— Select —",
            "Incident Not Qualified",
            "How much is the settlement",
            "How much will the law firm charge me",
            "PC Disagreement Over 40% Fee",
            "Asking ID and other evidences",
            "Asking SSN",
            "Asking last 4 digits - SSN",
            "I did not submit my information",
            "Where are you from",
            "Scam Suspicions",
            "Multi-District Litigation (MDL) vs. Class Action",
            "Class Action Clarification",
            "I Need a Local Law Firm",
            "What kind of claim is this?",
            "Are settlements taxable?",
            "What happens if I die?",
            "Reasons for Using Plaid",
            "Using Plaid: Quick Directions",
            "Has Attorney",
            "Unanswered Client Callback Script",
            "RSA District Court?",
            "Settlement Claims in Rideshare Assault",
            "Rideshare Companies in Litigation",
            "Medical Office Three-Way Call",
            "Wagstaff Law Information",
            "Instructions for Resending Rideshare Receipts",
            "How to Report an Assault to Uber/Lyft",
            "Script for Irate Callers",
            "Responding to Law Firm",
            "Using Plaid: Quick Directions (link)",
            "ID and Proof Retrieval Script",
            "Mailer – Commitment Script",
            "Esign Guide Text",
            "Esign Guide Email",
            "Identity Verification Links",
            "PLAID Link",
            "How to Send Plaid Link to Clients",
            "How to Guide Clients in Plaid Text",
            "SOP for Plaid",
            "Call Transfers with C9 and Law Ruler",
            "RSA - Objection Script",
        ],
        key="obj_picker"
    )

    obj_map = {
        "Incident Not Qualified": "I apologize, but the incident does not meet our firm's criteria. If that changes, we’ll contact you. In the meantime, consider reaching out to other firms.",
        "How much is the settlement": "I don't want to misinform you — it depends on the specifics and trauma involved. For context, in Dec 2022 the California PUC approved a $9M settlement with Uber regarding reporting issues; each case is unique.",
        "How much will the law firm charge me": "Standard fee is 40% due to the risks involved. You owe nothing upfront. We’ll handle records and expert review. If there’s no recovery — you owe nothing.",
        "PC Disagreement Over 40% Fee": "I respect that. Most firms use this fee due to uncertainty. You’re paying for seasoned counsel and convenience — no record chasing or court appearances for you. If you proceed today, we move forward with no upfront payment.",
        "Asking ID and other evidences": "To qualify, we need to retrieve medical/therapy records and confirm identity so funds go to the right person. Please provide a government ID + selfie, and any records/photos/med bottles that support your claim.",
        "Asking SSN": "The hospital must ensure they send the correct information... (full explanation as above).",
        "Asking last 4 digits - SSN": "Can I get just the last four digits for HIPAA releases? These remain private and confidential.",
        "I did not submit my information": "You likely filled out a survey or form online. If you or a loved one experienced a rideshare sexual assault, we can connect you with top attorneys. I’m here to help you pursue a settlement.",
        "Where are you from": "I’m calling from Dallas, Texas, representing the Advocate Rights Center, an intake center for your selected firm.",
        "Scam Suspicions": "I won’t need bank details. We ask only for information needed to obtain records and prove your claim. This protects your identity and strengthens your case.",
        "Multi-District Litigation (MDL) vs. Class Action": "MDL is individualized — compensation reflects personal impact. Class actions divide equally regardless of differences.",
        "Class Action Clarification": "This isn’t a class action; compensation is customized based on exactly what happened to you.",
        "I Need a Local Law Firm": "Claims are consolidated in the N.D. of California (MDL 3084). You don’t need a local attorney anymore. You can choose the firm you prefer.",
        "What kind of claim is this?": "These are personal injury claims against the rideshare company for harms caused by sexual assault incidents.",
        "Are settlements taxable?": "Generally, personal injury/emotional distress settlements are non-taxable, but please consult a tax professional.",
        "What happens if I die?": "If a claimant passes, the firm substitutes the estate administrator. A will is helpful; a case manager will guide your family.",
        "Reasons for Using Plaid": "1) Identity verification, 2) Medical records under HIPAA, 3) Accurate settlement routing; no banking details until a settlement is confirmed.",
        "Using Plaid: Quick Directions": "Click the link, enter last 4 of SSN, photo both sides of your ID, then a 10-second selfie. That matches your ID to keep your case secure.",
        "Has Attorney": "To avoid double representation, if you already have an attorney, we can’t proceed.",
        "Unanswered Client Callback Script": "The firm has been trying to reach you to verify a few things... please call them back; engagement helps them invest resources in your case.",
        "RSA District Court?": "Claims are consolidated in the U.S. District Court for the Northern District of California under Judge Charles Breyer (MDL No. 3084).",
        "Settlement Claims in Rideshare Assault": "Medical expenses, emotional distress, lost wages, punitive damages, legal fees, pain/suffering, future medical, loss of enjoyment, property damage, loss of consortium.",
        "Rideshare Companies in Litigation": "Uber, Lyft, Via, Ola, Grab, Didi Chuxing, Bolt, Gett.",
        "Medical Office Three-Way Call": "We can 3-way call your provider to confirm last visit and condition (with your permission). This is to validate the claim, not for evidence — the records cover that.",
        "Wagstaff Law Information": "Wagstaff Law Firm — 940 Lincoln St, Denver, CO 80203; 303-376-6360; https://www.wagstafflawfirm.com/",
        "Instructions for Resending Rideshare Receipts": "Uber: Activity tab → ride → Receipt → resend email. Lyft: Ride history → ride → Resend receipt.",
        "How to Report an Assault to Uber/Lyft": "See guide link: https://docs.google.com/document/d/1Oiljbf3oHqtoKDv2jArsXMIVw5hhuNrRiZ1MDl0aoqo/edit",
        "Script for Irate Callers": "https://docs.google.com/document/d/1wlQurtqG_0tVIUhBfHXL2R8fF58i8s64/edit",
        "Responding to Law Firm": "https://docs.google.com/document/d/1BNJoF14vqEkH2WojUC_H7AsWUmu-ZC1NVmvO0J_GN9Q/edit",
        "Using Plaid: Quick Directions (link)": "https://docs.google.com/document/d/1P_jodMzz-2vc0vQsDbgCimCBDGDHyuNaFqyE7KmbO5Y/edit",
        "ID and Proof Retrieval Script": "https://docs.google.com/document/d/1DTcBIWg4NJfEgETe4bwagbz4refPSyoP/edit",
        "Mailer – Commitment Script": "https://docs.google.com/document/d/1VMxf5JcVIFN2ABXmkLHKdkvYJ6tfmSmIp0jlMrh7glE/edit",
        "Esign Guide Text": "https://docs.google.com/document/d/1e6sGJB8wRPwa2_sBEvLbDl4wUM4TsS8f46agwNWvIRE/edit",
        "Esign Guide Email": "https://docs.google.com/document/d/1zVTewqs7jtAB_yL0cdz8vz_8o-IfgoYVhj4KPNNG9M8/edit",
        "Identity Verification Links": "https://besthistorysites.net/ (placeholder; replace with your internal link)",
        "PLAID Link": "https://advocaterightscenter.com/plaid_verification/",
        "How to Send Plaid Link to Clients": "https://docs.google.com/document/d/1huakazfAU_-P3PORmcP5DLrdIn_pHRzGNjjdjnOWwVw/edit",
        "How to Guide Clients in Plaid Text": "https://docs.google.com/document/d/19Uj2gXI1WKOlnaVprvryvYipOgMAAum2gR4uDsMJ7B8/edit",
        "SOP for Plaid": "https://docs.google.com/document/d/1Rc_C3mqQ21CdpfbHAXzqDNernl32Jr-2/edit",
        "Call Transfers with C9 and Law Ruler": "https://docs.google.com/document/d/1powoAbPlhqVV3q54ZlgFIZml70Iudrzh/edit",
        "RSA - Objection Script": "https://docs.google.com/document/d/14fYJyeWYuuIbQmwrzGMCkuvnVoIwqrKy/edit",
    }
    if obj and obj in obj_map:
        st.markdown(f"<div class='script'>{obj_map[obj]}</div>", unsafe_allow_html=True)

    # ---------- Closing ----------
    st.markdown("---")
    st.subheader("Closing")
    st.markdown(
        "<div class='ok'>You’ve done something incredibly brave by sharing your story. Next steps: I’ll send the secure ID upload link and e-sign forms (retainer + HIPAA). "
        "A paralegal will call you at your preferred time; they may confirm your SSN for HIPAA releases. Would you like me to repeat any step?</div>",
        unsafe_allow_html=True
    )

render()
