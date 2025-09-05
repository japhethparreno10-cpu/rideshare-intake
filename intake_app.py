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
.big-btn {display:inline-block; padding:14px 18px; margin:6px 8px 0 0; font-size:18px; border-radius:10px; border:none; cursor:pointer;}
.btn-wag {background:#16a34a; color:white;}
.btn-tri {background:#2563eb; color:white;}
.btn-ghost {background:#f3f4f6; color:#111827; border:1px solid #d1d5db;}
[data-testid="stDataFrame"] div, [data-testid="stTable"] div {font-size: 1rem;}
</style>
""", unsafe_allow_html=True)

# =========================
# TODAY (auto-updates)
# =========================
TODAY = datetime.now()

# =========================
# CONSTANTS & LOOKUPS
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

WD_SOL = {
    "Alabama":2,"Alaska":2,"Arizona":2,"Arkansas":3,"California":2,"Colorado":2,"Connecticut":2,"Delaware":2,
    "Florida":2,"Georgia":2,"Hawaii":2,"Idaho":2,"Illinois":2,"Indiana":2,"Iowa":2,"Kansas":2,"Kentucky":1,
    "Louisiana":1,"Maine":6,"Maryland":3,"Massachusetts":3,"Michigan":3,"Minnesota":3,"Mississippi":3,"Missouri":3,
    "Montana":3,"Nebraska":2,"Nevada":2,"New Hampshire":3,"New Jersey":2,"New Mexico":3,"New York":2,
    "North Carolina":2,"North Dakota":6,"Ohio":2,"Oklahoma":2,"Oregon":3,"Pennsylvania":2,"Rhode Island":3,
    "South Carolina":3,"South Dakota":3,"Tennessee":1,"Texas":2,"Utah":2,"Vermont":2,"Virginia":2,"Washington":3,
    "West Virginia":2,"Wisconsin":3,"Wyoming":2
}

SA_EXT = {
    "California":{"rape_penetration":"No SOL","other_touching":"No SOL"},
    "New York":{"rape_penetration":"10 years","other_touching":"10 years"},
    "Texas":{"rape_penetration":"5 years","other_touching":"2 years"},
    "Illinois":{"rape_penetration":"No SOL","other_touching":"2 years"},
    "Connecticut":{"rape_penetration":"No SOL","other_touching":"2 years"},
}

NON_LETHAL_ITEMS = [
    "Pepper Spray - Incapacitates with eye/respiratory irritation",
    "Personal Alarm - Loud noise deterrent",
    "Stun Gun - Electric shock to incapacitate",
    "Taser - Electric darts from a distance",
    "Self-Defense Keychain - Pointed/hard edges",
    "Tactical Flashlight - Disorienting light, striking tool",
    "Groin Kickers - Aid for strikes to sensitive areas",
    "Personal Safety Apps - Emergency alerts/notify authorities",
    "Defense Flares - Signal/deter",
    "Baton - Collapsible, non-lethal strikes",
    "Kubotan - Pressure point tool",
    "Umbrella - Defensive striking tool / create distance",
    "Whistle - Loud alert",
    "Combat Pen - Writing tool & striker",
    "Pocket Knife - Tool that may be used defensively",
    "Personal Baton - Lightweight baton",
    "Nunchaku - Martial arts implement",
    "Flashbang - Loud + bright disorienter",
    "Air Horn - Loud deterrent",
    "Bear Spray - Potent spray defense",
    "Sticky Foam - Temporary immobilization",
    "Tactical Scarf/Shawl - Blocking/striking",
    "Self-Defense Ring - Pointed edge ring",
    "Hearing Protection - Reduces noise distraction"
]

STATES = sorted(set(list(TORT_SOL.keys()) + list(WD_SOL.keys()) + ["D.C."]))

# =========================
# HELPERS
# =========================
def tier_and_aggravators(data):
    t1 = bool(data["Rape/Penetration"] or data["Forced Oral/Forced Touching"])
    t2 = bool(data["Touching/Kissing w/o Consent"] or data["Indecent Exposure"] or data["Masturbation Observed"])
    aggr_kidnap = bool(data["Kidnapping Off-Route w/ Threats"])
    aggr_imprison = bool(data["False Imprisonment w/ Threats"])
    aggr = []
    if aggr_kidnap: aggr.append("Kidnapping w/ threats")
    if aggr_imprison: aggr.append("False imprisonment w/ threats")

    if t1: base = "Tier 1"
    elif t2: base = "Tier 2"
    else: base = "Unclear"

    if base in ("Tier 1","Tier 2") and aggr:
        label = f"{base} (+ Aggravators: {', '.join(aggr)})"
    else:
        label = base
    return label, (base in ("Tier 1","Tier 2") and len(aggr) > 0)

def fmt_date(dt): return dt.strftime("%Y-%m-%d") if dt else "—"
def fmt_dt(dt): return dt.strftime("%Y-%m-%d %H:%M") if dt else "—"
def badge(ok: bool, label: str):
    css = "badge-ok" if ok else "badge-no"
    st.markdown(f"<div class='{css}'>{label}</div>", unsafe_allow_html=True)

# =========================
# STATE: FLOW
# =========================
if "step" not in st.session_state:
    st.session_state.step = "intake"     # intake -> firm_questions
if "selected_firm" not in st.session_state:
    st.session_state.selected_firm = None
if "answers_wag" not in st.session_state:
    st.session_state.answers_wag = {}
if "answers_tri" not in st.session_state:
    st.session_state.answers_tri = {}

# =========================
# REFERENCE
# =========================
st.title("Rideshare Intake Qualifier")
with st.expander("Injury & Sexual Assault: Tiers and State SOL Extensions (Reference)"):
    st.markdown("""
**Tier 1**  
- Rape or sodomy  
- Forcing someone to touch themselves  
- Forcing someone to perform oral sex  

**Tier 2** *(must include touching/kissing category)*  
- Touching/kissing mouth/private parts without consent  
- Indecent exposure (showing private parts inappropriately)  
- Masturbation in front of someone without their consent  

**Tier 3 (Aggravators; requires Tier 1 or Tier 2)**  
- Kidnapping (off intended route) **with clear sexual/extreme physical threats**  
- False imprisonment (driver refuses to stop/locked in) **with clear sexual/extreme physical threats**

**State Sexual Assault SOL Extensions (quick look)**  
- **California:** No SOL for touching of sexual body parts, rape, digital/oral/vaginal/anal penetration  
- **New York:** 10-year SOL for touching of sexual body parts, rape, digital/oral/vaginal/anal penetration  
- **Texas:** 5-year SOL for rape/penetration of mouth/anus/vagina; **2-year** SOL for all other conduct  
- **Illinois:** No SOL for rape/penetration; **2-year** SOL for other conduct  
- **Connecticut:** No SOL for rape/penetration; **2-year** SOL for other conduct
""")

# =========================
# INTAKE & ELIGIBILITY PAGE
# =========================
def render_intake_and_decision():
    st.markdown("<div class='section'></div>", unsafe_allow_html=True)
    st.header("Intake")

    top1, top2, top3 = st.columns([1,1,1])
    with top1:
        client = st.text_input("Client Name", placeholder="e.g., Jane Doe")
    with top2:
        company = st.selectbox("Rideshare company", ["Uber", "Lyft"])
    with top3:
        state = st.selectbox("Incident State", STATES, index=STATES.index("California") if "California" in STATES else 0)

    row2 = st.columns(6)
    with row2[0]:
        female_rider = st.toggle("Female rider", value=True)
    with row2[1]:
        receipt = st.toggle("Receipt provided (email/PDF/app)", value=True)
    with row2[2]:
        gov_id = st.toggle("ID provided", value=True)
    with row2[3]:
        inside_near = st.toggle("Incident inside/just outside/started near car", value=True)
    with row2[4]:
        has_atty = st.toggle("Already has an attorney", value=False)
    with row2[5]:
        incident_time = st.time_input("Incident Time", value=time(21, 0))
    incident_date = st.date_input("Incident Date", value=TODAY.date())

    reported_to = st.multiselect(
        "Reported To (choose all that apply)",
        [
            "Rideshare company","Police","Therapist",
            "Medical professional","Physician","Family/Friends","Audio/Video evidence"
        ], default=["Police"]
    )

    report_dates = {}
    if "Rideshare company" in reported_to:
        report_dates["Rideshare company"] = st.date_input("Date reported to Rideshare company", value=TODAY.date())
    if "Police" in reported_to:
        report_dates["Police"] = st.date_input("Date reported to Police", value=TODAY.date())
    if "Therapist" in reported_to:
        report_dates["Therapist"] = st.date_input("Date reported to Therapist", value=TODAY.date())
    if "Medical professional" in reported_to:
        report_dates["Medical professional"] = st.date_input("Date reported to Medical professional", value=TODAY.date())
    if "Physician" in reported_to:
        report_dates["Physician"] = st.date_input("Date reported to Physician", value=TODAY.date())
    if "Audio/Video evidence" in reported_to:
        report_dates["Audio/Video evidence"] = st.date_input("Date of Audio/Video evidence", value=TODAY.date())

    family_report_dt = None
    if "Family/Friends" in reported_to:
        fr_c1, fr_c2 = st.columns([1,1])
        family_report_date = fr_c1.date_input("Date reported to Family/Friends", value=TODAY.date())
        family_report_time = fr_c2.time_input("Time reported to Family/Friends", value=incident_time)
        family_report_dt = datetime.combine(family_report_date, family_report_time)

    dq1, dq2, dq3 = st.columns([1,1,1])
    with dq1:
        weapon = st.selectbox("Weapon involved?", ["No","Non-lethal defensive (e.g., pepper spray)","Yes"])
    with dq2:
        verbal_only = st.toggle("Verbal abuse only (no sexual contact/acts)", value=False)
    with dq3:
        attempt_only = st.toggle("Attempt/minor contact only", value=False)

    st.subheader("Acts (check what applies)")
    c1, c2 = st.columns(2)
    with c1:
        rape = st.checkbox("Rape/Penetration")
        forced_oral = st.checkbox("Forced Oral/Forced Touching")
        touching = st.checkbox("Touching/Kissing w/o Consent")
    with c2:
        exposure = st.checkbox("Indecent Exposure")
        masturb = st.checkbox("Masturbation Observed")
        kidnap = st.checkbox("Kidnapping Off-Route w/ Threats")
        imprison = st.checkbox("False Imprisonment w/ Threats")
        felony = st.toggle("Client has felony record", value=False)

    st.subheader("Wrongful Death")
    wd_col1, wd_col2 = st.columns([1,2])
    with wd_col1:
        wd = st.toggle("Wrongful Death?", value=False)
    with wd_col2:
        date_of_death = st.date_input("Date of Death", value=TODAY.date()) if wd else None

    # ==== DECISION ====
    st.markdown("<div class='section'></div>", unsafe_allow_html=True)
    st.header("Decision")

    incident_dt = datetime.combine(incident_date, incident_time)
    state_data = {
        "Client Name": client,
        "Female Rider": female_rider,
        "Receipt": receipt,
        "ID": gov_id,
        "InsideNear": inside_near,
        "HasAtty": has_atty,
        "Company": company,
        "State": state,
        "IncidentDateTime": incident_dt,
        "ReportedTo": reported_to,
        "ReportDates": report_dates,
        "FamilyReportDateTime": family_report_dt,
        "Felony": felony,
        "Weapon": weapon,
        "VerbalOnly": verbal_only,
        "AttemptOnly": attempt_only,
        "Rape/Penetration": rape,
        "Forced Oral/Forced Touching": forced_oral,
        "Touching/Kissing w/o Consent": touching,
        "Indecent Exposure": exposure,
        "Masturbation Observed": masturb,
        "Kidnapping Off-Route w/ Threats": kidnap,
        "False Imprisonment w/ Threats": imprison,
        "WrongfulDeath": wd,
        "DateOfDeath": datetime.combine(date_of_death, time(12, 0)) if wd and date_of_death else None
    }

    tier_label, _ = tier_and_aggravators(state_data)
    common_ok = all([female_rider, receipt, gov_id, inside_near, not has_atty])

    sol_years = TORT_SOL.get(state)
    sol_end = incident_dt + relativedelta(years=+int(sol_years)) if sol_years else None
    wagstaff_deadline = (sol_end - timedelta(days=45)) if sol_end else None
    wagstaff_time_ok = (TODAY <= wagstaff_deadline) if wagstaff_deadline else True

    # Triten earliest report <= 14d
    earliest_report_date = None
    all_dates = [d for d in report_dates.values() if d]
    if state_data["FamilyReportDateTime"]:
        all_dates.append(state_data["FamilyReportDateTime"].date())
    if all_dates:
        earliest_report_date = min(all_dates)
    triten_report_ok = (earliest_report_date - incident_dt.date()).days <= 14 if earliest_report_date else False

    # SA note
    sa_note = ""
    if state in SA_EXT and ("Tier 1" in tier_label or "Tier 2" in tier_label):
        if "Tier 1" in tier_label:
            sa_note = f"{state}: rape/penetration SOL = {SA_EXT[state]['rape_penetration']}"
        else:
            sa_note = f"{state}: other touching SOL = {SA_EXT[state]['other_touching']}"

    # WD note
    wd_note = ""
    if wd and state_data["DateOfDeath"] and state in WD_SOL:
        wd_deadline = state_data["DateOfDeath"] + relativedelta(years=+int(WD_SOL[state]))
        wd_note = f"Wrongful Death SOL: {WD_SOL[state]} years → deadline {fmt_date(wd_deadline)}"

    # WAGSTAFF rules
    wag_disq, reported_to_set = [], set(reported_to) if reported_to else set()
    if felony: wag_disq.append("Felony record → Wagstaff requires no felony history")
    if weapon == "Yes": wag_disq.append("Weapon involved → disqualified under Wagstaff")
    if verbal_only: wag_disq.append("Verbal abuse only → does not qualify")
    if attempt_only: wag_disq.append("Attempt/minor contact only → does not qualify")
    if has_atty: wag_disq.append("Already has attorney → cannot intake")

    within_24h_family_ok, missing_family_dt = True, False
    if reported_to_set == {"Family/Friends"}:
        if not state_data["FamilyReportDateTime"]:
            within_24h_family_ok = False; missing_family_dt = True
            wag_disq.append("Family/Friends-only selected but date/time was not provided")
        else:
            delta = state_data["FamilyReportDateTime"] - state_data["IncidentDateTime"]
            within_24h_family_ok = (timedelta(0) <= delta <= timedelta(hours=24))
            if not within_24h_family_ok:
                wag_disq.append("Family/Friends-only report exceeded 24 hours after incident → fails Wagstaff rule")

    base_tier_ok = ("Tier 1" in tier_label) or ("Tier 2" in tier_label)
    wag_ok = common_ok and wagstaff_time_ok and within_24h_family_ok and base_tier_ok and not wag_disq

    # TRITEN rules
    tri_disq = []
    if verbal_only: tri_disq.append("Verbal abuse only → does not qualify")
    if attempt_only: tri_disq.append("Attempt/minor contact only → does not qualify")
    if has_atty: tri_disq.append("Already has attorney → cannot intake")
    if earliest_report_date is None: tri_disq.append("No report date provided for any channel")
    if not triten_report_ok: tri_disq.append("Report not within 2 weeks (based on earliest report date)")
    triten_ok = common_ok and triten_report_ok and base_tier_ok and not tri_disq

    # COMPANY POLICY
    # Triten: Uber & Lyft; Waggy: Uber only; Priority: Triten if both
    company_note = ""; priority_note = ""
    if company == "Uber":
        company_note = "Uber → Waggy (Wagstaff) and Triten"
        if wag_ok and triten_ok:
            priority_note = "Priority: Triten (both eligible)."
    elif company == "Lyft":
        company_note = "Lyft → Triten only"
        if wag_ok:
            wag_ok = False
        if "Company rule: Lyft → Triten only." not in wag_disq:
            wag_disq.append("Company rule: Lyft → Triten only.")

    # BADGES
    b1, b2, b3 = st.columns([1,1,1])
    with b1:
        st.markdown(f"<div class='badge-note'>Tier</div>", unsafe_allow_html=True)
        badge(True, tier_label if tier_label!="Unclear" else "Tier unclear")
    with b2:
        st.markdown(f"<div class='badge-note'>Wagstaff</div>", unsafe_allow_html=True)
        badge(wag_ok, "Eligible" if wag_ok else "Not Eligible")
    with b3:
        st.markdown(f"<div class='badge-note'>Triten</div>", unsafe_allow_html=True)
        badge(triten_ok, "Eligible" if triten_ok else "Not Eligible")

    if company_note: st.info(company_note)
    if priority_note: st.info(priority_note)

    # NOTES
    st.subheader("Eligibility Notes")
    st.markdown("### Wagstaff")
    if wag_ok:
        st.markdown(f"<div class='note-wag'>Meets screen.</div>", unsafe_allow_html=True)
    else:
        reasons = []
        if wag_disq: reasons.extend(wag_disq)
        if not wagstaff_time_ok: reasons.append("Past Wagstaff filing window (must file 45 days before SOL).")
        if reported_to_set == {"Family/Friends"}:
            if missing_family_dt:
                reasons.append("Family/Friends-only selected but date/time was not provided.")
            elif not within_24h_family_ok:
                reasons.append("Family/Friends-only report not within 24 hours of incident.")
        if not base_tier_ok: reasons.append("Tier unclear (select Tier 1 or Tier 2 qualifying acts).")
        if reasons:
            for r in reasons:
                st.markdown(f"<div class='note-wag'>{r}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='note-muted'>No specific reason captured.</div>", unsafe_allow_html=True)

    st.markdown("### Triten")
    if triten_ok:
        st.markdown(f"<div class='note-tri'>Meets screen.</div>", unsafe_allow_html=True)
    else:
        reasons = []
        if tri_disq: reasons.extend(tri_disq)
        if not base_tier_ok: reasons.append("Tier unclear (select Tier 1 or Tier 2 qualifying acts).")
        if reasons:
            for r in reasons:
                st.markdown(f"<div class='note-tri'>{r}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='note-muted'>No specific reason captured.</div>", unsafe_allow_html=True)

    # SUMMARY
    st.subheader("Summary")
    report_dates_str = "; ".join([f"{k}: {fmt_date(v)}" for k, v in report_dates.items()]) if report_dates else "—"
    family_dt_str = fmt_dt(family_report_dt) if family_report_dt else "—"
    decision = {
        "Tier (severity-first)": tier_label,
        "General Tort SOL (yrs)": TORT_SOL.get(state,"—"),
        "SOL End (est.)": fmt_dt(sol_end) if sol_end else "—",
        "Wagstaff file-by (SOL-45d)": fmt_dt(wagstaff_deadline) if wagstaff_deadline else "—",
        "Sexual Assault Extension Note": (sa_note if sa_note else "—"),
        "Reported Dates (by channel)": report_dates_str,
        "Reported to Family/Friends (DateTime)": family_dt_str,
        "Wrongful Death Note": (wd_note if wd_note else "—"),
        "Company Rule": company_note,
        "Priority": (priority_note if priority_note else "—")
    }
    df = pd.DataFrame([decision])
    st.dataframe(df, use_container_width=True, height=400)

    # ======= FIRM SELECTION (NEW) =======
    st.subheader("Next Step: Choose Firm")
    cols = st.columns(3)
    with cols[0]:
        disabled = not wag_ok
        if st.button("Proceed with Wagstaff", type="primary", disabled=disabled, help="Opens Wagstaff question flow", key="btn_wag"):
            st.session_state.selected_firm = "Wagstaff"
            st.session_state.step = "firm_questions"
            st.session_state.latest_decision = decision
            st.session_state.intake_payload = state_data
            st.rerun()
        if disabled:
            st.caption("Wagstaff not eligible based on screening.")
    with cols[1]:
        disabled = not triten_ok
        if st.button("Proceed with Triten", type="primary", disabled=disabled, help="Opens Triten question flow", key="btn_tri"):
            st.session_state.selected_firm = "Triten"
            st.session_state.step = "firm_questions"
            st.session_state.latest_decision = decision
            st.session_state.intake_payload = state_data
            st.rerun()
        if disabled:
            st.caption("Triten not eligible based on screening.")
    with cols[2]:
        st.write("")  # spacer

    # EXPORT (intake + decision)
    st.subheader("Export")
    export_df = pd.concat([pd.DataFrame([state_data]), df], axis=1)
    csv_bytes = export_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV (intake + decision)", data=csv_bytes, file_name="intake_decision.csv", mime="text/csv")

    st.caption("Firm rules: Triten = Uber & Lyft; Waggy = Uber only; Priority = Triten if both eligible. Wagstaff: no felonies, no weapons (non-lethal defensive allowed), no verbal/attempt-only; file 45 days before SOL; Family/Friends-only report must be within 24 hours. Triten: earliest report within 2 weeks.")

# =========================
# FIRM QUESTION FLOWS
# =========================
def render_wagstaff_questions():
    st.header("Wagstaff – Follow-up Questions")
    st.markdown("These questions are specific to Wagstaff. Send me your exact list and I’ll wire them in. For now, here’s a clean scaffold you can use immediately.")

    # --- EXAMPLE PLACEHOLDERS (replace with your real questions) ---
    st.subheader("Incident Details")
    q1 = st.radio("Did the incident involve penetration?", ["No","Yes"], index=0, horizontal=True, key="wag_q1")
    q2 = st.text_area("Brief description (what happened)?", key="wag_q2")
    q3 = st.date_input("Date you first contacted Wagstaff (if applicable)", value=TODAY.date(), key="wag_q3")

    st.subheader("Evidence & Reporting")
    q4 = st.checkbox("Photos or videos available", key="wag_q4")
    q5 = st.text_input("Police Report # (if any)", key="wag_q5")
    q6 = st.file_uploader("Upload any supporting documents (PDF, images)", accept_multiple_files=True, key="wag_files")

    st.subheader("Medical")
    q7 = st.checkbox("Sought medical attention", key="wag_q7")
    q8 = st.text_input("Facility / Physician", key="wag_q8")

    # Save answers in session_state
    st.session_state.answers_wag = {
        "penetration": q1, "description": q2, "first_contact_date": str(q3),
        "media": q4, "police_report_no": q5, "medical": q7, "physician": q8,
        "files_count": len(q6) if q6 else 0
    }

    # Footer controls
    colA, colB, colC = st.columns([1,1,2])
    with colA:
        if st.button("Back", help="Return to intake/eligibility screen"):
            st.session_state.step = "intake"; st.rerun()
    with colB:
        if st.button("Save Answers (CSV)"):
            payload = {
                "firm":"Wagstaff",
                **(st.session_state.intake_payload if "intake_payload" in st.session_state else {}),
                **st.session_state.answers_wag
            }
            df = pd.DataFrame([payload])
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Wagstaff Answers", data=csv_bytes, file_name="wagstaff_followup.csv", mime="text/csv", key="dl_wag_csv")
    with colC:
        st.caption("Once you send the exact questions, I’ll replace the placeholders above 1:1.")

def render_triten_questions():
    st.header("Triten – Follow-up Questions")
    st.markdown("These questions are specific to Triten. Drop me your exact list and I’ll wire them in. This scaffold captures answers and lets you export them.")

    # --- EXAMPLE PLACEHOLDERS (replace with your real questions) ---
    st.subheader("Timeline & Contact")
    q1 = st.date_input("Earliest report date (to any channel)", value=TODAY.date(), key="tri_q1")
    q2 = st.text_input("Rideshare case/incident # (if provided)", key="tri_q2")

    st.subheader("Threats / Aggravators")
    q3 = st.checkbox("Driver made explicit sexual/physical threats", key="tri_q3")
    q4 = st.checkbox("Off-route / False imprisonment", key="tri_q4")

    st.subheader("Damages")
    q5 = st.text_area("Physical or psychological injuries (summary)", key="tri_q5")
    q6 = st.checkbox("Ongoing therapy/treatment", key="tri_q6")

    st.session_state.answers_tri = {
        "earliest_report_date": str(q1), "rs_case_no": q2,
        "threats": q3, "offroute_or_fi": q4,
        "injuries": q5, "therapy": q6
    }

    # Footer controls
    colA, colB, colC = st.columns([1,1,2])
    with colA:
        if st.button("Back", help="Return to intake/eligibility screen"):
            st.session_state.step = "intake"; st.rerun()
    with colB:
        if st.button("Save Answers (CSV)"):
            payload = {
                "firm":"Triten",
                **(st.session_state.intake_payload if "intake_payload" in st.session_state else {}),
                **st.session_state.answers_tri
            }
            df = pd.DataFrame([payload])
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Triten Answers", data=csv_bytes, file_name="triten_followup.csv", mime="text/csv", key="dl_tri_csv")
    with colC:
        st.caption("When you send the exact questions, I’ll swap these placeholders for your real form.")

# =========================
# ROUTER
# =========================
if st.session_state.step == "intake":
    render_intake_and_decision()
elif st.session_state.step == "firm_questions":
    firm = st.session_state.selected_firm
    if firm == "Wagstaff":
        render_wagstaff_questions()
    elif firm == "Triten":
        render_triten_questions()
    else:
        st.warning("No firm selected. Returning to intake."); st.session_state.step="intake"; st.rerun()
