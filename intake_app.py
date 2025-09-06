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
# Normalize common DC labels for SOL lookups
STATE_ALIAS = {"Washington DC": "D.C.", "District of Columbia": "D.C."}

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

# reusable scripted radios
def yesno(label, key, script_yes=None, script_no=None, default="No"):
    options = ["No","Yes"]
    index = 0 if default == "No" else 1
    val = st.radio(label, options, horizontal=True, key=key, index=index)
    if val == "Yes" and script_yes:
        script_block(script_yes)
    if val == "No" and script_no:
        script_block(script_no)
    return val

def pick(label, options, key, scripts_by_value=None, horizontal=False, index=0):
    val = st.radio(label, options, horizontal=horizontal, key=key, index=index)
    if scripts_by_value and val in scripts_by_value:
        script_block(scripts_by_value[val])
    return val

def validate_inputs(incident_dt, earliest_report_date, family_report_dt):
    issues = []
    if earliest_report_date and earliest_report_date < incident_dt.date():
        issues.append("Earliest report date is before the incident date. Please double-check.")
    return issues

# =========================
# SESSION STATE
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
    st.header("Decision")

    incident_dt = datetime.combine(incident_date, incident_time)
    state_data = {
        "Client Name": client, "Female Rider": female_rider, "Receipt": receipt, "ID": gov_id,
        "InsideNear": inside_near, "HasAtty": has_atty, "Company": company, "State": state,
        "IncidentDateTime": incident_dt, "ReportedTo": reported_to, "ReportDates": report_dates,
        "FamilyReportDateTime": family_report_dt, "Felony": felony, "Weapon": weapon,
        "VerbalOnly": verbal_only, "AttemptOnly": attempt_only,
        "Rape/Penetration": rape, "Forced Oral/Forced Touching": forced_oral,
        "Touching/Kissing w/o Consent": touching, "Indecent Exposure": exposure,
        "Masturbation Observed": masturb, "Kidnapping Off-Route w/ Threats": kidnap,
        "False Imprisonment w/ Threats": imprison, "WrongfulDeath": wd,
        "DateOfDeath": datetime.combine(date_of_death, time(12, 0)) if wd and date_of_death else None
    }

    tier_label, _ = tier_and_aggravators(state_data)
    common_ok = all([female_rider, receipt, gov_id, inside_near, not has_atty])

    # SOL + Wagstaff timing (with DC alias)
    sol_lookup_state = STATE_ALIAS.get(state, state)
    sol_years = TORT_SOL.get(sol_lookup_state)
    if sol_years:
        sol_end = incident_dt + relativedelta(years=+int(sol_years))
        wagstaff_deadline = sol_end - timedelta(days=45)
        wagstaff_time_ok = TODAY <= wagstaff_deadline
    else:
        sol_end = None
        wagstaff_deadline = None
        wagstaff_time_ok = True

    # Triten earliest report <= 14d (guard against negatives)
    earliest_report_date = None
    all_dates = [d for d in report_dates.values() if d]
    if state_data["FamilyReportDateTime"]: all_dates.append(state_data["FamilyReportDateTime"].date())
    if all_dates: earliest_report_date = min(all_dates)
    delta_days = (earliest_report_date - incident_dt.date()).days if earliest_report_date else None
    triten_report_ok = (delta_days is not None) and (0 <= delta_days <= 14)

    # Basic validation warnings
    for msg in validate_inputs(incident_dt, earliest_report_date, family_report_dt):
        st.warning(msg)

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
    if earliest_report_date is None: tri_disq.append("No report date provided for any channel")
    if not triten_report_ok: tri_disq.append("Report not within 2 weeks (based on earliest report date)")
    if has_atty: tri_disq.append("Already has attorney → cannot intake")
    triten_ok = common_ok and triten_report_ok and base_tier_ok and not tri_disq

    # COMPANY POLICY
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
        "General Tort SOL (yrs)": TORT_SOL.get(sol_lookup_state,"—"),
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
            st.rerun()
        if disabled:
            st.caption("Wagstaff not eligible based on screening.")
    with cols[1]:
        disabled = not triten_ok
        if st.button("Proceed with Triten", type="primary", disabled=disabled, key="btn_tri"):
            st.session_state.selected_firm = "Triten"
            st.session_state.step = "firm_questions"
            st.session_state.latest_decision = decision
            st.session_state.intake_payload = state_data
            st.rerun()
        if disabled:
            st.caption("Triten not eligible based on screening.")

    st.subheader("Export")
    export_df = pd.concat([pd.DataFrame([state_data]), df], axis=1)
    csv_bytes = export_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV (intake + decision)", data=csv_bytes, file_name="intake_decision.csv", mime="text/csv")

    st.caption("Firm rules: Triten = Uber & Lyft; Waggy = Uber only; Priority = Triten if both eligible. Wagstaff: Family/Friends-only report must be within 24h; file 45 days before SOL; no felonies, no weapons (non-lethal defensive OK). Triten: earliest report within 2 weeks.")

