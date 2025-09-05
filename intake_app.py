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
.script {border-left:4px solid #9ca3af; background:#f3f4f6; color:#111827; padding:10px 12px; border-radius:6px; margin:6px 0 14px 0; font-size:0.95rem;}
.small {font-size: 0.9rem; color:#4b5563;}
hr {border:0; border-top:1px solid #e5e7eb; margin:12px 0;}
[data-testid="stDataFrame"] div, [data-testid="stTable"] div {font-size: 1rem;}
</style>
""", unsafe_allow_html=True)

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
STATE_OPTIONS = [
    "Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","Delaware","Florida","Georgia",
    "Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana","Maine","Maryland",
    "Massachusetts","Michigan","Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada","New Hampshire",
    "New Jersey","New Mexico","New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon","Pennsylvania",
    "Rhode Island","South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont","Virginia","Washington",
    "Washington DC","West Virginia","Wisconsin","Wyoming","Puerto Rico"
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
    label = f"{base} (+ Aggravators: {', '.join(aggr)})" if base in ("Tier 1","Tier 2") and aggr else base
    return label, (base in ("Tier 1","Tier 2") and len(aggr) > 0)

def fmt_date(dt): return dt.strftime("%Y-%m-%d") if dt else "—"
def fmt_dt(dt): return dt.strftime("%Y-%m-%d %H:%M") if dt else "—"
def badge(ok: bool, label: str):
    css = "badge-ok" if ok else "badge-no"
    st.markdown(f"<div class='{css}'>{label}</div>", unsafe_allow_html=True)

def script_block(text: str):
    if not text: return
    st.markdown(f"<div class='script'>{text}</div>", unsafe_allow_html=True)

def yesno(label, key, script_yes=None, script_no=None, default="No", horizontal=True):
    if key not in st.session_state:
        st.session_state[key] = default
    val = st.radio(label, ["No","Yes"], key=key, horizontal=horizontal, index=(0 if st.session_state[key]=="No" else 1))
    if val == "Yes" and script_yes: script_block(script_yes)
    if val == "No" and script_no: script_block(script_no)
    return val

def pick(label, options, key, scripts_by_value=None, horizontal=False, default_index=0):
    if key not in st.session_state:
        st.session_state[key] = options[default_index]
    val = st.radio(label, options, key=key, horizontal=horizontal, index=options.index(st.session_state[key]))
    if scripts_by_value and val in scripts_by_value:
        script_block(scripts_by_value[val])
    return val

def init_once(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

# =========================
# SESSION STATE ROOTS
# =========================
init_once("step", "intake")  # intake -> firm_questions
init_once("selected_firm", None)
init_once("answers_wag", {})
init_once("answers_tri", {})

# ---------- Intake keys initialize (defaults) ----------
init_once("in_client", "")
init_once("in_company", "Uber")
init_once("in_state", "California")
init_once("in_female_rider", True)
init_once("in_receipt", True)
init_once("in_gov_id", True)
init_once("in_inside_near", True)
init_once("in_has_atty", False)
init_once("in_incident_time", time(21,0))
init_once("in_incident_date", TODAY.date())

init_once("in_reported_to", ["Police"])
# per-channel dates
for ch in ["Rideshare company","Police","Therapist","Medical professional","Physician","Audio/Video evidence"]:
    init_once(f"in_date_{ch}", TODAY.date())
# family report datetime
init_once("in_family_report_date", TODAY.date())
init_once("in_family_report_time", time(21,0))

# disqualifiers
init_once("in_weapon", "No")
init_once("in_verbal_only", False)
init_once("in_attempt_only", False)

# acts
init_once("in_rape", False)
init_once("in_forced_oral", False)
init_once("in_touching", False)
init_once("in_exposure", False)
init_once("in_masturb", False)
init_once("in_kidnap", False)
init_once("in_imprison", False)
init_once("in_felony", False)

# wrongful death
init_once("in_wd", False)
init_once("in_date_of_death", TODAY.date())

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
- Indecent exposure  
- Masturbation in front of someone without their consent  

**Tier 3 (Aggravators; requires Tier 1 or Tier 2)**  
- Kidnapping (off intended route) with clear sexual/extreme physical threats  
- False imprisonment with clear sexual/extreme physical threats

**State Sexual Assault SOL Extensions (quick look)**  
- CA: No SOL for penetration/touching  
- NY: 10 years penetration/touching  
- TX: 5 years penetration / 2 years other  
- IL: No SOL penetration / 2 years other  
- CT: No SOL penetration / 2 years other
""")

# =========================
# INTAKE & ELIGIBILITY PAGE
# =========================
def render_intake_and_decision():
    st.header("Intake")

    top1, top2, top3 = st.columns([1,1,1])
    with top1:
        st.session_state.in_client = st.text_input("Client Name", value=st.session_state.in_client, key="in_client")
    with top2:
        st.session_state.in_company = st.selectbox("Rideshare company", ["Uber","Lyft"], index=["Uber","Lyft"].index(st.session_state.in_company), key="in_company")
    with top3:
        # ensure index exists
        state_list = STATES
        if st.session_state.in_state not in state_list:
            st.session_state.in_state = "California"
        st.session_state.in_state = st.selectbox("Incident State", state_list, index=state_list.index(st.session_state.in_state), key="in_state")

    row2 = st.columns(6)
    with row2[0]:
        st.session_state.in_female_rider = st.toggle("Female rider", value=st.session_state.in_female_rider, key="in_female_rider")
    with row2[1]:
        st.session_state.in_receipt = st.toggle("Receipt provided (email/PDF/app)", value=st.session_state.in_receipt, key="in_receipt")
    with row2[2]:
        st.session_state.in_gov_id = st.toggle("ID provided", value=st.session_state.in_gov_id, key="in_gov_id")
    with row2[3]:
        st.session_state.in_inside_near = st.toggle("Incident inside/just outside/started near car", value=st.session_state.in_inside_near, key="in_inside_near")
    with row2[4]:
        st.session_state.in_has_atty = st.toggle("Already has an attorney", value=st.session_state.in_has_atty, key="in_has_atty")
    with row2[5]:
        st.session_state.in_incident_time = st.time_input("Incident Time", value=st.session_state.in_incident_time, key="in_incident_time")
    st.session_state.in_incident_date = st.date_input("Incident Date", value=st.session_state.in_incident_date, key="in_incident_date")

    st.session_state.in_reported_to = st.multiselect(
        "Reported To (choose all that apply)",
        ["Rideshare company","Police","Therapist","Medical professional","Physician","Family/Friends","Audio/Video evidence"],
        default=st.session_state.in_reported_to,
        key="in_reported_to"
    )

    # channel dates
    report_dates = {}
    if "Rideshare company" in st.session_state.in_reported_to:
        st.session_state.in_date_Rideshare_company = st.date_input("Date reported to Rideshare company", value=st.session_state.in_date_Rideshare_company, key="in_date_Rideshare company")
        report_dates["Rideshare company"] = st.session_state["in_date_Rideshare company"]
    if "Police" in st.session_state.in_reported_to:
        st.session_state.in_date_Police = st.date_input("Date reported to Police", value=st.session_state.in_date_Police, key="in_date_Police")
        report_dates["Police"] = st.session_state.in_date_Police
    if "Therapist" in st.session_state.in_reported_to:
        st.session_state.in_date_Therapist = st.date_input("Date reported to Therapist", value=st.session_state.in_date_Therapist, key="in_date_Therapist")
        report_dates["Therapist"] = st.session_state.in_date_Therapist
    if "Medical professional" in st.session_state.in_reported_to:
        st.session_state.in_date_Medical_professional = st.date_input("Date reported to Medical professional", value=st.session_state.in_date_Medical_professional, key="in_date_Medical professional")
        report_dates["Medical professional"] = st.session_state["in_date_Medical professional"]
    if "Physician" in st.session_state.in_reported_to:
        st.session_state.in_date_Physician = st.date_input("Date reported to Physician", value=st.session_state.in_date_Physician, key="in_date_Physician")
        report_dates["Physician"] = st.session_state.in_date_Physician
    if "Audio/Video evidence" in st.session_state.in_reported_to:
        st.session_state.in_date_Audio_Video_evidence = st.date_input("Date of Audio/Video evidence", value=st.session_state.in_date_Audio_Video_evidence, key="in_date_Audio/Video evidence")
        report_dates["Audio/Video evidence"] = st.session_state["in_date_Audio/Video evidence"]

    family_report_dt = None
    if "Family/Friends" in st.session_state.in_reported_to:
        fr_c1, fr_c2 = st.columns([1,1])
        st.session_state.in_family_report_date = fr_c1.date_input("Date reported to Family/Friends", value=st.session_state.in_family_report_date, key="in_family_report_date")
        st.session_state.in_family_report_time = fr_c2.time_input("Time reported to Family/Friends", value=st.session_state.in_family_report_time, key="in_family_report_time")
        family_report_dt = datetime.combine(st.session_state.in_family_report_date, st.session_state.in_family_report_time)

    dq1, dq2, dq3 = st.columns([1,1,1])
    with dq1:
        st.session_state.in_weapon = st.selectbox("Weapon involved?", ["No","Non-lethal defensive (e.g., pepper spray)","Yes"], index=["No","Non-lethal defensive (e.g., pepper spray)","Yes"].index(st.session_state.in_weapon), key="in_weapon")
    with dq2:
        st.session_state.in_verbal_only = st.toggle("Verbal abuse only (no sexual contact/acts)", value=st.session_state.in_verbal_only, key="in_verbal_only")
    with dq3:
        st.session_state.in_attempt_only = st.toggle("Attempt/minor contact only", value=st.session_state.in_attempt_only, key="in_attempt_only")

    st.subheader("Acts (check what applies)")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.in_rape = st.checkbox("Rape/Penetration", value=st.session_state.in_rape, key="in_rape")
        st.session_state.in_forced_oral = st.checkbox("Forced Oral/Forced Touching", value=st.session_state.in_forced_oral, key="in_forced_oral")
        st.session_state.in_touching = st.checkbox("Touching/Kissing w/o Consent", value=st.session_state.in_touching, key="in_touching")
    with c2:
        st.session_state.in_exposure = st.checkbox("Indecent Exposure", value=st.session_state.in_exposure, key="in_exposure")
        st.session_state.in_masturb = st.checkbox("Masturbation Observed", value=st.session_state.in_masturb, key="in_masturb")
        st.session_state.in_kidnap = st.checkbox("Kidnapping Off-Route w/ Threats", value=st.session_state.in_kidnap, key="in_kidnap")
        st.session_state.in_imprison = st.checkbox("False Imprisonment w/ Threats", value=st.session_state.in_imprison, key="in_imprison")
        st.session_state.in_felony = st.toggle("Client has felony record", value=st.session_state.in_felony, key="in_felony")

    st.subheader("Wrongful Death")
    wd_col1, wd_col2 = st.columns([1,2])
    with wd_col1:
        st.session_state.in_wd = st.toggle("Wrongful Death?", value=st.session_state.in_wd, key="in_wd")
    with wd_col2:
        if st.session_state.in_wd:
            st.session_state.in_date_of_death = st.date_input("Date of Death", value=st.session_state.in_date_of_death, key="in_date_of_death")

    # ==== DECISION ====
    st.header("Decision")

    incident_dt = datetime.combine(st.session_state.in_incident_date, st.session_state.in_incident_time)
    state_data = {
        "Client Name": st.session_state.in_client,
        "Female Rider": st.session_state.in_female_rider,
        "Receipt": st.session_state.in_receipt,
        "ID": st.session_state.in_gov_id,
        "InsideNear": st.session_state.in_inside_near,
        "HasAtty": st.session_state.in_has_atty,
        "Company": st.session_state.in_company,
        "State": st.session_state.in_state,
        "IncidentDateTime": incident_dt,
        "ReportedTo": st.session_state.in_reported_to,
        "ReportDates": report_dates,
        "FamilyReportDateTime": family_report_dt,
        "Felony": st.session_state.in_felony,
        "Weapon": st.session_state.in_weapon,
        "VerbalOnly": st.session_state.in_verbal_only,
        "AttemptOnly": st.session_state.in_attempt_only,
        "Rape/Penetration": st.session_state.in_rape,
        "Forced Oral/Forced Touching": st.session_state.in_forced_oral,
        "Touching/Kissing w/o Consent": st.session_state.in_touching,
        "Indecent Exposure": st.session_state.in_exposure,
        "Masturbation Observed": st.session_state.in_masturb,
        "Kidnapping Off-Route w/ Threats": st.session_state.in_kidnap,
        "False Imprisonment w/ Threats": st.session_state.in_imprison,
        "WrongfulDeath": st.session_state.in_wd,
        "DateOfDeath": datetime.combine(st.session_state.in_date_of_death, time(12,0)) if st.session_state.in_wd else None
    }

    tier_label, _ = tier_and_aggravators(state_data)
    common_ok = all([
        st.session_state.in_female_rider,
        st.session_state.in_receipt,
        st.session_state.in_gov_id,
        st.session_state.in_inside_near,
        not st.session_state.in_has_atty
    ])

    sol_years = TORT_SOL.get(st.session_state.in_state)
    sol_end = incident_dt + relativedelta(years=+int(sol_years)) if sol_years else None
    wagstaff_deadline = (sol_end - timedelta(days=45)) if sol_end else None
    wagstaff_time_ok = (TODAY <= wagstaff_deadline) if wagstaff_deadline else True

    # Triten earliest report <= 14d
    earliest_report_date = None
    all_dates = [d for d in report_dates.values() if d]
    if state_data["FamilyReportDateTime"]: all_dates.append(state_data["FamilyReportDateTime"].date())
    if all_dates: earliest_report_date = min(all_dates)
    triten_report_ok = (earliest_report_date - incident_dt.date()).days <= 14 if earliest_report_date else False

    # WAGSTAFF rules
    wag_disq, reported_to_set = [], set(st.session_state.in_reported_to) if st.session_state.in_reported_to else set()
    if st.session_state.in_felony: wag_disq.append("Felony record → Wagstaff requires no felony history")
    if st.session_state.in_weapon == "Yes": wag_disq.append("Weapon involved → disqualified under Wagstaff")
    if st.session_state.in_verbal_only: wag_disq.append("Verbal abuse only → does not qualify")
    if st.session_state.in_attempt_only: wag_disq.append("Attempt/minor contact only → does not qualify")
    if st.session_state.in_has_atty: wag_disq.append("Already has attorney → cannot intake")

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
    if st.session_state.in_verbal_only: tri_disq.append("Verbal abuse only → does not qualify")
    if st.session_state.in_attempt_only: tri_disq.append("Attempt/minor contact only → does not qualify")
    if earliest_report_date is None: tri_disq.append("No report date provided for any channel")
    if not triten_report_ok: tri_disq.append("Report not within 2 weeks (based on earliest report date)")
    if st.session_state.in_has_atty: tri_disq.append("Already has attorney → cannot intake")
    triten_ok = common_ok and triten_report_ok and base_tier_ok and not tri_disq

    # COMPANY POLICY: Triten (Uber & Lyft); Waggy (Uber only); Priority Triten if both
    company_note = ""; priority_note = ""
    if st.session_state.in_company == "Uber":
        company_note = "Uber → Waggy (Wagstaff) and Triten"
        if wag_ok and triten_ok:
            priority_note = "Priority: Triten (both eligible)."
    elif st.session_state.in_company == "Lyft":
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
        "General Tort SOL (yrs)": TORT_SOL.get(st.session_state.in_state,"—"),
        "SOL End (est.)": fmt_dt(sol_end) if sol_end else "—",
        "Wagstaff file-by (SOL-45d)": fmt_dt(wagstaff_deadline) if wagstaff_deadline else "—",
        "Reported Dates (by channel)": report_dates_str,
        "Reported to Family/Friends (DateTime)": family_dt_str,
        "Company Rule": company_note,
        "Priority": (priority_note if priority_note else "—")
    }
    df = pd.DataFrame([decision])
    st.dataframe(df, use_container_width=True, height=380)

    # ======= FIRM SELECTION =======
    st.subheader("Next Step: Choose Firm")
    cols = st.columns(3)
    with cols[0]:
        disabled = not wag_ok
        if st.button("Proceed with Wagstaff", type="primary", disabled=disabled, key="btn_wag"):
            st.session_state.selected_firm = "Wagstaff"
            st.session_state.step = "firm_questions"
            st.session_state.latest_decision = decision
            st.session_state.intake_payload = state_data
            st.experimental_rerun()
        if disabled:
            st.caption("Wagstaff not eligible based on screening.")
    with cols[1]:
        disabled = not triten_ok
        if st.button("Proceed with Triten", type="primary", disabled=disabled, key="btn_tri"):
            st.session_state.selected_firm = "Triten"
            st.session_state.step = "firm_questions"
            st.session_state.latest_decision = decision
            st.session_state.intake_payload = state_data
            st.experimental_rerun()
        if disabled:
            st.caption("Triten not eligible based on screening.")

    st.subheader("Export")
    export_df = pd.concat([pd.DataFrame([state_data]), df], axis=1)
    csv_bytes = export_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV (intake + decision)", data=csv_bytes, file_name="intake_decision.csv", mime="text/csv")

    st.caption("Firm rules: Triten = Uber & Lyft; Waggy = Uber only; Priority = Triten if both eligible. Wagstaff: Family/Friends-only report must be within 24h; file 45 days before SOL; no felonies, no weapons (non-lethal defensive OK). Triten: earliest report within 2 weeks.")

# =========================
# WAGSTAFF QUESTIONS (live scripts)
# =========================
def render_wagstaff_questions():
    st.header("Wagstaff – Detailed Questionnaire")
    st.caption("Scripts change instantly based on Yes/No selections.")

    # minimal example content; your full question set from the previous version remains available
    # (omitted here to keep focus on persistence fix).
    # Use Back to Intake to verify persistence.

    if st.button("Back to Intake"):
        st.session_state.step = "intake"
        st.experimental_rerun()

    st.info("Navigate back with the button above. Intake entries will remain intact.")

# =========================
# TRITEN PLACEHOLDER
# =========================
def render_triten_questions():
    st.header("Triten – Follow-up Questions (placeholder)")

    if st.button("Back to Intake"):
        st.session_state.step = "intake"
        st.experimental_rerun()

    st.info("Navigate back with the button above. Intake entries will remain intact.")

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
        st.warning("No firm selected. Returning to intake.")
        st.session_state.step = "intake"
        st.experimental_rerun()
