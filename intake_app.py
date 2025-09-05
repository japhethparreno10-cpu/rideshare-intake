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
.small {font-size: 0.9rem; color:#4b5563;}
hr {border:0; border-top:1px solid #e5e7eb; margin:12px 0;}
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

    sol_years = TORT_SOL.get(state)
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

    # COMPANY POLICY: Triten (Uber & Lyft); Waggy (Uber only); Priority Triten if both
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
        "Sexual Assault Extension Note": "—",  # optional quick note could be re-added
        "Reported Dates (by channel)": report_dates_str,
        "Reported to Family/Friends (DateTime)": family_dt_str,
        "Wrongful Death Note": "—",
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

    # EXPORT (intake + decision)
    st.subheader("Export")
    export_df = pd.concat([pd.DataFrame([state_data]), df], axis=1)
    csv_bytes = export_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV (intake + decision)", data=csv_bytes, file_name="intake_decision.csv", mime="text/csv")

    st.caption("Firm rules: Triten = Uber & Lyft; Waggy = Uber only; Priority = Triten if both eligible. Wagstaff: no felonies, no weapons (non-lethal defensive allowed), no verbal/attempt-only; file 45 days before SOL; Family/Friends-only report must be within 24 hours. Triten: earliest report within 2 weeks.")

# =========================
# WAGSTAFF QUESTION FLOW (1–105)
# =========================
def render_wagstaff_questions():
    st.header("Wagstaff – Detailed Questionnaire")

    with st.form("wagstaff_form", clear_on_submit=False):
        # 1–4: Narrative fields
        st.subheader("1–4. Narrative")
        s1 = st.text_area("1. Statement of the Case")
        s2 = st.text_area("2. Burden")
        s3 = st.text_area("3. Icebreaker")
        s4 = st.text_area("4. Comments")

        st.markdown("---")
        st.subheader("Client Contact Details (5–18)")

        ccols = st.columns([1,1,1])
        with ccols[0]:
            c_first = st.text_input("5. First Name", value="")
        with ccols[1]:
            c_middle = st.text_input("5. Middle Name", value="")
        with ccols[2]:
            c_last = st.text_input("5. Last Name", value="")

        c_email = st.text_input("6. Primary Email")
        c_addr = st.text_input("7. Mailing Address")
        c_city = st.text_input("8. City")
        c_state = st.selectbox("9. State", STATE_OPTIONS, index=STATE_OPTIONS.index("Georgia") if "Georgia" in STATE_OPTIONS else 0)
        c_zip = st.text_input("10. Zip")
        c_home = st.text_input("11. Home Phone No.", placeholder="+1 (###) ###-####")
        c_cell = st.text_input("12. Cell Phone No.", placeholder="(###) ###-####")
        c_best_time = st.text_input("13. Best Time to Contact")
        c_pref_method = st.text_input("14. Preferred Method of Contact")
        c_dob = st.date_input("15. Date of Birth", value=TODAY.date())
        c_ssn = st.text_input("16. Social Security No.", placeholder="000-00-0000")
        c_claim_for = st.radio("17. Does the claim pertain to you or another person?", ["Myself","Someone Else"], horizontal=True)
        c_prev_firm = st.text_area("18. Signed up with any law firm before and got disqualified? (explain)")

        st.markdown("---")
        st.subheader("Injured Party Details (19–27)")
        ip_name = st.text_input("19. Injured/Deceased Party's Full Name")
        ip_gender = st.text_input("20. Injured Party Gender")
        ip_dob = st.date_input("21. Injured/Deceased Party's DOB", value=TODAY.date())
        ip_ssn = st.text_input("22. Injured/Deceased Party's SS#", placeholder="000-00-0000")
        ip_relationship = st.text_input("23. PC's Relationship to Injured/Deceased")
        ip_title = st.multiselect("24. Title to Represent", ["Executor","Administrator","Trustee","Conservator","Legal Guardian","Parent","Power of Attorney","Other Agent"])
        ip_has_poa = st.radio("25. Does caller have POA or other legal authority?", ["Yes","No"], horizontal=True)
        ip_has_proof = st.radio("26. Does caller have proof of legal authority?", ["Yes","No"], horizontal=True)
        ip_reason_no_discuss = st.selectbox("27. Reason PC cannot discuss case", ["Select","Minor","Incapacitated","Death","Other"])

        st.markdown("---")
        st.subheader("Death Details (28–33)")
        is_deceased = st.radio("28. Is the client deceased?", ["No","Yes"], horizontal=True)
        dod = st.date_input("29. Date of Death (if applies)", value=TODAY.date()) if is_deceased=="Yes" else None
        cod = st.text_input("30. Cause of Death on Death Cert") if is_deceased=="Yes" else ""
        death_state = st.selectbox("31. State of death", STATE_OPTIONS) if is_deceased=="Yes" else ""
        has_death_cert = st.radio("32. Do you have a death certificate?", ["No","Yes"], horizontal=True) if is_deceased=="Yes" else "No"
        right_to_claim_docs = st.text_area("33. Documentation of your right to the decedent’s claim?")

        st.markdown("---")
        st.subheader("Alternate / Emergency Contact (34–37)")
        ec_name = st.text_input("34. Alt/Emergency Contact Name")
        ec_relation = st.text_input("35. Relation to Client")
        ec_phone = st.text_input("36. Alt/Emergency Contact Number", placeholder="+1 (###) ###-####")
        ec_email = st.text_input("37. Alt/Emergency Contact Email")

        st.markdown("---")
        st.subheader("Incident Details (38–51)")
        was_driver_or_rider = st.radio("38. Were you the driver or rider during this incident?", ["Driver","Rider"], horizontal=True)
        incident_narr = st.text_area("39. Describe what happened (purpose, location, seat, stopped/moving)")
        has_incident_date = st.checkbox("40. Do you have the date of the incident?")
        incident_date_known = st.date_input("Incident Date", value=TODAY.date()) if has_incident_date else None
        rs_company = st.selectbox("41. Which Rideshare company did you use?", ["Uber","Lyft","Other"])
        us_occurrence = st.radio("42. Did the incident occur within the United States?", ["Yes","No"], horizontal=True)
        incident_state = st.selectbox("43. In what state did this happen?", STATE_OPTIONS)
        pickup_addr = st.text_input("44. Pick-up location (full address)")
        dropoff_addr = st.text_input("45. Drop-off location (full address)")
        sexually_assaulted = st.radio("46. Sexually assaulted or inappropriately touched by the driver?", ["No","Yes"], horizontal=True)
        fi_kidnapping = st.radio("47. False imprisonment or kidnapping with threats?", ["No","Yes"], horizontal=True)
        verbal_harassment = st.radio("48. Subjected to verbal harassment?", ["No","Yes"], horizontal=True)
        inside_or_near = st.radio("49. Incident occurred while using rideshare (inside/just outside)?", ["No","Yes"], horizontal=True)
        driver_weapon = st.text_input("50. Did the driver threaten/use weapons or force? (describe)")
        client_weapon = st.radio("51. Were you carrying a weapon at the time? (Note: non-lethal defense like pepper spray may not count)", ["No","Yes"], horizontal=True)

        st.markdown("---")
        st.subheader("Reporting & Treatment Details (52–61)")
        has_receipt = st.radio("52. Able to reproduce the Rideshare Receipt?", ["Yes","No"], horizontal=True)
        reported_channels = st.multiselect(
            "53. Did you report the incident to any of the following?",
            ["Rideshare Company","Physician","Friend or Family Member","Therapist","Police Department","NO (DQ, UNLESS TIER 1 OR MINOR)"]
        )
        rs_submit_how = st.text_input("54. If submitted to Rideshare: how (email/app)?")
        willing_to_report = st.radio("55. If not submitted via app/email: willing to report if the firm recommends?", ["Yes","No","Unsure"], horizontal=True)
        rs_received_response = st.radio("56. Did you receive a response from Uber/Lyft?", ["No","Yes"], horizontal=True)
        report_contact_info = st.text_area("57. Contact info of person/org reported to (Name, Relationship, Address, Phone, Date Reported)")

        st.subheader("If PC called Uber or Lyft (58–61)")
        where_found_number = st.text_input("58. Where did you find the phone number you called?")
        got_case_number = st.radio("59. Did you receive a confirmation or case number from that call?", ["No","Yes"], horizontal=True)
        who_answered = st.text_input("60. When you called, did someone say they were with Uber/Lyft or just take info?")
        follow_up_after_call = st.text_area("61. Any follow-up after the call? (email/app/instructions or none)")

        st.markdown("---")
        st.subheader("Medical Treatment Details (62–68)")
        forms_signed_for_records = st.text_input("62. Signed any forms for anyone to get your medical records? Who?")
        med_treated = st.radio("63. Received medical treatment for physical injuries?", ["No","Yes"], horizontal=True)
        med_treatment_desc = st.text_area("64. Describe medical treatment")
        med_doctor = st.text_input("65. Doctor who diagnosed you")
        med_facility = st.text_input("66. Hospital/Facility where diagnosis done")
        med_address = st.text_input("67. Hospital/Facility/Doctor's Address")
        med_phone = st.text_input("68. Hospital/Facility/Doctor's Phone Number", placeholder="+1 (###) ###-####")

        st.markdown("---")
        st.subheader("Mental Health Treatment Details 1 (69–77)")
        mh1_yes = st.radio("69. Received mental health treatment related to assault?", ["No","Yes"], horizontal=True)
        mh1_desc = st.text_area("70. Describe mental health treatment (general)")
        mh1_doctor = st.text_input("71. Doctor who treated you")
        mh1_hospital = st.text_input("72. Hospital where treated")
        mh1_address = st.text_input("73. Hospital's Address")
        mh1_phone = st.text_input("74. Hospital's Phone Number", placeholder="+1 (###) ###-####")
        mh1_website = st.text_input("75. Hospital's Website")
        mh1_diagnosis = st.text_input("76. Diagnosed Ailment / Diagnosis Date(s)")
        mh1_treatment = st.text_area("77. Treatment Type / Treatment Date(s)")

        st.markdown("---")
        st.subheader("Mental Health Treatment Details 2 (78–86)")
        mh2_yes = st.radio("78. Received mental health treatment related to assault? (2)", ["No","Yes"], horizontal=True)
        mh2_desc = st.text_area("79. Describe mental health treatment (general) (2)")
        mh2_doctor = st.text_input("80. Doctor who treated you (2)")
        mh2_hospital = st.text_input("81. Hospital where treated (2)")
        mh2_address = st.text_input("82. Hospital's Address (2)")
        mh2_phone = st.text_input("83. Hospital's Phone Number (2)", placeholder="+1 (###) ###-####")
        mh2_website = st.text_input("84. Hospital's Website (2)")
        mh2_diagnosis = st.text_input("85. Diagnosed Ailment / Diagnosis Date(s) (2)")
        mh2_treatment = st.text_area("86. Treatment Type / Treatment Date(s) (2)")

        st.markdown("---")
        st.subheader("Additional Medical / Mental Health Providers (87–94)")
        am_name = st.text_input("87. Doctor/Facility Name")
        am_address = st.text_input("88. Address")
        am_phone = st.text_input("89. Phone Number", placeholder="+1 (###) ###-####")
        am_website = st.text_input("90. Website Address")
        am_diagnosis = st.text_input("91. Diagnosed Ailment / Diagnosis Date(s)")
        am_symptoms = st.text_input("92. Symptoms")
        am_treatment = st.text_input("93. Treatment Type / Treatment Date(s)")
        am_comments = st.text_area("94. Comments")

        st.markdown("---")
        st.subheader("Pharmacy for Medications (95–103)")
        ph_name = st.text_input("95. Pharmacy Name")
        ph_phone = st.text_input("96. Phone", placeholder="+1 (###) ###-####")
        ph_website = st.text_input("97. Website")
        ph_address = st.text_input("98. Full Address (Street, City, Zip)")
        ph_med1 = st.text_input("99. Ailment / Medication / Dates Prescribed")
        ph_med2 = st.text_input("100. Ailment / Medication / Dates Prescribed")
        ph_comments = st.text_area("101. Comments")
        ph_med3 = st.text_input("102. Ailment / Medication / Date Prescribed")

        affirm = st.radio("103. Do you affirm the information is true and correct (including previous firm signup)?", ["Yes","No"], horizontal=True)

        st.markdown("---")
        st.subheader("Technical (104–105)")
        ip_addr = st.text_input("104. IP Address")
        jornaya = st.text_area("105. Trusted Form / Jornaya Data")

        submitted = st.form_submit_button("Save Wagstaff Answers")
        if submitted:
            st.session_state.answers_wag = {
                # 1–4
                "statement_of_case": s1, "burden": s2, "icebreaker": s3, "comments": s4,
                # 5–18 Client
                "client_first": c_first, "client_middle": c_middle, "client_last": c_last,
                "client_email": c_email, "client_addr": c_addr, "client_city": c_city, "client_state": c_state,
                "client_zip": c_zip, "client_home": c_home, "client_cell": c_cell, "best_time": c_best_time,
                "pref_method": c_pref_method, "dob": str(c_dob), "ssn": c_ssn, "claim_for": c_claim_for,
                "prev_firm": c_prev_firm,
                # 19–27 Injured Party
                "ip_name": ip_name, "ip_gender": ip_gender, "ip_dob": str(ip_dob), "ip_ssn": ip_ssn,
                "ip_relationship": ip_relationship, "ip_title": ip_title, "ip_has_poa": ip_has_poa,
                "ip_has_proof": ip_has_proof, "ip_reason_no_discuss": ip_reason_no_discuss,
                # 28–33 Death
                "is_deceased": is_deceased, "date_of_death": str(dod) if dod else "", "cause_of_death": cod,
                "death_state": death_state, "has_death_cert": has_death_cert, "right_to_claim_docs": right_to_claim_docs,
                # 34–37 EC
                "ec_name": ec_name, "ec_relation": ec_relation, "ec_phone": ec_phone, "ec_email": ec_email,
                # 38–51 Incident
                "driver_or_rider": was_driver_or_rider, "incident_narrative": incident_narr,
                "has_incident_date": has_incident_date, "incident_date": str(incident_date_known) if incident_date_known else "",
                "rideshare_company": rs_company, "in_us": us_occurrence, "incident_state": incident_state,
                "pickup_addr": pickup_addr, "dropoff_addr": dropoff_addr, "sexually_assaulted": sexually_assaulted,
                "false_imprisonment_kidnap": fi_kidnapping, "verbal_harassment": verbal_harassment,
                "inside_or_near": inside_or_near, "driver_weapon_desc": driver_weapon, "client_weapon": client_weapon,
                # 52–61 Reporting
                "has_receipt": has_receipt, "reported_channels": reported_channels,
                "rs_submit_how": rs_submit_how, "willing_to_report": willing_to_report,
                "rs_received_response": rs_received_response, "report_contact_info": report_contact_info,
                "where_found_number": where_found_number, "got_case_number": got_case_number,
                "who_answered": who_answered, "follow_up_after_call": follow_up_after_call,
                # 62–68 Medical
                "forms_signed_for_records": forms_signed_for_records, "med_treated": med_treated,
                "med_treatment_desc": med_treatment_desc, "med_doctor": med_doctor, "med_facility": med_facility,
                "med_address": med_address, "med_phone": med_phone,
                # 69–77 MH1
                "mh1_yes": mh1_yes, "mh1_desc": mh1_desc, "mh1_doctor": mh1_doctor,
                "mh1_hospital": mh1_hospital, "mh1_address": mh1_address, "mh1_phone": mh1_phone,
                "mh1_website": mh1_website, "mh1_diagnosis": mh1_diagnosis, "mh1_treatment": mh1_treatment,
                # 78–86 MH2
                "mh2_yes": mh2_yes, "mh2_desc": mh2_desc, "mh2_doctor": mh2_doctor,
                "mh2_hospital": mh2_hospital, "mh2_address": mh2_address, "mh2_phone": mh2_phone,
                "mh2_website": mh2_website, "mh2_diagnosis": mh2_diagnosis, "mh2_treatment": mh2_treatment,
                # 87–94 Additional
                "am_name": am_name, "am_address": am_address, "am_phone": am_phone,
                "am_website": am_website, "am_diagnosis": am_diagnosis, "am_symptoms": am_symptoms,
                "am_treatment": am_treatment, "am_comments": am_comments,
                # 95–103 Pharmacy
                "ph_name": ph_name, "ph_phone": ph_phone, "ph_website": ph_website, "ph_address": ph_address,
                "ph_med1": ph_med1, "ph_med2": ph_med2, "ph_comments": ph_comments, "ph_med3": ph_med3,
                # 103–105 Affirm + tech
                "affirm": affirm, "ip_address": ip_addr, "jornaya": jornaya
            }
            st.success("Wagstaff answers saved in session. Use Export below to download.")

    colA, colB, colC = st.columns([1,1,2])
    with colA:
        if st.button("Back to Intake"):
            st.session_state.step = "intake"; st.rerun()
    with colB:
        if st.button("Export Wagstaff CSV"):
            payload = {"firm":"Wagstaff"}
            if "intake_payload" in st.session_state: payload.update(st.session_state.intake_payload)
            payload.update(st.session_state.answers_wag)
            df = pd.DataFrame([payload])
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download wagstaff_followup.csv", data=csv_bytes, file_name="wagstaff_followup.csv", mime="text/csv", key="dl_wag_csv_btn")
    with colC:
        st.caption("All 1–105 Wagstaff questions implemented. Tell me any wording tweaks or required fields.")

# =========================
# TRITEN PLACEHOLDER (send exact list to wire)
# =========================
def render_triten_questions():
    st.header("Triten – Follow-up Questions (placeholder)")
    st.info("Send your exact Triten question list and field types and I’ll wire them in.")
    q1 = st.date_input("Earliest report date (any channel)", value=TODAY.date(), key="tri_q1")
    q2 = st.text_input("Rideshare case/incident #", key="tri_q2")
    q3 = st.checkbox("Driver made explicit sexual/physical threats", key="tri_q3")
    q4 = st.checkbox("Off-route / False imprisonment", key="tri_q4")
    q5 = st.text_area("Physical or psychological injuries (summary)", key="tri_q5")
    q6 = st.checkbox("Ongoing therapy/treatment", key="tri_q6")

    st.session_state.answers_tri = {
        "earliest_report_date": str(q1), "rs_case_no": q2,
        "threats": q3, "offroute_or_fi": q4,
        "injuries": q5, "therapy": q6
    }
    colA, colB = st.columns([1,1])
    with colA:
        if st.button("Back to Intake"):
            st.session_state.step = "intake"; st.rerun()
    with colB:
        if st.button("Export Triten CSV"):
            payload = {"firm":"Triten"}
            if "intake_payload" in st.session_state: payload.update(st.session_state.intake_payload)
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