# =========================
# WAGSTAFF QUESTION FLOW – NO FORM (LIVE SCRIPTS)
# =========================
def render_wagstaff_questions():
    st.header("Wagstaff – Detailed Questionnaire")
    st.caption("Scripts below change instantly based on your Yes/No selections.")

    # 1–4 Narrative
    st.subheader("1–4. Narrative")
    s1 = st.text_area("1. Statement of the Case:")
    s2 = st.text_area("2. Burden:")
    s3 = st.text_area("3. Icebreaker:")
    s4 = st.text_area("4. Comments:")

    # CLIENT CONTACT (5–18)
    st.markdown("---")
    st.subheader("CLIENT CONTACT DETAILS")
    ccols = st.columns([1,1,1])
    with ccols[0]:
        c_first = st.text_input("5. Client Name (First Name)")
    with ccols[1]:
        c_middle = st.text_input("5. Client Name (Middle Name)")
    with ccols[2]:
        c_last = st.text_input("5. Client Name (Last Name)")
    c_email = st.text_input("6. Primary Email:")
    c_addr = st.text_input("7. Mailing Address:")
    c_city = st.text_input("8. City:")
    c_state = st.selectbox("9. State:", STATE_OPTIONS, index=(STATE_OPTIONS.index("Georgia") if "Georgia" in STATE_OPTIONS else 0))
    c_zip = st.text_input("10. Zip:")
    c_home = st.text_input("11. Home Phone No.:", placeholder="+1 (###) ###-####")
    c_cell = st.text_input("12. Cell Phone No.:", placeholder="(214) 550-0063")
    c_best_time = st.text_input("13. Best Time to Contact:")
    c_pref_method = st.text_input("14. Preferred Method of Contact:")
    c_dob = st.date_input("15. Date of Birth (mm-dd-yyyy):", value=TODAY.date())
    c_ssn = st.text_input("16. Social Security No.:", placeholder="000-00-0000")
    c_claim_for = st.radio("17. Does the claim pertain to you or another person?", ["Myself","Someone Else"], horizontal=True)
    c_prev_firm = st.text_area("18. ...disqualified for any reason? (details)")

    # INJURED PARTY (19–27)
    st.markdown("---")
    st.subheader("INJURED PARTY DETAILS")
    ip_name = st.text_input("19. Injured/Deceased Party's Full Name (First, Middle, & Last Name):")
    ip_gender = st.text_input("20. Injured Party Gender")
    ip_dob = st.date_input("21. Injured/Deceased Party's DOB (mm-dd-yyyy):", value=TODAY.date())
    ip_ssn = st.text_input("22. Injured/Deceased Party's SS#: ", placeholder="000-00-0000")
    ip_relationship = st.text_input("23. PC's Relationship to Injured/Deceased:")
    ip_title = st.multiselect("24. Title to Represent:", ["Executor","Conservator","Parent","Administrator","Legal Guardian","Other Agent","Trustee","Power of Attorney"])
    ip_has_poa = st.radio("25. Does caller have POA or other legal authority?", ["Yes","No"], horizontal=True)
    ip_has_proof = st.radio("26. Does caller have proof of legal authority?", ["Yes","No"], horizontal=True)
    ip_reason_no_discuss = st.selectbox("27. Reason PC cannot discuss case:", ["Select","Minor","Incapacitated","Death","Other"])

    # DEATH (28–33)
    st.markdown("IF INJURED CLAIMANT DIED:  (Please provide copy of Death Certificate to Paralegal When Confirming Details)")
    is_deceased = st.radio("28. Is the client deceased?", ["No","Yes"], horizontal=True)
    dod = st.date_input("29. Date of Death (if applies):", value=TODAY.date()) if is_deceased=="Yes" else None
    cod = st.text_input("30. Cause of Death on Death Cert:") if is_deceased=="Yes" else ""
    death_state = st.selectbox("31. In what state did the death occur?", STATE_OPTIONS) if is_deceased=="Yes" else ""
    has_death_cert = st.radio("32. Do you have a death certificate?", ["Yes","No"], horizontal=True) if is_deceased=="Yes" else "No"
    right_to_claim_docs = st.text_area("33. Documentation of your right to the decedent’s claim?")

    # EMERGENCY CONTACT (34–37)
    st.markdown("---")
    st.subheader("ALTERNATE  / EMERGENCY CONTACT DETAILS")
    ec_name = st.text_input("34. Alternate / Emergency Contact First & Last Name")
    ec_relation = st.text_input("35. Alternate / Emergency Contact Relation to Client")
    ec_phone = st.text_input("36. Alternate / Emergency Contact Number", placeholder="+1 (###) ###-####")
    ec_email = st.text_input("37. Alternate / Emergency Contact Email")

    # INCIDENT (38–51) – dynamic scripts
    st.markdown("---")
    st.subheader("INCIDENT DETAILS")

    was_driver_or_rider = pick(
        "38. Were you the driver or rider during this incident?",
        ["Driver","Rider"],
        key="q38",
        horizontal=True,
        scripts_by_value={
            "Rider": "If Rider: Okay, you were the rider. Thank you for clarifying that — this helps us understand who had control of the vehicle.",
            "Driver": "If Driver: Okay. You were the driver — thank you for sharing that. Unfortunately, the law firm is not currently taking cases where the driver was assaulted. I’m really sorry we cannot help you."
        }
    )

    incident_narr = st.text_area(
        '39. Describe what happened (purpose of ride, location type, seat, stopped/moving, etc.).'
    )
    script_block('Agent Response: Thank you for sharing that with me. You said "[mirror key words]" — and that sounds incredibly difficult. This space is confidential.')

    has_incident_date = pick("40. Do you have the Date the incident occurred?", ["No","Yes"], key="q40", horizontal=True)
    if has_incident_date == "Yes":
        incident_date_known = st.date_input("40.a Select date", value=TODAY.date())
        script_block("Agent Response: Got it. The date was [repeat date]. The timing helps link the trip and incident.")
    else:
        incident_date_known = None

    rs_company = st.selectbox("41. Which Rideshare company did you use?", ["Uber","Lyft","Other"])
    script_block("Agent Response: [Rideshare company name], got it. That helps determine responsibility and operator.")

    us_occurrence = pick("42. Did the incident occur within the United States?", ["Yes","No"], key="q42", horizontal=True)

    incident_state = st.selectbox("43. What state did this happen?", STATE_OPTIONS)
    script_block("Agent Response: Okay. [Repeat state]. Thank you.")

    pickup_addr = st.text_input("44. Pick-up location (full address)")
    script_block("Agent Response: Picked up from [repeat location]. Every detail helps validate what happened.")

    dropoff_addr = st.text_input("45. Drop-off location (full address)")
    script_block("Agent Response: Dropped off at [location]. Helpful for trip details.")

    sexually_assaulted = yesno(
        "46. Were you sexually assaulted or inappropriately touched by the Rideshare driver?",
        key="q46",
        script_yes="Okay, I’m really sorry to hear you were [repeat details]. It’s incredibly brave to talk about it. Thank you for trusting us.",
        script_no="Thank you for clarifying. We’ll continue neutrally and document everything carefully."
    )

    fi_kidnapping = yesno(
        "47. False imprisonment or kidnapping with overt/physical threats?",
        key="q47",
        script_yes="That sounds terrifying – you mentioned [repeat acts]. We want the firm to understand the seriousness.",
        script_no="Thank you. We’ll continue through the next questions."
    )

    verbal_harassment = yesno(
        "48. Were you subjected to verbal harassment?",
        key="q48",
        script_yes="Understood—you did experience verbal harassment. Those moments are serious and deserve to be heard.",
        script_no="Thank you for clarifying. We’ll proceed."
    )

    inside_or_near = yesno(
        "49. Did the incident occur while using the Rideshare service (inside/just outside the vehicle)?",
        key="q49",
        script_yes="Okay. It happened while using the service. That helps confirm scope of responsibility for safe transport.",
        script_no="Understood. We’ll note the location context accordingly."
    )

    driver_weapon = st.text_area("50. Driver used/threatened weapon or force (gun, knife, choking)? If yes, elaborate.")
    if driver_weapon.strip():
        script_block("Okay, [repeat weapon/force]. That’s very serious and helps paint the full picture. I’m sorry that happened.")
    else:
        script_block("No weapon reported. Still a very serious situation; this does not lessen the magnitude.")

    client_weapon = yesno(
        "51. Were you carrying a weapon at the time? (Non-lethal defense like pepper spray may not be a weapon)",
        key="q51",
        script_yes="Thank you for your honesty. Based on current guidelines, the firm may not accept cases where the victim had a weapon.",
        script_no="You did not have a weapon. That’s all we need on that part — thank you."
    )

    # REPORTING & TREATMENT (52–61) dynamic
    st.markdown("---")
    st.subheader("REPORTING & TREATMENT DETAILS")

    has_receipt = yesno(
        "52. Are you able to reproduce the Rideshare receipt (email/app/PDF)?",
        key="q52",
        script_yes="Great—you can obtain the receipt. It’s one of the most important proofs linking the trip to the incident.",
        script_no="Understood. The receipt is critical. Please check email/app; we can provide instructions for retrieving it."
    )

    reported_channels = st.multiselect(
        "53. Did you report the incident to anyone?",
        ["Rideshare Company","Physician","Friend or Family Member","Therapist","Police Department","NO (DQ, UNLESS TIER 1 OR MINOR)"]
    )
    if reported_channels:
        script_block("Okay, you reported to [repeat answer]. That shows you sought help and can support the case.")
    else:
        script_block("You didn’t tell anyone—this can make it harder to pursue. We may need to review with a supervisor.")

    rs_submit_how = st.text_input("54. If reported to Rideshare: how did you submit (email/app)?")
    if rs_submit_how.strip():
        script_block("You submitted via [email/app]. Either method is fine—thank you for sharing.")

    willing_to_report = pick(
        "55. If not yet reported to Rideshare: would you be willing to if the firm recommends it?",
        ["Yes","No","Unsure"], key="q55", horizontal=True,
        scripts_by_value={
            "Yes":"Thank you—being open to reporting can really help support the case.",
            "No":"Totally understandable. If the firm thinks it’s important later, they’ll walk you through it step by step.",
            "Unsure":"Completely fine to be unsure. If needed later, the firm will guide you."
        }
    )

    rs_received_response = yesno(
        "56. Did you receive a response from Uber or Lyft?",
        key="q56",
        script_yes="Got it—they responded. Please forward any emails or app messages you received.",
        script_no="They did not respond. That’s frustrating—we’ll document that."
    )

    report_contact_info = st.text_area("57. Contact info for the person you reported to (Name, Relation, Address, Phone, Date)")
    if report_contact_info.strip():
        script_block("Okay, you reported to [repeat answer]. We’ll note that carefully.")

    st.markdown("**IF PC CALLED UBER OR LYFT**")
    st.caption("Many survivors try different ways to reach Uber; options aren’t always clear.")

    where_found_number = st.text_input("58. Where did you find the phone number you called?")
    if where_found_number.strip():
        script_block('Thanks. Many people find numbers online or in emails. You found it via [source]—that helps.')

    got_case_number = yesno(
        "59. Did you receive any confirmation or case number from the call?",
        key="q59",
        script_yes='Got it—that helps us track whether Uber created an internal file.',
        script_no='Understood—many callers don’t receive one. We’ll document that.'
    )

    who_answered = st.text_input("60. Who answered—did they say they were with Uber/Lyft, or just took info?")
    if who_answered.strip():
        script_block('Okay—they answered and you said they [repeat answer]. Others have reported similar uncertainty; noted.')

    follow_up_after_call = st.text_area("61. Any follow-up after the call (email/app message/instructions)?")
    if follow_up_after_call.strip():
        script_block('Thanks—you were told to [repeat answer]. Many report unclear guidance; you’re not alone.')
    else:
        script_block('No follow-up received—understood. Many have reported the same experience.')

    # MEDICAL (62–68)
    st.markdown("---")
    st.subheader("MEDICAL TREATMENT DETAILS")
    forms_signed_for_records = st.text_input("62. Signed any forms authorizing release of medical records? (who?)")
    med_treated = pick("63. Received medical treatment for physical injuries?", ["Yes","No"], key="q63", horizontal=True)
    med_treatment_desc = st.text_area("64. Describe medical treatment:")
    med_doctor = st.text_input("65. Doctor who diagnosed you:")
    med_facility = st.text_input("66. Hospital/Facility of diagnosis:")
    med_address = st.text_input("67. Facility/Doctor Address:")
    med_phone = st.text_input("68. Facility/Doctor Phone:", placeholder="+1 (###) ###-####")

    # MH1 (69–77)
    st.markdown("---")
    st.subheader("MENTAL HEALTH TREATMENT DETAILS 1")
    mh1_yes = pick("69. Any mental health treatment related to the assault?", ["Yes","No"], key="q69", horizontal=True)
    mh1_desc = st.text_area("70. Describe mental health treatment (general):")
    mh1_doctor = st.text_input("71. Treating doctor:")
    mh1_hospital = st.text_input("72. Hospital:")
    mh1_address = st.text_input("73. Hospital Address:")
    mh1_phone = st.text_input("74. Hospital Phone:", placeholder="+1 (###) ###-####")
    mh1_website = st.text_input("75. Hospital Website:")
    mh1_diagnosis = st.text_input("76. Diagnosis / Dates:")
    mh1_treatment = st.text_area("77. Treatment Type / Dates (detail):")

    # MH2 (78–86)
    st.markdown("---")
    st.subheader("MENTAL HEALTH TREATMENT DETAILS 2")
    mh2_yes = pick("78. Any mental health treatment related to the assault? (second entry)", ["Yes","No"], key="q78", horizontal=True)
    mh2_desc = st.text_area("79. Describe treatment (general):")
    mh2_doctor = st.text_input("80. Doctor:")
    mh2_hospital = st.text_input("81. Hospital:")
    mh2_address = st.text_input("82. Hospital Address:")
    mh2_phone = st.text_input("83. Hospital Phone:")
    mh2_website = st.text_input("84. Hospital Website:")
    mh2_diagnosis = st.text_input("85. Diagnosis / Dates:")
    mh2_treatment = st.text_area("86. Treatment Type / Dates (detail):")

    # ADDITIONAL PROVIDERS (87–94)
    st.markdown("---")
    st.subheader("ADDITIONAL RELEVANT MEDICAL OR MENTAL HEALTH PROVIDERS")
    am_name = st.text_input("87. Doctor/ Facility Name:")
    am_address = st.text_input("88. Address:")
    am_phone = st.text_input("89. Phone Number:")
    am_website = st.text_input("90. Website Address")
    am_diagnosis = st.text_input("91. Diagnosed Ailment / Diagnosis Date(s):")
    am_symptoms = st.text_input("92. Symptom(s):")
    am_treatment = st.text_input("93. Treatment Type / Treatment Date(s):")
    am_comments = st.text_area("94. Comments:")

    # PHARMACY (95–103)
    st.markdown("---")
    st.subheader("PHARMACY FOR MEDICATIONS")
    ph_name = st.text_input("95. Name:")
    ph_phone = st.text_input("96. Phone:")
    ph_website = st.text_input("97. Website:")
    ph_address = st.text_input("98. Full Street, City, Zip Address:")
    ph_med1 = st.text_input("99. Ailment / Medication / Dates Prescribed:")
    ph_med2 = st.text_input("100. Ailment / Medication / Dates Prescribed:")
    ph_comments = st.text_area("101. Comments:")
    ph_med3 = st.text_input("102. Ailment / Medication / Date Prescribed:")

    affirm = pick("103. Affirm all answers are true and correct (incl. prior firm signup)?", ["Yes","No"], key="q103", horizontal=True)

    # TECH (104–105)
    st.markdown("---")
    st.subheader("INTAKE ENDS HERE")
    ip_addr = st.text_input("104. IP Address")
    jornaya = st.text_area("105. Trusted Form/Jornaya Data")

    if st.button("Save Wagstaff Answers"):
        st.session_state.answers_wag = {
            # 1–4
            "1_statement_of_case": s1, "2_burden": s2, "3_icebreaker": s3, "4_comments": s4,
            # 5–18 Client
            "5_first": c_first, "5_middle": c_middle, "5_last": c_last,
            "6_email": c_email, "7_addr": c_addr, "8_city": c_city, "9_state": c_state,
            "10_zip": c_zip, "11_home": c_home, "12_cell": c_cell, "13_best_time": c_best_time,
            "14_pref_contact": c_pref_method, "15_dob": str(c_dob), "16_ssn": c_ssn,
            "17_claim_for": c_claim_for, "18_prev_firm": c_prev_firm,
            # 19–27 Injured Party
            "19_ip_name": ip_name, "20_ip_gender": ip_gender, "21_ip_dob": str(ip_dob), "22_ip_ssn": ip_ssn,
            "23_ip_relationship": ip_relationship, "24_ip_title": ip_title,
            "25_ip_has_poa": ip_has_poa, "26_ip_has_proof": ip_has_proof,
            "27_ip_reason_no_discuss": ip_reason_no_discuss,
            # 28–33 Death
            "28_is_deceased": is_deceased, "29_date_of_death": str(dod) if dod else "",
            "30_cause_of_death": cod, "31_death_state": death_state, "32_has_death_cert": has_death_cert,
            "33_right_to_claim_docs": right_to_claim_docs,
            # 34–37 EC
            "34_ec_name": ec_name, "35_ec_relation": ec_relation, "36_ec_phone": ec_phone, "37_ec_email": ec_email,
            # 38–51 Incident
            "38_driver_or_rider": was_driver_or_rider, "39_incident_narrative": incident_narr,
            "40_has_incident_date": has_incident_date, "40a_incident_date": str(incident_date_known) if incident_date_known else "",
            "41_rideshare_company": rs_company, "42_in_us": us_occurrence, "43_incident_state": incident_state,
            "44_pickup_addr": pickup_addr, "45_dropoff_addr": dropoff_addr,
            "46_sexually_assaulted": sexually_assaulted, "47_fi_kidnapping": fi_kidnapping,
            "48_verbal_harassment": verbal_harassment, "49_inside_or_near": inside_or_near,
            "50_driver_weapon_desc": driver_weapon, "51_client_weapon": client_weapon,
            # 52–61 Reporting
            "52_has_receipt": has_receipt, "53_reported_channels": reported_channels,
            "54_rs_submit_how": rs_submit_how, "55_willing_to_report": willing_to_report,
            "56_rs_received_response": rs_received_response, "57_report_contact_info": report_contact_info,
            "58_where_found_number": where_found_number, "59_got_case_number": got_case_number,
            "60_who_answered": who_answered, "61_follow_up_after_call": follow_up_after_call,
            # 62–68 Medical
            "62_forms_signed_for_records": forms_signed_for_records, "63_med_treated": med_treated,
            "64_med_treatment_desc": med_treatment_desc, "65_med_doctor": med_doctor,
            "66_med_facility": med_facility, "67_med_address": med_address, "68_med_phone": med_phone,
            # 69–77 MH1
            "69_mh1_yes": mh1_yes, "70_mh1_desc": mh1_desc, "71_mh1_doctor": mh1_doctor,
            "72_mh1_hospital": mh1_hospital, "73_mh1_address": mh1_address, "74_mh1_phone": mh1_phone,
            "75_mh1_website": mh1_website, "76_mh1_diagnosis": mh1_diagnosis, "77_mh1_treatment": mh1_treatment,
            # 78–86 MH2
            "78_mh2_yes": mh2_yes, "79_mh2_desc": mh2_desc, "80_mh2_doctor": mh2_doctor,
            "81_mh2_hospital": mh2_hospital, "82_mh2_address": mh2_address, "83_mh2_phone": mh2_phone,
            "84_mh2_website": mh2_website, "85_mh2_diagnosis": mh2_diagnosis, "86_mh2_treatment": mh2_treatment,
            # 87–94 Additional
            "87_am_name": am_name, "88_am_address": am_address, "89_am_phone": am_phone,
            "90_am_website": am_website, "91_am_diagnosis": am_diagnosis, "92_am_symptoms": am_symptoms,
            "93_am_treatment": am_treatment, "94_am_comments": am_comments,
            # 95–103 Pharmacy
            "95_ph_name": ph_name, "96_ph_phone": ph_phone, "97_ph_website": ph_website, "98_ph_address": ph_address,
            "99_ph_med1": ph_med1, "100_ph_med2": ph_med2, "101_ph_comments": ph_comments, "102_ph_med3": ph_med3,
            # 103–105
            "103_affirm": affirm, "104_ip_address": ip_addr, "105_jornaya": jornaya
        }
        st.success("Wagstaff answers saved.")

    # footer actions
    colA, colB, colC = st.columns([1,1,2])
    with colA:
        if st.button("Back to Intake"):
            st.session_state.step = "intake"; st.rerun()
    with colB:
        # Always-on CSV
        payload = {"firm":"Wagstaff"}
        if "intake_payload" in st.session_state: payload.update(st.session_state.intake_payload)
        payload.update(st.session_state.answers_wag)
        df = pd.DataFrame([payload])
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download wagstaff_followup.csv", data=csv_bytes, file_name="wagstaff_followup.csv", mime="text/csv", key="dl_wag_csv_btn")
    with colC:
        st.caption("Yes/No scripts now update instantly—no Submit needed.")

