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
.kv {font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace;}
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
# SEXUAL-ASSAULT EXTENSIONS (your reference)
# years=None means "No SOL"
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
    return label, (base in ("Tier 1","Tier 2") and len(aggr) > 0)

def sa_category(flags):
    """Decide SOL category: 'penetration', 'other', or None (if no SA selection)."""
    if flags.get("Rape/Penetration") or flags.get("Forced Oral/Forced Touching"):
        return "penetration"
    if flags.get("Touching/Kissing w/o Consent") or flags.get("Indecent Exposure") or flags.get("Masturbation Observed"):
        return "other"
    return None

def sol_rule_for(state, category):
    """
    Returns (years_or_None, rule_text, used_sa_extension: bool)
    If category is None or state not in SA_EXT => fall back to general TORT_SOL.
    """
    if category and state in SA_EXT:
        data = SA_EXT[state]
        years = data[category]
        # Full state summary (both categories) for diagnostics context:
        summary = data["summary"]
        return years, f"{state}: {summary}", True
    # General tort SOL fallback
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
st.title("Rideshare Intake Qualifier · with Coach + Deep Diagnostics")

def render():
    # ---------- page inputs ----------
    L, R = st.columns(2)

    with L:
        client_name = st.text_input("Client full name (PC)", key="client_name")
        st.markdown("**1. Describe what happened (allow claimant to speak freely).**")
        narr = st.text_area(" ", key="q1_narr")
        script_block('Agent Response: Thank you for sharing that with me. You said "[mirror key words]". This space is confidential.')

        st.markdown("**3. Are you able to reproduce the ride share receipt to show proof of the ride? (If not, DQ)**")
        receipt = st.toggle("Receipt provided (email/app/PDF)", value=False, key="q3_receipt_toggle")
        if not receipt:
            st.markdown("<div class='callout'><b>Text to send:</b><br><span class='copy'>Forward your receipt to <b>jay@advocaterightscenter.com</b> by selecting the ride in Ride History and choosing “Resend Receipt.”<br>(Msg Rates Apply. Txt STOP to cancel/HELP for help)</span></div>", unsafe_allow_html=True)

        st.markdown("**5. Reported to anyone?**")
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
            ff_date = st.date_input("Date informed Friend/Family", value=TODAY.date(), key="q5a_dt_ff")
            ff_time = st.time_input("Time informed Friend/Family", value=time(21,0), key="q5a_tm_ff")
            report_dates["Family/Friends"] = ff_date
            family_report_dt = datetime.combine(ff_date, ff_time)

        st.markdown("**7. Did the incident occur while utilizing the Rideshare service, either inside or just outside the vehicle?**")
        inside_near = st.toggle("Mark ON once confirmed inside/just outside/started near the car", value=False, key="q7_inside")
        if not inside_near:
            script_block("Did the incident occur while utilizing the Rideshare service, either inside or just outside the vehicle?")
        else:
            script_block("If Yes: Okay. So, it happened [repeat where happened]. Knowing where it happened confirms it was within the Rideshare’s safety responsibility.")

        st.markdown("**9. Did you receive a response from Uber or Lyft?**")
        rs_received_response = st.toggle("Mark ON if a response was received", value=False, key="q9_resp_toggle")
        rs_response_detail = st.text_input("If yes, what did they say? (optional)", key="q9_resp_detail")

    with R:
        st.markdown("**2. Which Rideshare company did you use?**")
        company = st.selectbox(" ", ["Uber","Lyft","Other"], key="q2_company")

        st.markdown("**4. Do you have the Date the incident occurred?**")
        has_incident_date = st.toggle("Mark ON once claimant confirms they know the date", value=False, key="q4_hasdate")
        incident_date = st.date_input("Select Incident Date", value=TODAY.date(), key="q4_date") if has_incident_date else None

        st.markdown("**6. What state did this happen?**")
        state = st.selectbox("Incident State", STATES, index=(STATES.index("California") if "California" in STATES else 0), key="q6_state")

        st.text_input("Pick-up location (full address or description)", key="pickup")
        st.text_input("Drop-off location (full address or description)", key="dropoff")
        st.text_input("Purpose of ride (optional if obvious from p/u → d/o)", key="purpose")

        st.markdown("**8. If submitted to Rideshare: how did you submit? (email/app/other)**")
        rs_submit_how = st.text_input("email / app / other", key="q8_submit_how")

        st.markdown("**10. Do you have any felonies or criminal history?**")
        felony = st.toggle("Mark ON only if they confirm a felony/criminal history", value=False, key="q10_felony")

    st.markdown("---")
    st.caption("Eligibility switches (leave OFF until verified)")
    colE1, colE2, colE3 = st.columns(3)
    with colE1:
        female_rider = st.toggle("Female rider", value=False, key="elig_female")
    with colE2:
        gov_id = st.toggle("ID provided", value=False, key="elig_id")
        if not gov_id:
            script_block("We’ll need a government ID to ensure any settlement is paid to the right person. No banking details requested now.")
    with colE3:
        has_atty = st.toggle("Already has an attorney", value=False, key="elig_atty")

    colX1, colX2, colX3, colX4 = st.columns(4)
    with colX1:
        driver_weapon = st.selectbox("Driver used/threatened weapon?", ["No","Non-lethal defensive (e.g., pepper spray)","Yes"], key="elig_driver_weapon")
    with colX2:
        client_weapon = st.toggle("Client carrying a weapon?", value=False, key="elig_client_weapon")
    with colX3:
        verbal_only = st.toggle("Verbal abuse only (no sexual acts)", value=False, key="elig_verbal_only")
    with colX4:
        attempt_only = st.toggle("Attempt/minor contact only", value=False, key="elig_attempt_only")

    st.subheader("Acts (check all that apply)")
    c1, c2 = st.columns(2)
    with c1:
        rape = st.checkbox("Rape/Penetration", key="act_rape")
        forced_oral = st.checkbox("Forced Oral/Forced Touching", key="act_forced_oral")
        touching = st.checkbox("Touching/Kissing w/o Consent", key="act_touch")
    with c2:
        exposure = st.checkbox("Indecent Exposure", key="act_exposure")
        masturb = st.checkbox("Masturbation Observed", key="act_masturb")
        kidnap = st.checkbox("Kidnapping Off-Route w/ Threats", key="act_kidnap")
        imprison = st.checkbox("False Imprisonment w/ Threats", key="act_imprison")

    # ========= Calculations =========
    incident_time = st.time_input("Incident Time (for timing rules)", value=time(21,0), key="time_for_calc")
    used_date = incident_date or TODAY.date()  # safe fallback so UI stays live, but flag in diagnostics if unknown
    incident_dt = datetime.combine(used_date, incident_time)

    act_flags = {
        "Rape/Penetration": rape,
        "Forced Oral/Forced Touching": forced_oral,
        "Touching/Kissing w/o Consent": touching,
        "Indecent Exposure": exposure,
        "Masturbation Observed": masturb,
        "Kidnapping Off-Route w/ Threats": kidnap,
        "False Imprisonment w/ Threats": imprison
    }
    tier_label, _ = tier_and_aggravators(act_flags)
    base_tier_ok = ("Tier 1" in tier_label) or ("Tier 2" in tier_label)

    # SA category & SOL rule
    category = sa_category(act_flags)  # 'penetration' | 'other' | None
    sol_state = STATE_ALIAS.get(state, state)
    sol_years, sol_rule_text, used_sa = sol_rule_for(sol_state, category)

    # Compute SOL end / Wagstaff timing
    if sol_years is None:
        sol_end = None
        wagstaff_deadline = None
        wagstaff_time_ok = True  # no SOL => no deadline
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
    if driver_weapon == "Yes": wag_disq.append("Weapon involved → disqualified under Wagstaff.")
    if client_weapon: wag_disq.append("Victim carrying a weapon → may disqualify.")
    if verbal_only: wag_disq.append("Verbal abuse only → does not qualify.")
    if attempt_only: wag_disq.append("Attempt/minor contact only → does not qualify.")
    if has_atty: wag_disq.append("Already has attorney → cannot intake.")

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
    common_ok = bool(female_rider and receipt and gov_id and inside_near and (not has_atty))

    wag_ok_core = common_ok and wagstaff_time_ok and within_24h_family_ok and base_tier_ok and (not wag_disq)
    wag_ok = wag_ok_core and (company == "Uber")
    tri_disq = []
    if verbal_only: tri_disq.append("Verbal abuse only → does not qualify.")
    if attempt_only: tri_disq.append("Attempt/minor contact only → does not qualify.")
    if earliest_report_date is None: tri_disq.append("No report date provided for any channel.")
    if not triten_report_ok: tri_disq.append("Earliest report not within 2 weeks.")
    if has_atty: tri_disq.append("Already has attorney → cannot intake.")
    triten_ok = bool(common_ok and triten_report_ok and base_tier_ok and (not tri_disq))

    # ========= UI: Eligibility badges =========
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

    # ========= DIAGNOSTICS (highly specific) =========
    st.subheader("Diagnostics")

    # Wagstaff diagnostics
    st.markdown("#### Wagstaff")
    wag_lines = []
    if tier_label == "Unclear":
        wag_lines.append("• Tier unclear (needs Tier 1 or Tier 2 acts).")
    else:
        wag_lines.append(f"• Tier = {tier_label}.")

    if company != "Uber":
        wag_lines.append(f"• Company policy: Wagstaff = Uber only → selected {company}.")
    if not female_rider: wag_lines.append("• Female rider requirement not met.")
    if not receipt: wag_lines.append("• Receipt not provided.")
    if not gov_id: wag_lines.append("• ID not provided.")
    if not inside_near: wag_lines.append("• Scope not confirmed as inside/just outside vehicle.")
    if has_atty: wag_lines.append("• Already represented by an attorney.")
    wag_lines.extend([f"• {x}" for x in wag_disq])

    # SOL specifics
    if not incident_date:
        wag_lines.append("• Incident date is unknown → SOL timing cannot be verified precisely.")
    if used_sa:
        # show state rule once, plus pass/fail
        if sol_years is None:
            wag_lines.append(f"• SOL timing: No SOL per sexual-assault extension — {sol_rule_text} → timing OK.")
        else:
            if TODAY > sol_end:
                wag_lines.append(f"• SOL passed ({sol_rule_text}) — deadline was {fmt_dt(sol_end)}.")
            else:
                wag_lines.append(f"• SOL open until {fmt_dt(sol_end)} ({sol_rule_text}).")
    else:
        # using general tort SOL
        if sol_years is None:
            wag_lines.append(f"• SOL timing: No SOL (unexpected for {state}).")
        else:
            if TODAY > (sol_end or TODAY):
                wag_lines.append(f"• SOL passed — general tort rule {sol_years} year(s); deadline was {fmt_dt(sol_end)}.")
            else:
                wag_lines.append(f"• SOL open until {fmt_dt(sol_end)} — general tort rule {sol_years} year(s).")

    # Wagstaff file-by check
    if sol_years is None:
        wag_lines.append("• Wagstaff file-by: not applicable (No SOL).")
    else:
        wag_lines.append(f"• Wagstaff file-by (SOL − 45 days): {fmt_dt(wagstaff_deadline)} → {'OK' if wagstaff_time_ok else 'Not OK'}.")

    # Family-only rule
    if set(reported_to) == {"Friend or Family Member"}:
        if family_report_dt:
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

    tri_lines.append(f"• Common requirements: female={bool(female_rider)}, receipt={bool(receipt)}, id={bool(gov_id)}, scope={bool(inside_near)}, has_atty={bool(has_atty)}.")
    if earliest_report_date:
        tri_lines.append(f"• Earliest report date = {fmt_date(earliest_report_date)}; incident = {fmt_date(incident_dt.date())}; Δ = {delta_days} day(s) → {'OK (≤14 days)' if triten_report_ok else 'Not OK (>14 days or negative)'}")
    else:
        tri_lines.append("• No earliest report date captured → cannot verify 14-day requirement.")
    tri_lines.extend([f"• {x}" for x in tri_disq])

    st.markdown("<div class='kv'>" + "\n".join(tri_lines) + "</div>", unsafe_allow_html=True)

    # ========= SUMMARY TABLE =========
    st.subheader("Summary")
    sol_end_str = fmt_dt(sol_end) if sol_years not in (None, ) and sol_end else ("—" if sol_years is not None else "No SOL")
    wag_deadline_str = fmt_dt(wagstaff_deadline) if wagstaff_deadline else ("—" if sol_years is not None else "N/A (No SOL)")
    report_dates_str = "; ".join([f"{k}: {fmt_date(v)}" for k, v in report_dates.items()]) if report_dates else "—"
    family_dt_str = fmt_dt(family_report_dt) if family_report_dt else "—"
    decision = {
        "Company": company,
        "Tier (severity-first)": tier_label,
        "SA category for SOL": category or "—",
        "Used SA extension?": "Yes" if sa_category(act_flags) and (sol_state in SA_EXT) else "No (general tort)",
        "SOL rule applied": sol_rule_text,
        "SOL End (est.)": sol_end_str,
        "Wagstaff file-by (SOL-45d)": wag_deadline_str,
        "Reported Dates": report_dates_str,
        "Reported to Family/Friends (DateTime)": family_dt_str,
        "Wagstaff Eligible?": "Eligible" if wag_ok else "Not Eligible",
        "Triten Eligible?": "Eligible" if triten_ok else "Not Eligible",
    }
    st.dataframe(pd.DataFrame([decision]), use_container_width=True, height=300)

    # ========= DETAILED REPORT (auto-populated) =========
    st.subheader("Detailed Report — Elements of Statement of the Case for RIDESHARE")
    pickup = st.session_state.get("pickup", "")
    dropoff = st.session_state.get("dropoff", "")
    purpose = st.session_state.get("purpose", "")
    brief = categorical_brief(act_flags)
    elements = f"""1. Date of ride: {fmt_date(incident_date) if incident_date else 'UNKNOWN'}
2. Name of PC: {client_name or 'UNKNOWN'}
3. Reserved a ride with: {company}
4. Pick-up → Drop-off: {pickup or 'UNKNOWN'} → {dropoff or 'UNKNOWN'}
5. Purpose of ride (if needed): {purpose or '—'}
7. Brief/categorical description: {brief}
8. Person/entities PC reported incident: {', '.join(reported_to) if reported_to else '—'}
"""
    st.markdown(f"<div class='copy'>{elements}</div>", unsafe_allow_html=True)

    # ========= EXPORT =========
    st.subheader("Export")
    export_payload = {
        "ClientName": client_name, "Narrative": narr, "Company": company, "State": state,
        "IncidentDate": fmt_date(incident_date) if incident_date else "UNKNOWN",
        "IncidentTime": incident_time.strftime("%H:%M"),
        "Receipt": receipt, "ID": gov_id, "InsideNear": inside_near, "HasAtty": has_atty,
        "FemaleRider": female_rider, "Felony": felony, "DriverWeapon": driver_weapon,
        "ClientCarryingWeapon": client_weapon, "VerbalOnly": verbal_only, "AttemptOnly": attempt_only,
        "Acts_RapePenetration": rape, "Acts_ForcedOralForcedTouch": forced_oral,
        "Acts_TouchingKissing": touching, "Acts_Exposure": exposure, "Acts_Masturbation": masturb,
        "Agg_Kidnap": kidnap, "Agg_Imprison": imprison,
        "SA_Category": category or "—", "SA_Extension_Used": (sol_state in SA_EXT) and bool(category),
        "SOL_Rule_Text": sol_rule_text, "SOL_Years": ("No SOL" if sol_years is None else sol_years),
        "SOL_End": sol_end_str, "Wagstaff_FileBy": wag_deadline_str,
        "ReportedTo": reported_to, "ReportDates": {k: fmt_date(v) for k,v in report_dates.items()},
        "FamilyReportDateTime": fmt_dt(family_report_dt) if family_report_dt else "—",
        "RS_Submit_How": rs_submit_how, "RS_Received_Response": rs_received_response,
        "RS_Response_Detail": rs_response_detail,
        "Eligibility_Wagstaff": "Eligible" if wag_ok else "Not Eligible",
        "Eligibility_Triten": "Eligible" if triten_ok else "Not Eligible",
        "Elements_Report": elements.strip()
    }
    st.download_button(
        "Download CSV (intake + decision + diagnostics + report)",
        data=pd.DataFrame([export_payload]).to_csv(index=False).encode("utf-8"),
        file_name="intake_decision_with_diagnostics.csv",
        mime="text/csv"
    )

render()
