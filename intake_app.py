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
    """Show a visible coaching/script block under a field."""
    if not text: return
    st.markdown(f"<div class='script'>{text}</div>", unsafe_allow_html=True)

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
# WAGSTAFF QUESTION FLOW WITH NUMBERS & VISIBLE SCRIPTS
# =========================
def render_wagstaff_questions():
    st.header("Wagstaff – Detailed Questionnaire")

    with st.form("wagstaff_form", clear_on_submit=False):
        # 1–4 Narrative
        st.subheader("1–4. Narrative")
        s1 = st.text_area("1. Statement of the Case")
        script_block("Agent Response: Encourage a concise, chronological statement. Reflect key terms for accuracy.")
        s2 = st.text_area("2. Burden")
        script_block("Agent Response: Clarify expectations and the firm's process; reassure about confidentiality.")
        s3 = st.text_area("3. Icebreaker")
        script_block("Agent Response: Use a gentle opener to build rapport. Keep tone supportive and neutral.")
        s4 = st.text_area("4. Comments")
        script_block("Agent Response: Note anything unusual, hesitations, or language needs.")

        # 5–18 Client Contact
        st.markdown("---")
        st.subheader("Client Contact Details (5–18)")
        ccols = st.columns([1,1,1])
        with ccols[0]:
            c_first = st.text_input("5. First Name")
        with ccols[1]:
            c_middle = st.text_input("5. Middle Name")
        with ccols[2]:
            c_last = st.text_input("5. Last Name")
        script_block("Agent Response: Confirm legal name spelling exactly as on ID if possible.")
        c_email = st.text_input("6. Primary Email")
        script_block("Agent Response: Verify spelling; ask to repeat slowly if needed.")
        c_addr = st.text_input("7. Mailing Address")
        c_city = st.text_input("8. City")
        c_state = st.selectbox("9. State", STATE_OPTIONS, index=(STATE_OPTIONS.index("Georgia") if "Georgia" in STATE_OPTIONS else 0))
        c_zip = st.text_input("10. Zip")
        script_block("Agent Response: Confirm apartment/unit numbers where applicable.")
        c_home = st.text_input("11. Home Phone No.", placeholder="+1 (###) ###-####")
        c_cell = st.text_input("12. Cell Phone No.", placeholder="(###) ###-####")
        script_block("Agent Response: Ask which number is best for call-backs and voicemail.")
        c_best_time = st.text_input("13. Best Time to Contact")
        c_pref_method = st.text_input("14. Preferred Method of Contact")
        c_dob = st.date_input("15. Date of Birth", value=TODAY.date())
        c_ssn = st.text_input("16. Social Security No.", placeholder="000-00-0000")
        script_block("Agent Response: Only request SSN if firm policy requires; mention security.")
        c_claim_for = st.radio("17. Does the claim pertain to you or another person?", ["Myself","Someone Else"], horizontal=True)
        script_block("Agent Response: If 'Someone Else', capture relationship and authority later.")
        c_prev_firm = st.text_area("18. Prior signup with a firm and disqualified? (explain)")
        script_block("Agent Response: Neutral tone. Prior rejection doesn't automatically disqualify; we just need context.")

        # 19–27 Injured Party
        st.markdown("---")
        st.subheader("Injured Party Details (19–27)")
        ip_name = st.text_input("19. Injured/Deceased Party's Full Name")
        ip_gender = st.text_input("20. Injured Party Gender")
        ip_dob = st.date_input("21. Injured/Deceased Party's DOB", value=TODAY.date())
        ip_ssn = st.text_input("22. Injured/Deceased Party's SS#", placeholder="000-00-0000")
        script_block("Agent Response: If caller is not the injured party, confirm authority to share SSN/DOB.")
        ip_relationship = st.text_input("23. PC's Relationship to Injured/Deceased")
        ip_title = st.multiselect("24. Title to Represent", ["Executor","Administrator","Trustee","Conservator","Legal Guardian","Parent","Power of Attorney","Other Agent"])
        ip_has_poa = st.radio("25. Does caller have POA or other legal authority?", ["Yes","No"], horizontal=True)
        ip_has_proof = st.radio("26. Does caller have proof of legal authority?", ["Yes","No"], horizontal=True)
        ip_reason_no_discuss = st.selectbox("27. Reason PC cannot discuss case", ["Select","Minor","Incapacitated","Death","Other"])
        script_block("Agent Response: If 'Other', capture brief reason; do not pressure for sensitive details.")

        # 28–33 Death
        st.markdown("---")
        st.subheader("Death Details (28–33)")
        is_deceased = st.radio("28. Is the client deceased?", ["No","Yes"], horizontal=True)
        if is_deceased == "Yes":
            script_block("Agent Response: Be empathetic; slow pace; avoid leading questions.")
        dod = st.date_input("29. Date of Death (if applies)", value=TODAY.date()) if is_deceased=="Yes" else None
        cod = st.text_input("30. Cause of Death on Death Cert") if is_deceased=="Yes" else ""
        death_state = st.selectbox("31. In what state did the death occur?", STATE_OPTIONS) if is_deceased=="Yes" else ""
        has_death_cert = st.radio("32. Do you have a death certificate?", ["No","Yes"], horizontal=True) if is_deceased=="Yes" else "No"
        right_to_claim_docs = st.text_area("33. Documentation of your right to the decedent’s claim?")
        if is_deceased == "Yes":
            script_block("Agent Response: Ask if a copy can be provided; explain secure transfer options.")

        # 34–37 Emergency Contact
        st.markdown("---")
        st.subheader("Alternate / Emergency Contact (34–37)")
        ec_name = st.text_input("34. Alternate/Emergency Contact Name")
        ec_relation = st.text_input("35. Alternate/Emergency Contact Relation to Client")
        ec_phone = st.text_input("36. Alternate/Emergency Contact Number", placeholder="+1 (###) ###-####")
        ec_email = st.text_input("37. Alternate/Emergency Contact Email")
        script_block("Agent Response: This is optional but helpful if we can't reach the primary contact.")

        # 38–51 Incident
        st.markdown("---")
        st.subheader("Incident Details (38–51)")
        was_driver_or_rider = st.radio("38. Were you the driver or rider during this incident?", ["Driver","Rider"], horizontal=True)
        if was_driver_or_rider == "Rider":
            script_block("If Rider: Okay, you were the rider. Thank you for clarifying that — this helps us understand who had control of the vehicle.")
        else:
            script_block("If Driver: Okay. You were the driver — thank you for sharing that. Unfortunately, the law firm is not currently taking cases where the driver was assaulted. I’m really sorry we cannot help you.")

        incident_narr = st.text_area("39. Describe what happened (purpose of rideshare, location, seat, moving/stopped)")
        script_block("Agent Response: “Thank you for sharing that with me. You said '[mirror key words]' — and that sounds incredibly difficult. This space is confidential.”")

        has_incident_date = st.checkbox("40. Do you have the date the incident occurred?")
        if has_incident_date:
            incident_date_known = st.date_input("40.a Incident Date", value=TODAY.date())
            script_block("Agent Response: “Got it. The date was [repeat date]. The timing helps us document and connect the ride.”")
        else:
            incident_date_known = None

        rs_company = st.selectbox("41. Which Rideshare company did you use?", ["Uber","Lyft","Other"])
        script_block("Agent Response: “[Company], got it. This helps determine responsibility and verify who operated the ride.”")

        us_occurrence = st.radio("42. Did the incident occur within the United States?", ["Yes","No"], horizontal=True)
        script_block("Agent Response: If 'No', note the country/jurisdiction briefly for conflicts checks.")

        incident_state = st.selectbox("43. What state did this happen?", STATE_OPTIONS)
        script_block("Agent Response: “Okay. [Repeat state]. Thank you.”")

        pickup_addr = st.text_input("44. Pick-up location (full address)")
        script_block("Agent Response: “You were picked up from [repeat location]. Helps reconstruct the trip.”")

        dropoff_addr = st.text_input("45. Drop-off location (full address)")
        script_block("Agent Response: “You were dropped off at [location]. Helps build out the trip details.”")

        sexually_assaulted = st.radio("46. Were you sexually assaulted or inappropriately touched by the driver?", ["No","Yes"], horizontal=True)
        if sexually_assaulted == "Yes":
            script_block("Agent Response: “I’m really sorry to hear you were [repeat relevant details]. Thank you for trusting us.”")
        else:
            script_block("Agent Response: If 'No', continue neutrally; do not minimize verbal/other harms.")

        fi_kidnapping = st.radio("47. False imprisonment or kidnapping (restraint/restriction) with threats?", ["No","Yes"], horizontal=True)
        if fi_kidnapping == "Yes":
            script_block("Agent Response: “That sounds terrifying — we want to ensure the firm understands how serious this was.”")

        verbal_harassment = st.radio("48. Were you subjected to verbal harassment?", ["No","Yes"], horizontal=True)
        if verbal_harassment == "Yes":
            script_block("Agent Response: “Even when it’s not physical, those moments are serious and deserve to be heard.”")

        inside_or_near = st.radio("49. Did this occur while using the Rideshare service (inside or just outside the vehicle)?", ["No","Yes"], horizontal=True)
        if inside_or_near == "Yes":
            script_block("Agent Response: “Knowing that it happened while using the rideshare helps confirm scope of responsibility.”")

        driver_weapon = st.text_input("50. Did the driver threaten to use or actually use any weapons/force? (describe)")
        if driver_weapon.strip():
            script_block("Agent Response: “Thank you. That’s very serious; details help paint a full picture.”")
        else:
            script_block("Agent Response: If no weapon, reassure: the incident is still serious.")

        client_weapon = st.radio("51. Were you carrying a weapon at the time? (Personal defense like pepper spray may not count)", ["No","Yes"], horizontal=True)
        if client_weapon == "Yes":
            script_block("Agent Response: “Thanks for your honesty. Some guidelines may disqualify where the victim had a weapon.”")
        else:
            script_block("Agent Response: “Okay, you did not have a weapon with you. That’s all we need on that part.”")

        # 52–61 Reporting/Treatment
        st.markdown("---")
        st.subheader("Reporting & Treatment Details (52–61)")
        has_receipt = st.radio("52. Are you able to reproduce the Rideshare receipt?", ["Yes","No"], horizontal=True)
        if has_receipt == "Yes":
            script_block("Agent Response: “Great—you can access it via the app or email. It’s key proof linking ride to incident.”")
        else:
            script_block("Agent Response: “Please try the app/email; we can guide you. It’s important evidence.”")

        reported_channels = st.multiselect(
            "53. Did you report the incident to any of the following?",
            ["Rideshare Company","Physician","Friend or Family Member","Therapist","Police Department","NO (DQ, UNLESS TIER 1 OR MINOR)"]
        )
        if reported_channels:
            script_block(f"Agent Response: “Good—you reported to {', '.join(reported_channels)}. That shows you took steps to get help.”")
        else:
            script_block("Agent Response: “Not reporting can make it difficult to pursue, but we’ll note it and advise.”")

        rs_submit_how = st.text_input("54. If submitted to Rideshare: how did you submit (email/app)?")
        if rs_submit_how.strip():
            script_block("Agent Response: “Submitted via {email/app} is fine—thanks for clarifying.”")

        willing_to_report = st.radio("55. If not submitted via app/email: willing to report if the firm recommends?", ["Yes","No","Unsure"], horizontal=True)
        if willing_to_report == "Yes":
            script_block("Agent Response: “Thank you for being open. The firm will guide you step-by-step if needed.”")
        elif willing_to_report == "No":
            script_block("Agent Response: “Understood. If it becomes important later, the firm will discuss options.”")
        else:
            script_block("Agent Response: “No problem—if the firm recommends it later, they’ll walk you through it.”")

        rs_received_response = st.radio("56. Did you receive a response from Uber or Lyft?", ["No","Yes"], horizontal=True)
        if rs_received_response == "Yes":
            script_block("Agent Response: “Got it—please forward any emails or screenshots you received.”")
        else:
            script_block("Agent Response: “That can be frustrating. We’ll document that there was no response.”")

        report_contact_info = st.text_area("57. Contact info for the person/entity reported to (Name, Relationship, Address, Phone, Date Reported)")
        if report_contact_info.strip():
            script_block("Agent Response: “Perfect—that helps us corroborate your report.”")

        # 58–61 If called Uber/Lyft
        st.subheader("If PC called Uber or Lyft (58–61)")
        where_found_number = st.text_input("58. Where did you find the phone number you called?")
        if where_found_number.strip():
            script_block("Agent Response: “Thanks. Many call numbers found online or in emails—your source helps us verify.”")

        got_case_number = st.radio("59. Did you receive a confirmation or case number from that call?", ["No","Yes"], horizontal=True)
        if got_case_number == "Yes":
            script_block("Agent Response: “Great—that helps track whether Uber created an internal file.”")
        else:
            script_block("Agent Response: “Okay—many callers don’t receive a case number. We’ll document it.”")

        who_answered = st.text_input("60. On the call, did someone say they were with Uber/Lyft or just take info?")
        if who_answered.strip():
            script_block("Agent Response: “Thanks—that clarifies who you spoke to; many aren’t sure.”")

        follow_up_after_call = st.text_area("61. Any follow-up after the call (email/app/instructions)? Or none?")
        if follow_up_after_call.strip():
            script_block("Agent Response: “Thanks—please forward any message you received for the record.”")
        else:
            script_block("Agent Response: “Not hearing back is common; we’ll note that there was no follow-up.”")

        # 62–68 Medical
        st.markdown("---")
        st.subheader("Medical Treatment Details (62–68)")
        forms_signed_for_records = st.text_input("62. Signed any forms to obtain medical records? (Who?)")
        med_treated = st.radio("63. Received medical treatment for physical injuries?", ["No","Yes"], horizontal=True)
        med_treatment_desc = st.text_area("64. Describe medical treatment")
        med_doctor = st.text_input("65. Doctor who diagnosed you")
        med_facility = st.text_input("66. Hospital/Facility where diagnosis was done")
        med_address = st.text_input("67. Hospital/Facility/Doctor's Address")
        med_phone = st.text_input("68. Hospital/Facility/Doctor's Phone Number", placeholder="+1 (###) ###-####")
        if med_treated == "Yes":
            script_block("Agent Response: “Thank you—treatment details help establish damages and timeline.”")

        # 69–77 MH1
        st.markdown("---")
        st.subheader("Mental Health Treatment Details 1 (69–77)")
        mh1_yes = st.radio("69. Received mental health treatment related to the assault?", ["No","Yes"], horizontal=True)
        mh1_desc = st.text_area("70. Describe mental health treatment so far (general)")
        mh1_doctor = st.text_input("71. Name of the doctor who treated you")
        mh1_hospital = st.text_input("72. Hospital where you received treatment")
        mh1_address = st.text_input("73. Hospital's Address")
        mh1_phone = st.text_input("74. Hospital's Phone Number", placeholder="+1 (###) ###-####")
        mh1_website = st.text_input("75. Hospital's Website Address")
        mh1_diagnosis = st.text_input("76. Diagnosed Ailment / Diagnosis Date(s)")
        mh1_treatment = st.text_area("77. Treatment Type / Treatment Date(s) (detail)")
        if mh1_yes == "Yes":
            script_block("Agent Response: “Understood—documenting therapy and diagnosis supports the case.”")

        # 78–86 MH2
        st.markdown("---")
        st.subheader("Mental Health Treatment Details 2 (78–86)")
        mh2_yes = st.radio("78. Received mental health treatment related to the assault? (second set)", ["No","Yes"], horizontal=True)
        mh2_desc = st.text_area("79. Describe mental health treatment so far (general) (2)")
        mh2_doctor = st.text_input("80. Name of the doctor who treated you (2)")
        mh2_hospital = st.text_input("81. Hospital where you received treatment (2)")
        mh2_address = st.text_input("82. Hospital's Address (2)")
        mh2_phone = st.text_input("83. Hospital's Phone Number (2)", placeholder="+1 (###) ###-####")
        mh2_website = st.text_input("84. Hospital's Website Address (2)")
        mh2_diagnosis = st.text_input("85. Diagnosed Ailment / Diagnosis Date(s) (2)")
        mh2_treatment = st.text_area("86. Treatment Type / Treatment Date(s) (2) — detail")
        if mh2_yes == "Yes":
            script_block("Agent Response: “Thanks—capturing all providers ensures complete records.”")

        # 87–94 Additional providers
        st.markdown("---")
        st.subheader("Additional Medical / Mental Health Providers (87–94)")
        am_name = st.text_input("87. Doctor/Facility Name")
        am_address = st.text_input("88. Address")
        am_phone = st.text_input("89. Phone Number", placeholder="+1 (###) ###-####")
        am_website = st.text_input("90. Website Address")
        am_diagnosis = st.text_input("91. Diagnosed Ailment / Diagnosis Date(s)")
        am_symptoms = st.text_input("92. Symptom(s)")
        am_treatment = st.text_input("93. Treatment Type / Treatment Date(s)")
        am_comments = st.text_area("94. Comments")
        script_block("Agent Response: Add any other clinics, urgent care, or counselors not already listed.")

        # 95–103 Pharmacy
        st.markdown("---")
        st.subheader("Pharmacy for Medications (95–103)")
        ph_name = st.text_input("95. Pharmacy Name")
        ph_phone = st.text_input("96. Phone", placeholder="+1 (###) ###-####")
        ph_website = st.text_input("97. Website")
        ph_address = st.text_input("98. Full Street, City, Zip Address")
        ph_med1 = st.text_input("99. Ailment / Medication / Dates Prescribed")
        ph_med2 = st.text_input("100. Ailment / Medication / Dates Prescribed")
        ph_comments = st.text_area("101. Comments")
        ph_med3 = st.text_input("102. Ailment / Medication / Date Prescribed")
        script_block("Agent Response: Pharmacy records can corroborate treatment and timing.")

        affirm = st.radio("103. Do you affirm the accuracy of all information (including prior firm signup)?", ["Yes","No"], horizontal=True)
        if affirm == "Yes":
            script_block("Agent Response: “Thank you—your confirmation is noted.”")
        else:
            script_block("Agent Response: “No problem—we can correct anything as needed before submission.”")

        # 104–105 Technical
        st.markdown("---")
        st.subheader("Technical (104–105)")
        ip_addr = st.text_input("104. IP Address")
        jornaya = st.text_area("105. Trusted Form / Jornaya Data")
        script_block("Agent Response: These are for verification only; do not share externally.")

        # Save
        submitted = st.form_submit_button("Save Wagstaff Answers")
        if submitted:
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
                # 58–61 call branch
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
            st.success("Wagstaff answers saved. Use Export below to download.")

    # Footer
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
        st.caption("All questions 1–105 include visible agent script blocks. Dynamic lines switch based on answers.")

# =========================
# TRITEN PLACEHOLDER (send exact list to wire)
# =========================
def render_triten_questions():
    st.header("Triten – Follow-up Questions (placeholder)")
    q1 = st.date_input("T1. Earliest report date (any channel)", value=TODAY.date())
    q2 = st.text_input("T2. Rideshare case/incident #")
    q3 = st.checkbox("T3. Driver made explicit sexual/physical threats")
    q4 = st.checkbox("T4. Off-route / False imprisonment")
    q5 = st.text_area("T5. Physical or psychological injuries (summary)")
    q6 = st.checkbox("T6. Ongoing therapy/treatment")

    st.session_state.answers_tri = {
        "T1_earliest_report_date": str(q1), "T2_rs_case_no": q2,
        "T3_threats": q3, "T4_offroute_or_fi": q4,
        "T5_injuries": q5, "T6_therapy": q6
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