# =========================
# TRITEN – YOUR DETAILED FLOW (VERBATIM)
# =========================
def render_triten_questions():
    st.header("Triten – Detailed Questionnaire")
    st.caption("Uses your exact wording. Scripts show inline where you specified them.")

    def calc_age(d):
        try:
            if not d: return None
            today = TODAY.date()
            return today.year - d.year - ((today.month, today.day) < (d.month, d.day))
        except Exception:
            return None

    # 1–4 Narrative
    st.subheader("1–4. Narrative")
    tri_1_stmt = st.text_area("1. Statement of the Case:")
    tri_2_burden = st.text_area("2. Burden:")
    tri_3_ice = st.text_area("3. Icebreaker:")
    tri_4_comments = st.text_area("4. Comments:")

    # CLIENT CONTACT DETAILS (5–21)
    st.markdown("---")
    st.subheader("CLIENT CONTACT DETAILS")

    ccols = st.columns([1,1,1])
    tri_5_first = ccols[0].text_input("5. Client Name: (First Name)")
    tri_5_middle = ccols[1].text_input("(Middle Name)")
    tri_5_last = ccols[2].text_input("(Last Name)")

    tri_6_maiden = st.text_input("6. What is your maiden name (if applicable)?")
    tri_7_prefname = st.text_input("7. Preferred Name?")
    tri_8_email = st.text_input("8. Primary Email:")
    tri_9_addr = st.text_input("9. Mailing Address:")
    tri_10_city = st.text_input("10. City:")
    tri_11_state = st.selectbox("11. State:", STATE_OPTIONS)
    tri_12_zip = st.text_input("12. Zip:")
    tri_13_home = st.text_input("13. Home Phone No.:", placeholder="+1 (###) ###-####")
    tri_14_cell = st.text_input("14. Cell Phone No.:", placeholder="(214) 550-0063")
    tri_15_best = st.text_input("15. Best Time to Contact:")
    tri_16_pref = st.text_input("16. Preferred Method of Contact:")

    tri_17_dob = st.date_input("17. Date of Birth: mm-dd-yyyy", value=TODAY.date())
    st.caption(f"Age: {calc_age(tri_17_dob) if tri_17_dob else 'Not calculated yet'}")

    tri_18_ssn = st.text_input("18. Social Security No.: 000-00-0000")
    tri_19_claim_for = st.radio("19. Does the claim pertain to you or another person?", ["Myself","Someone else"], horizontal=True)
    tri_20_marital = st.radio("20. Current marital status:", ["Single","Married","Divorced","Widowed"], horizontal=True)
    tri_21_prevfirm = st.text_area("21. As far as you can remember, have you signed up with any Law Firm to represent you on this case but then got disqualified for any reason . . . we still might be able to help but need to know?")

    # INJURED PARTY DETAILS (22–30)
    st.markdown("---")
    st.subheader("INJURED PARTY DETAILS")

    tri_22_ip_dob = st.date_input("22. Injured/Deceased Party's DOB: mm-dd-yyyy", value=TODAY.date())
    st.caption(f"Age: {calc_age(tri_22_ip_dob) if tri_22_ip_dob else 'Not calculated yet'}")

    tri_23_ip_name = st.text_input("23. Injured/Deceased Party's Full Name (First, Middle, & Last Name):")
    tri_24_ip_gender = st.text_input("24. Injured Party Gender")
    tri_25_ip_ssn = st.text_input("25. Injured/Deceased Party's SS#: 000-00-0000")
    tri_26_ip_rel = st.text_input("26. PC's Relationship to Injured/Deceased: (leave blank if PC is representing self)")

    tri_27_poa = st.radio("27. Does caller have POA or other legal authority?", ["Yes","No"], horizontal=True)
    tri_28_title = st.multiselect("28. Title to Represent:", ["Executor","Administrator","Trustee","Conservator","Legal Guardian","Power of Attorney","Parent","Other Agent"])
    tri_29_proof = st.radio("29. Does caller have proof of legal authority?", ["Yes","No"], horizontal=True)
    tri_30_reason = st.selectbox("30. Reason PC cannot discuss case:", ["Select","Minor","Incapacitated","Death","Other"])

    # IF DECEASED (31–36)
    st.markdown("IF INJURED CLAIMANT DIED:  (Please provide copy of Death Certificate to Paralegal When Confirming Details)")
    tri_31_deceased = st.radio("31. Is the client deceased?", ["Yes","No"], horizontal=True)
    tri_32_dod = st.date_input("32. Date of Death (if applies):", value=TODAY.date()) if tri_31_deceased=="Yes" else None
    tri_33_cod = st.text_input("33. Cause of Death on Death Cert:") if tri_31_deceased=="Yes" else ""
    tri_34_death_state = st.selectbox("34. In what state did the death occur?", STATE_OPTIONS) if tri_31_deceased=="Yes" else ""
    tri_35_death_cert = st.radio("35. Do you have a death certificate?", ["Yes","No"], horizontal=True) if tri_31_deceased=="Yes" else "No"
    tri_36_right_docs = st.text_area("36. Documentation of your right to the decedent’s claim?")

    # ALTERNATE / EMERGENCY CONTACT (37–40)
    st.markdown("---")
    st.subheader("ALTERNATE  / EMERGENCY CONTACT DETAILS")
    tri_37_ec_name = st.text_input("37. Alternate / Emergency Contact First & Last Name")
    tri_38_ec_rel = st.text_input("38. Alternate / Emergency Contact Relation to Client")
    tri_39_ec_phone = st.text_input("39. Alternate / Emergency Contact Number", placeholder="+1 (###) ###-####")
    tri_40_ec_email = st.text_input("40. Alternate / Emergency Contact Email")

    # INCIDENT DETAILS (41–59)
    st.markdown("---")
    st.subheader("INCIDENT DETAILS")

    tri_41_role = pick(
        "41. Were you the driver or rider during this incident?",
        ["Driver","Rider"], key="tri_41_role", horizontal=True,
        scripts_by_value={
            "Rider": "If Rider: Okay, you were the rider. Thank you for clarifying that — this helps us understand who had control of the vehicle.",
            "Driver": "If Driver: Okay. You were the driver — thank you for sharing that. Unfortunately, the law firm is not currently taking cases where the driver was assaulted. I’m really sorry we cannot help you."
        }
    )

    tri_42_narr = st.text_area(
        "42. I know it’s not always easy to talk about the incident and we appreciate you trusting us with these details. "
        "Can you please describe what happened in your own words. (Allow claimant to speak freely.)  "
        "(Include purpose of rideshare and type of location, like business or residence; front or back seat; vehicle stopped or moving during assault.)"
    )
    script_block('Agent Response: Thank you for sharing that with me. You said "[mirror key words]" — and that sounds incredibly difficult. I want you to know this space is confidential, and you\'re doing the right thing by speaking up.')

    tri_43_options = [
        "Rape","Sodomy","Digital penetration",
        "Forced oral copulation (oral contact with sexual organs or anus)",
        "Unwanted touching or attempt of touching (including kissing) of sexual body parts (breast, buttocks, genitals, inner thighs) Over Clothes",
        "Unwanted touching or attempt of touching (including kissing) of sexual body parts (breast, buttocks, genitals, inner thighs) -- Under Clothes",
        "Indecent exposure and unwanted touching, masturbation",
        "Masturbation",
        "Inappropriate/unwanted touching to non-sexual body parts",
        "Forced manual stimulation"
    ]
    tri_43_rst = st.multiselect("43. (RST) Please select any of the following that occurred:", options=sorted(set(tri_43_options)))

    tri_44_inj_dx = st.text_area("44. Please provide details regarding your injuries and diagnosis (from a medical professional, including doctor, therapist, psychiatrist).")

    tri_45_has_date = pick("45. Do you have the Date the incident occurred?", ["Yes","No"], key="tri_45_has_date", horizontal=True,
                           scripts_by_value={"Yes": "Agent Response: Got it. The date was [repeat date]. The timing really helps us document everything properly and connect the incident with the Rideshare trip. So thank you for that."})
    tri_45a_inc_date = st.date_input("Select date", value=TODAY.date(), key="tri_45a_inc_date") if tri_45_has_date=="Yes" else None

    tri_46_timing = st.radio("46. Timing of incident", ["1 year ago","1-2 years ago","3-4 years ago","4+ years ago"], horizontal=True)
    tri_47_company = st.selectbox("47. Which Rideshare company did you use?", ["Uber","Lyft","Other"])
    script_block("Agent Response: [Rideshare company name], got it. That helps the law firm determine who may be held responsible and verify who operated the ride at the time. You’re doing great.")

    tri_48_in_us = st.radio("48. Did the incident occur within the United States?", ["Yes","No"], horizontal=True)
    tri_49_state = st.selectbox("49. What state this this happen?", STATE_OPTIONS)
    script_block("Agent Response: Okay. [Repeat state]. Thank you.")

    tri_50_pickup = st.text_input("50. Can you tell me the Pick-up location? (Need full address + accurate description confirmed in Google maps)")
    script_block("Agent Response: Okay, you were picked up from [repeat location]. Got it – every detail like this helps to reconstruct the trip and validate what happened — thank you.")

    tri_51_drop = st.text_input("51. And where was the Drop-off location? (Need full address + accurate description confirmed in Google maps)")
    script_block("Agent Response: Okay, you were dropped off at [location]. Thank you. That’s helpful in building out the trip details.")

    tri_52_sa = yesno(
        "52. You’re doing great. Were you sexually assaulted or inappropriately touched by the Rideshare driver?",
        key="tri_52_sa",
        script_yes="Agent Response: Okay, I’m really sorry to hear you were [repeat relevant details] and put in that situation. It’s incredibly brave of you to talk about it. Thank you for trusting us with this."
    )

    tri_53_phys = yesno("53. Were you physically assaulted by a rideshare driver/passenger? (Ex: Was there a threat of - or actual - unwanted touching, slapping, pinching, pushing, shoving, choking, kicking, or physical restraints.)", key="tri_53_phys")

    tri_54_verbal = yesno("54. Were you subjected to verbal harassment?", key="tri_54_verbal",
                          script_yes="If Yes: Okay, so you did experience verbal harassment – I’m sorry you had to endure that. Even when it’s not physical, those moments are serious and deserve to be heard.")

    tri_55_flirt_threat = yesno("55. Did the assault involve aggressive flirtation and/or overt sexual threats? (Ex: Persistent physical touch, suggestive comments, disregard for personal space or boundaries / Threats of rape, assault, demands for sexual favors, threats of negative consequences for refusal.)", key="tri_55_flirt_threat")

    tri_56_fi_kidnap = yesno("56. During this incident, were you subjected to false imprisonment or kidnapping (such as physical/verbal restraint or restriction of movement) with overt or physical threats?",
                             key="tri_56_fi_kidnap",
                             script_yes="Agent Response: That sounds terrifying – you mentioned [repeat some relevant acts], and I’m really sorry you went through that. We want to make sure the law firm understands how serious this was.")

    tri_57_scope = pick("57. Did the incident occur while utilizing the Rideshare service, either inside or just outside the vehicle?",
                        ["Yes","No"], key="tri_57_scope", horizontal=True,
                        scripts_by_value={"Yes":"If Yes: Okay. So, it happened [repeat where happened]. Thank you. Knowing where it happened while using the Rideshare helps confirm that it’s within the scope of the Rideshare’s responsibility, which includes providing a safe means of transportation."})

    tri_58_driver_weapon = st.text_area("58. Did the driver threaten or use any weapons or means of force during the sexual assault, such as gun, knife, or choking? If yes, please elaborate.")
    if tri_58_driver_weapon.strip():
        script_block("If Yes: Okay, [repeat type of weapon or means of force]. That’s very serious and the details help paint a full picture of the situation. I’m so sorry that happened.")
    else:
        script_block("If No: Okay, although there was no weapon, this is still a very serious situation and does not change the magnitude of the incident.")

    tri_59_client_weapon = pick("59. Were you carrying a weapon at the time of the assault? If yes, DQ. (Personal defense tools like pepper spray/mace may not be a weapon)",
                                ["No","Yes"], key="tri_59_client_weapon", horizontal=True,
                                scripts_by_value={
                                    "No":"If No: Okay, you did not have a weapon with you. That’s all we need on that part — thank you for confirming.",
                                    "Yes":"If Yes: Okay, thank you for that. And I appreciate your honesty. But based upon the current guidelines, the law firm may not be accepting cases where the victim had a weapon."
                                })

    # REPORTING & TREATMENT DETAILS (60–75)
    st.markdown("---")
    st.subheader("REPORTING & TREATMENT DETAILS")

    tri_60_receipt = pick("60. Are you able to reproduce the Rideshare Receipt to show proof of the ride? (If not, DQ)",
                          ["Yes","No"], key="tri_60_receipt", horizontal=True,
                          scripts_by_value={
                              "Yes":"If Yes: Okay, that’s great you can get the receipt for the ride. That is one of the most important pieces of proof we need that will link your rideshare trip to the incident.",
                              "No":"If No: Okay, so you cannot check it in your email or on the app? That is one of the most important pieces of proof we need that will link your rideshare trip to the incident. [Refer the claimant to instructions on obtaining the receipt through email or the app.]"
                          })
    tri_61_login = pick("61. Do you have or can you retrieve the log in information for the account the ride was ordered from?",
                        ["Yes","No"], key="tri_61_login", horizontal=True)

    tri_62_reported = st.multiselect("62. Did you report the incident to anyone, like the Rideshare Company, Police, Therapist, Physician, or Friend or Family Member?",
                                     ["Rideshare Company","Physician","Friend or Family Member","Therapist","Police Department","NO (DQ, UNLESS TIER 1 OR MINOR)"])
    if tri_62_reported:
        script_block("If Reported: Okay, that’s good that you reported it to [repeat answer] — thank you. That helps show you took steps to get help, and that can support your case. It takes a lot of strength.")
    else:
        script_block("If Not Reported: Okay, so you didn’t tell anyone that might be able to corroborate your story. That can make it difficult to pursue. Let me speak with my supervisor, but based upon the guidelines, the law firm may not be accepting cases where the victim did not report it to anyone.")

    st.markdown("**If Reported to a Friend or Family Member:**")
    tri_63_ff_name = st.text_input("63. Name of friend/family member:")
    tri_64_ff_contact = st.text_input("64. Contact Information:")
    tri_65_ff_rel = st.text_input("65. Relationship:")
    tri_66_ff_perm = pick("66. Permission to speak to family member?", ["Yes","No"], key="tri_66_ff_perm", horizontal=True)
    tri_67_ff_date = st.date_input("67. Date informed family member?", value=TODAY.date())
    tri_68_ff_details = st.text_area("68. What details did you share to this family member?")
    tri_69_ff_ok = pick("69. Would you be okay with us reaching out to them at a later time?", ["Yes","No"], key="tri_69_ff_ok", horizontal=True)
    tri_70_ff_when = st.date_input("70. When did you report the incident to your friend or family member?", value=TODAY.date())
    tri_71_ff_share = st.text_area("71. What did you share with them about the incident?")

    tri_72_rs_how = st.text_input("72. If submitted to Rideshare:  How did you submit the report to Uber or Lyft?")
    if tri_72_rs_how.strip():
        script_block("Agent Response: Okay, so you submitted it through [email/app]. That’s helpful — thank you for sharing that. Some survivors have used the app, and others reached out by email, so either is totally fine.")

    tri_73_rs_resp = st.text_input("73. Did you receive a response from Uber or Lyft?")
    if tri_73_rs_resp.strip():
        script_block("Agent Response: Got it — so they [did/did not] respond. That can be really frustrating, especially when you're expecting someone to acknowledge what happened.")

    tri_74_willing = pick("74. If not submitted to Rideshare via app or email: If the law firm feels that it is best that you report the incident to Uber or Lyft via email or the app, would you be willing to do so?",
                          ["Yes","No","Unsure"], key="tri_74_willing", horizontal=True,
                          scripts_by_value={
                              "Yes":"If Yes: Okay, so you'd be willing to report the incident if the law firm recommends it — thank you for being open to that. I'm sure they will provide guidance. It shows strength, and it could really help support your case.",
                              "No":"If No or Unsure: Okay, so you're not comfortable reporting it through the app or email right now — I completely understand. If the law firm thinks it's important later on, they'll walk you through what to do step by step. You're not alone in this.",
                              "Unsure":"If No or Unsure: Okay, so you're not comfortable reporting it through the app or email right now — I completely understand. If the law firm thinks it's important later on, they'll walk you through what to do step by step. You're not alone in this."
                          })

    tri_75_contact_info = st.text_area("75. Contact information for the person to whom incident was reported (Name, Address, Phone, Date Reported)")
    if tri_75_contact_info.strip():
        script_block("Agent Response: Okay, you reported it to [repeat answer]. That’s very helpful — we’ll make sure it’s properly noted.")

    # DETAILS ON WHO INCIDENT WAS REPORTED TO #1–#5 (76–95)
    st.markdown("DETAILS ON WHO REPORTED INCIDENT TO:")
    rel_options = ["Rideshare Company","Physician","Therapist","Police Department","Friend or Family Member"]
    reported_blocks = []
    for idx in range(5):
        base = 76 + idx*4  # (#1: 76–79, #2: 80–83, #3: 84–87, #4: 88–91, #5: 92–95)
        st.markdown(f"**DETAILS ON WHO INCIDENT WAS REPORTED TO #{idx+1}:**")
        name = st.text_input(f"{base}. Name who incident was reported to:", key=f"tri_rep{idx+1}_name")
        relation = st.selectbox(f"{base+1}. Relationship to Claimant:", ["Select"] + rel_options, key=f"tri_rep{idx+1}_rel")
        date = st.date_input(f"{base+2}. Date incident was reported to this person:", value=TODAY.date(), key=f"tri_rep{idx+1}_date")
        addr = st.text_input(f"{base+3}. Address of this person incident was reported:", key=f"tri_rep{idx+1}_addr")
        reported_blocks.append({"name": name, "relation": relation, "date": str(date), "address": addr})

    # IF PC CALLED UBER OR LYFT (96–99)
    st.markdown("---")
    st.subheader("IF PC CALLED UBER OR LYFT")
    st.caption("A lot of survivors have tried different ways to get in touch with Uber. Sometimes it’s confusing because the options aren’t always clear — so you’re definitely not alone in that.")

    tri_96_where_num = st.text_input("96. Do you remember where you found the phone number you called?")
    if tri_96_where_num.strip():
        script_block('Agents Response: “Thanks for letting me know. A lot of people try calling through numbers they find online or in emails. You said you found it [repeat source: online/in an old email/etc.] — that’s helpful.”')

    tri_97_confirm_no = st.text_input("97. Did you receive any kind of confirmation or case number from that call?")
    if tri_97_confirm_no.strip():
        script_block('Agents Response: “Got it. That helps us track if Uber created an internal file for your report.”')

    tri_98_who_answered = st.text_input("98. When you made the call, did someone say they were with Uber or Lyft, or just take down your information?")
    if tri_98_who_answered.strip():
        script_block('Agents Response: “Okay, so they answered — and you said they [repeat answer]?” “That’s helpful. We’ve heard similar things from others who weren’t quite sure who they spoke with.”')

    tri_99_follow_up = st.text_area("99. Did you receive any follow-up after the call — like an email or app message? Or did they give you any instructions, like emailing, going to the app, or waiting for a follow-up?")
    if tri_99_follow_up.strip():
        script_block('If asked to email or use the app:  Thank you for walking me through that. You mentioned they told you to [repeat answer], and that’s something we hear often. A lot of survivors say they didn’t get much clarity — or were told to start over — so you’re not alone in that.”')
    else:
        script_block('If no follow-up was received:  Got it. You said you didn’t hear anything back — and that’s totally okay. A lot of survivors have shared the same experience, where they reported something and never received any kind of follow-up."')

    # MEDICAL TREATMENT DETAILS (100–106)
    st.markdown("---")
    st.subheader("MEDICAL TREATMENT DETAILS")
    tri_100_forms = st.text_input("100. Have you ever signed any forms for anyone to get your medical records for this matter? (If so, who?)")
    tri_101_med = pick("101. Did you receive medical treatment for physical injuries sustained during the assault?", ["Yes","No"], key="tri_101_med", horizontal=True)
    tri_102_med_desc = st.text_area("102. Please describe your medical treatment:")
    tri_103_doc = st.text_input("103. Doctor who diagnosed you:")
    tri_104_fac = st.text_input("104. Hospital/Facility where the diagnosis was done:")
    tri_105_addr = st.text_input("105. Hospital/Facility/Doctor's Address:")
    tri_106_phone = st.text_input("106. Hospital/Facility/Doctor's Phone Number:", placeholder="+1 (###) ###-####")

    # MENTAL HEALTH TREATMENT DETAILS 1 (107–115)
    st.markdown("---")
    st.subheader("MENTAL HEALTH TREATMENT DETAILS 1")
    tri_107_mh = pick("107. Have you received any mental health treatment related to your assault?", ["Yes","No"], key="tri_107_mh", horizontal=True)
    tri_108_mh_desc = st.text_area("108. Please describe your mental health treatment so far (generally):")
    tri_109_mh_doc = st.text_input("109. Name of the Doctor who treated you:")
    tri_110_mh_hosp = st.text_input("110. Hospital where you received treatment:")
    tri_111_mh_addr = st.text_input("111. Hospital's Address:")
    tri_112_mh_phone = st.text_input("112. Hospital's Phone Number:", placeholder="+1 (###) ###-####")
    tri_113_mh_web = st.text_input("113. Hospital's Website Address:")
    tri_114_mh_dx = st.text_input("114. Diagnosed Ailment / Diagnosis Date(s):")
    tri_115_mh_tx = st.text_area("115. Treatment Type / Treatment Date(s): (Describe the treatment that you received in detail)")

    # MENTAL HEALTH TREATMENT DETAILS 2 (116–124)
    st.markdown("---")
    st.subheader("MENTAL HEALTH TREATMENT DETAILS 2")
    tri_116_mh2 = pick("116. Have you received any mental health treatment related to your assault?", ["Yes","No"], key="tri_116_mh2", horizontal=True)
    tri_117_mh2_desc = st.text_area("117. Please describe your mental health treatment so far (generally):")
    tri_118_mh2_doc = st.text_input("118. Name of the Doctor who treated you:")
    tri_119_mh2_hosp = st.text_input("119. Hospital where you received treatment:")
    tri_120_mh2_addr = st.text_input("120. Hospital's Address:")
    tri_121_mh2_phone = st.text_input("121. Hospital's Phone Number:")
    tri_122_mh2_web = st.text_input("122. Hospital's Website Address:")
    tri_123_mh2_dx = st.text_input("123. Diagnosed Ailment / Diagnosis Datae(s):")
    tri_124_mh2_tx = st.text_area("124. Treatment Type / Treatment Date(s): (Describe the treatment that you received in detail).")

    # ADDITIONAL PROVIDERS (125–132)
    st.markdown("---")
    st.subheader("ADDITIONAL RELEVANT MEDICAL OR MENTAL HEALTH PROVIDERS")
    tri_125_am_name = st.text_input("125. Doctor/ Facility Name:")
    tri_126_am_addr = st.text_input("126. Address:")
    tri_127_am_phone = st.text_input("127. Phone Number:")
    tri_128_am_web = st.text_input("128. Website Address")
    tri_129_am_dx = st.text_input("129. Diagnosed Ailment / Diagnosis Date(s):")
    tri_130_am_sym = st.text_input("130. Symptom(s):")
    tri_131_am_tx = st.text_input("131. Treatment Type / Treatment Date(s):")
    tri_132_am_comments = st.text_area("132. Comments:")

    # PHARMACY (133–140)
    st.markdown("---")
    st.subheader("PHARMACY FOR MEDICATIONS")
    tri_133_ph_name = st.text_input("133. Name:")
    tri_134_ph_phone = st.text_input("134. Phone:")
    tri_135_ph_web = st.text_input("135. Website:")
    tri_136_ph_addr = st.text_input("136. Full Street, City, Zip Address:")
    tri_137_ph_med1 = st.text_input("137. Ailment / Medication / Dates Prescribed:")
    tri_138_ph_med2 = st.text_input("138. Ailment / Medication / Dates Prescribed:")
    tri_139_ph_comments = st.text_area("139. Comments:")
    tri_140_ph_med3 = st.text_input("140. Ailment / Medication / Date Prescribed:")

    # AFFIRM + TECH (141–143)
    st.markdown("---")
    tri_141_affirm = pick("141. [Having just confirmed all the answers you have provided in response to all the questions] Do you hereby affirm that the information submitted by you is true and correct in all respects, including whether you've ever signed up with another law firm?",
                          ["Yes","No"], key="tri_141_affirm", horizontal=True)
    st.subheader("INTAKE ENDS HERE")
    tri_142_ip = st.text_input("142. IP Address")
    tri_143_jornaya = st.text_area("143. Trusted Form/Jornaya Data")

    # LEGACY QUESTIONS (144–160)
    st.markdown("---")
    st.subheader("LEGACY QUESTIONS")
    tri_144_reported = st.multiselect("144. Did you report the incident to anyone, like the Rideshare Company, Police, Therapist, Physician, or Friend or Family Member?",
                                      ["Rideshare Company","Physician","Friend or Family Member","Therapist","Police Department","NO (DQ, UNLESS TIER 1 OR MINOR)"])
    if tri_144_reported:
        script_block("If Reported: Okay, that’s good that you reported it to [repeat answer] — thank you. That helps show you took steps to get help, and that can support your case. It takes a lot of strength.")
    else:
        script_block("If Not Reported: Okay, so you didn’t tell anyone that might be able to corroborate your story. That can make it difficult to pursue. Let me speak with my supervisor, but based upon the guidelines, the law firm may not be accepting cases where the victim did not report it to anyone.")

    tri_145_legacy_ipdob = st.date_input("145. Injured/Deceased Party's DOB: mm-dd-yyyy", value=TODAY.date())
    tri_146_claim_for = st.radio("146. Does the claim pertain to you or another person?", ["Myself","Someone Else"], horizontal=True)
    tri_147_legacy_dod = st.date_input("147. Date of Death (if applies):", value=TODAY.date())
    tri_148_legacy_state = st.selectbox("148. In what state did the death occur?", STATE_OPTIONS)
    tri_149_role2 = pick("149. Were you the driver or rider during this incident?",
                         ["Driver","Rider"], key="tri_149_role", horizontal=True,
                         scripts_by_value={
                             "Rider":"If Rider: Okay, you were the rider. Thank you for clarifying that — this helps us understand who had control of the vehicle.",
                             "Driver":"If Driver: Okay. You were the driver — thank you for sharing that. Unfortunately, the law firm is not currently taking cases where the driver was assaulted. I’m really sorry we cannot help you."
                         })
    tri_150_marital = st.multiselect("150. Current marital status' (check one):", ["Single","Divorced","Widowed","Married"])
    tri_151_timing = st.multiselect("151. Timing of incident", ["1 year ago","1-2 years ago","3-4 years ago","4+ years ago"])
    tri_152_title = st.multiselect("152. Title to Represent:", ["Executor","Conservator","Parent","Administrator","Legal Guardian","Other Agent","Trustee","Power of Attorney"])

    tri_153_reported2 = st.multiselect("153. Did you report the incident to anyone, like the Rideshare Company, Police, Therapist, Physician, or Friend or Family Member?",
                                       ["Rideshare Company","Police","Therapist","Physician","Friend or Family Member"])
    tri_154_has_incdate = st.text_input("154. Do you have the Date the incident occurred? (Agent Response: Got it. The date was [repeat date]. The timing really helps us document everything properly and connect the incident with the Rideshare trip. So thank you for that.)")

    tri_155_rel = st.text_input("155. Relationship to claimant:")
    tri_156_rel = st.text_input("156. Relationship to Claimant:")
    tri_157_rel = st.text_input("157. Relationship to claimant:")
    tri_158_rel = st.text_input("158. Relationship to claimant:")
    tri_159_rel = st.text_input("159. Relationship to claimant:")
    tri_160_perm = st.text_input("160. Permission to speak to family member?")

    # Derived 14-day Triten check (uses intake incident date + the earliest reported date we captured)
    incident_dt_from_intake = None
    if "intake_payload" in st.session_state and st.session_state.get("intake_payload", {}).get("IncidentDateTime"):
        incident_dt_from_intake = st.session_state.intake_payload["IncidentDateTime"]

    report_dates_candidates = []
    if tri_67_ff_date: report_dates_candidates.append(tri_67_ff_date)
    if tri_70_ff_when: report_dates_candidates.append(tri_70_ff_when)
    for blk in reported_blocks:
        try:
            d = pd.to_datetime(blk["date"]).date()
            report_dates_candidates.append(d)
        except Exception:
            pass

    tri_earliest_report = min(report_dates_candidates) if report_dates_candidates else None
    tri_14_check = "Unknown"
    if tri_earliest_report and incident_dt_from_intake:
        d = (tri_earliest_report - incident_dt_from_intake.date()).days
        tri_14_check = (0 <= d <= 14)
        if not tri_14_check:
            st.warning("Earliest report appears outside the two-week window (Triten screen). Double-check dates.")

    # Persist everything
    st.session_state.answers_tri = {
        "1_statement": tri_1_stmt, "2_burden": tri_2_burden, "3_icebreaker": tri_3_ice, "4_comments": tri_4_comments,
        "5_first": tri_5_first, "5_middle": tri_5_middle, "5_last": tri_5_last, "6_maiden": tri_6_maiden,
        "7_pref_name": tri_7_prefname, "8_email": tri_8_email, "9_addr": tri_9_addr, "10_city": tri_10_city,
        "11_state": tri_11_state, "12_zip": tri_12_zip, "13_home": tri_13_home, "14_cell": tri_14_cell,
        "15_best_time": tri_15_best, "16_pref_contact": tri_16_pref, "17_dob": str(tri_17_dob),
        "18_ssn": tri_18_ssn, "19_claim_for": tri_19_claim_for, "20_marital": tri_20_marital, "21_prev_firm": tri_21_prevfirm,
        "22_ip_dob": str(tri_22_ip_dob), "23_ip_name": tri_23_ip_name, "24_ip_gender": tri_24_ip_gender,
        "25_ip_ssn": tri_25_ip_ssn, "26_ip_rel": tri_26_ip_rel, "27_poa": tri_27_poa, "28_title": tri_28_title,
        "29_proof": tri_29_proof, "30_reason": tri_30_reason,
        "31_deceased": tri_31_deceased, "32_dod": (str(tri_32_dod) if tri_32_dod else ""),
        "33_cod": tri_33_cod, "34_death_state": tri_34_death_state, "35_death_cert": tri_35_death_cert,
        "36_right_docs": tri_36_right_docs,
        "37_ec_name": tri_37_ec_name, "38_ec_rel": tri_38_ec_rel, "39_ec_phone": tri_39_ec_phone, "40_ec_email": tri_40_ec_email,
        "41_role": tri_41_role, "42_narr": tri_42_narr, "43_rst": tri_43_rst, "44_inj_dx": tri_44_inj_dx,
        "45_has_date": tri_45_has_date, "45a_inc_date": (str(tri_45a_inc_date) if tri_45a_inc_date else ""),
        "46_timing": tri_46_timing, "47_company": tri_47_company, "48_in_us": tri_48_in_us, "49_state": tri_49_state,
        "50_pickup": tri_50_pickup, "51_dropoff": tri_51_drop, "52_sa": tri_52_sa, "53_phys_assault": tri_53_phys,
        "54_verbal": tri_54_verbal, "55_flirt_threat": tri_55_flirt_threat, "56_fi_kidnap": tri_56_fi_kidnap,
        "57_scope": tri_57_scope, "58_driver_weapon": tri_58_driver_weapon, "59_client_weapon": tri_59_client_weapon,
        "60_receipt": tri_60_receipt, "61_login": tri_61_login, "62_reported": tri_62_reported,
        "63_ff_name": tri_63_ff_name, "64_ff_contact": tri_64_ff_contact, "65_ff_rel": tri_65_ff_rel,
        "66_ff_perm": tri_66_ff_perm, "67_ff_date": str(tri_67_ff_date), "68_ff_details": tri_68_ff_details,
        "69_ff_ok": tri_69_ff_ok, "70_ff_when": str(tri_70_ff_when), "71_ff_share": tri_71_ff_share,
        "72_rs_how": tri_72_rs_how, "73_rs_resp": tri_73_rs_resp, "74_willing": tri_74_willing,
        "75_contact_info": tri_75_contact_info,
        "reported_to_blocks": reported_blocks,
        "96_where_number": tri_96_where_num, "97_confirm_or_case": tri_97_confirm_no,
        "98_who_answered": tri_98_who_answered, "99_follow_up": tri_99_follow_up,
        "100_forms": tri_100_forms, "101_med_treated": tri_101_med, "102_med_desc": tri_102_med_desc,
        "103_med_doc": tri_103_doc, "104_med_fac": tri_104_fac, "105_med_addr": tri_105_addr, "106_med_phone": tri_106_phone,
        "107_mh_yes": tri_107_mh, "108_mh_desc": tri_108_mh_desc, "109_mh_doc": tri_109_mh_doc,
        "110_mh_hosp": tri_110_mh_hosp, "111_mh_addr": tri_111_mh_addr, "112_mh_phone": tri_112_mh_phone,
        "113_mh_web": tri_113_mh_web, "114_mh_dx": tri_114_mh_dx, "115_mh_tx": tri_115_mh_tx,
        "116_mh2_yes": tri_116_mh2, "117_mh2_desc": tri_117_mh2_desc, "118_mh2_doc": tri_118_mh2_doc,
        "119_mh2_hosp": tri_119_mh2_hosp, "120_mh2_addr": tri_120_mh2_addr, "121_mh2_phone": tri_121_mh2_phone,
        "122_mh2_web": tri_122_mh2_web, "123_mh2_dx": tri_123_mh2_dx, "124_mh2_tx": tri_124_mh2_tx,
        "125_am_name": tri_125_am_name, "126_am_addr": tri_126_am_addr, "127_am_phone": tri_127_am_phone,
        "128_am_web": tri_128_am_web, "129_am_dx": tri_129_am_dx, "130_am_sym": tri_130_am_sym,
        "131_am_tx": tri_131_am_tx, "132_am_comments": tri_132_am_comments,
        "133_ph_name": tri_133_ph_name, "134_ph_phone": tri_134_ph_phone, "135_ph_web": tri_135_ph_web,
        "136_ph_addr": tri_136_ph_addr, "137_ph_med1": tri_137_ph_med1, "138_ph_med2": tri_138_ph_med2,
        "139_ph_comments": tri_139_ph_comments, "140_ph_med3": tri_140_ph_med3,
        "141_affirm": tri_141_affirm, "142_ip": tri_142_ip, "143_jornaya": tri_143_jornaya,
        "144_reported": tri_144_reported, "145_legacy_ipdob": str(tri_145_legacy_ipdob),
        "146_claim_for": tri_146_claim_for, "147_legacy_dod": str(tri_147_legacy_dod),
        "148_legacy_state": tri_148_legacy_state, "149_role": tri_149_role2,
        "150_marital": tri_150_marital, "151_timing": tri_151_timing, "152_title": tri_152_title,
        "153_reported2": tri_153_reported2, "154_has_incdate": tri_154_has_incdate,
        "155_rel": tri_155_rel, "156_rel": tri_156_rel, "157_rel": tri_157_rel, "158_rel": tri_158_rel, "159_rel": tri_159_rel,
        "160_perm": tri_160_perm,
        "Triten_earliest_report": (str(tri_earliest_report) if tri_earliest_report else ""),
        "Triten_14day_check": tri_14_check
    }

    # Footer actions
    colA, colB = st.columns([1,1])
    with colA:
        if st.button("Back to Intake", key="tri_back_intake"):
            st.session_state.step = "intake"; st.rerun()
    with colB:
        payload = {"firm":"Triten"}
        if "intake_payload" in st.session_state:
            payload.update(st.session_state.intake_payload)
        payload.update(st.session_state.answers_tri)
        df = pd.DataFrame([payload])
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download triten_followup.csv", data=csv_bytes, file_name="triten_followup.csv", mime="text/csv", key="dl_tri_csv_btn")

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
