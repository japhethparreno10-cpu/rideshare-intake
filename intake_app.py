import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta

# =========================
# PAGE SETUP & STYLES
# =========================
st.set_page_config(page_title="Rideshare Intake Qualifier + Coach", layout="wide")

st.markdown("""
<style>
h1 {font-size: 2.0rem !important;}
h2 {font-size: 1.5rem !important; margin-top: 0.6rem;}
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
STATE_ALIAS = {"Washington DC": "D.C.", "District of Columbia": "D.C."}
STATES = sorted(set(list(TORT_SOL.keys()) + list(WD_SOL.keys()) + ["D.C."]))

# =========================
# HELPERS (script rendering)
# =========================
def script_block(text: str):
    if not text: return
    st.markdown(f"<div class='script'>{text}</div>", unsafe_allow_html=True)

def badge(ok: bool, label: str):
    css = "badge-ok" if ok else "badge-no"
    st.markdown(f"<div class='{css}'>{label}</div>", unsafe_allow_html=True)

def fmt_date(dt): return dt.strftime("%Y-%m-%d") if dt else "—"
def fmt_dt(dt): return dt.strftime("%Y-%m-%d %H:%M") if dt else "—"

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

# =========================
# HEADER + REFERENCE
# =========================
st.title("Rideshare Intake Qualifier · with Agent Coach")

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
# INTAKE + COACH
# =========================
def render_intake_and_decision():
    st.header("Intake")

    # Intro / rapport scripting (always visible)
    intro_c1, intro_c2 = st.columns([1,1])
    with intro_c1:
        client = st.text_input("Client Name", placeholder="e.g., Jane Doe")
    with intro_c2:
        company = st.selectbox("Rideshare company", ["Uber", "Lyft"])

    # Intro script reacts to name
    intro_text = f"""
Thank you for calling about the rideshare assault claim. Can I have your full name, please, so we can help you better?

I'm sorry this happened to you{f", {client}" if client else ""}. You're not alone—many have come forward, and we're here to help you seek justice. Everything you share will remain private, and no evidence will be filed without your approval.

In order for us to proceed, the law firm requires two things: **the email copy of the receipt of the ride** and **your ID** (you may send the ID later).
"""
    script_block(intro_text)

    # Basics
    top3 = st.columns([1,1,1])
    with top3[0]:
        state = st.selectbox("Incident State", STATES, index=STATES.index("California") if "California" in STATES else 0)
    with top3[1]:
        incident_time = st.time_input("Incident Time", value=time(21, 0))
    with top3[2]:
        incident_date = st.date_input("Incident Date", value=TODAY.date())

    # First-level qualification toggles
    row2 = st.columns(6)
    with row2[0]:
        female_rider = st.toggle("Female rider", value=True)
    with row2[1]:
        receipt = st.toggle("Receipt provided (email/PDF/app)", value=True)
        if not receipt:
            st.markdown("**Ask:** Do you have an email receipt for the ride and a screenshot?")
            st.markdown("<div class='callout'><b>Text to send:</b><br><span class='copy'>Forward your receipt to <b>keren@advocaterightscenter.com</b> by selecting the ride in Ride History and choosing “Resend Receipt.”\n(Msg Rates Apply. Txt STOP to cancel/HELP for help)</span></div>", unsafe_allow_html=True)
            st.markdown("<div class='copy'>Forward your receipt to <b>keren@advocaterightscenter.com</b>\n(Msg Rates Apply. Txt STOP to cancel/HELP for help)</div>", unsafe_allow_html=True)
            if company == "Uber":
                st.markdown("<div class='script'><b>Uber steps:</b> Activity ➜ select the correct ride ➜ receipt icon above pickup address ➜ Resend email receipt.</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='script'><b>Lyft steps:</b> Ride history ➜ select correct ride ➜ Receipt icon ➜ Resend email receipt.</div>", unsafe_allow_html=True)
    with row2[2]:
        gov_id = st.toggle("ID provided", value=True)
        if not gov_id:
            script_block("""We need a government ID to ensure any settlement is paid to the right person. We will **not** ask for banking details at this stage.

**Why:**  
• Verification prevents impersonation and false claims.  
• Medical records: ID allows HIPAA-compliant requests.  
• Settlement accuracy: funds go to the correct person.""")

            st.markdown("<div class='callout'><b>Text to send:</b> “For identity verification, please upload your ID here: [your link].”</div>", unsafe_allow_html=True)

    with row2[3]:
        inside_near = st.toggle("Incident inside/just outside/started near car", value=True)
        if inside_near:
            script_block("Thanks — confirming it happened while using the service helps establish rideshare responsibility for safe transport.")
    with row2[4]:
        has_atty = st.toggle("Already has an attorney", value=False)
        if has_atty:
            script_block("Thank you for letting me know. Because another attorney already represents you on this claim, we can’t proceed with intake.")
        else:
            st.caption("If ‘No’, use this probe before firm contact:")
            script_block("Before the law firm reaches out, could you tell me what happened in your own words? This space is confidential.")
    with row2[5]:
        # Driver weapon (what happened in the car) vs client carrying weapon (next row)
        weapon = st.selectbox("Driver weapon/force used?", ["No","Non-lethal defensive (e.g., pepper spray)","Yes"])
        if weapon == "Yes":
            script_block("Understood. That’s very serious. Please describe what was threatened or used (e.g., gun, knife, choking).")

    # Additional disqualifiers / probes row
    row3 = st.columns(3)
    with row3[0]:
        verbal_only = st.toggle("Verbal abuse only (no sexual contact/acts)", value=False)
        if verbal_only:
            script_block("Thank you for explaining. We’ll document everything carefully, even when it was not physical.")
    with row3[1]:
        attempt_only = st.toggle("Attempt/minor contact only", value=False)
        if attempt_only:
            script_block("Thanks for clarifying there was an attempt or minor contact. I’m sorry you went through that.")
    with row3[2]:
        client_weapon = st.toggle("Client carrying a weapon?", value=False)
        if client_weapon:
            script_block("Thanks for your honesty. Some firms won’t accept cases where the victim had a weapon; we’ll make sure the team evaluates this carefully.")

    # Acts (map to Tier)
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
        if felony:
            script_block("""Also, do you have any felony records? We ask this to ensure there are no legal issues that could impact or weaken your case. 
This helps us prepare if the other side tries to use your past against you. It’s a standard part of handling your case and doesn’t reflect on your character.""")

    # Narrative probes (always available)
    st.subheader("Narrative (probing prompts)")
    narr = st.text_area("Can you tell me what happened during your ride? (free narrative)")
    qcol1, qcol2 = st.columns(2)
    with qcol1:
        where_to = st.text_input("Where were you going? (use receipt for address/business)")
        seat = st.selectbox("Where were you seated?", ["—","Front","Back","Other"])
    with qcol2:
        exit_how = st.text_input("How did you exit the car?")
        company_confirm = company  # echoed in script

    if narr.strip():
        script_block('“That must have been terrifying. I’m really sorry you experienced this. Let’s confirm some details to build your case.”')

    # Reporting
    reported_to = st.multiselect(
        "Reported To (choose all that apply)",
        ["Rideshare company","Police","Therapist","Medical professional","Physician","Family/Friends","Audio/Video evidence"],
        default=[]
    )
    if not reported_to:
        script_block("It’s okay if you haven’t reported yet. If the firm recommends it later, they’ll guide you step by step.")
    else:
        script_block(f"Good to know you reported to {', '.join(reported_to)} — that helps show you sought help and can support your case.")

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

    # Wrongful death (kept minimal)
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
        "VerbalOnly": verbal_only, "AttemptOnly": attempt_only, "ClientCarryingWeapon": client_weapon,
        "Rape/Penetration": rape, "Forced Oral/Forced Touching": forced_oral,
        "Touching/Kissing w/o Consent": touching, "Indecent Exposure": exposure,
        "Masturbation Observed": masturb, "Kidnapping Off-Route w/ Threats": kidnap,
        "False Imprisonment w/ Threats": imprison, "WrongfulDeath": wd,
        "DateOfDeath": datetime.combine(date_of_death, time(12, 0)) if wd and date_of_death else None,
        "Narrative": narr, "WhereTo": where_to, "Seat": seat, "ExitHow": exit_how
    }

    # Tier + timing
    tier_label, _ = tier_and_aggravators(state_data)
    common_ok = all([female_rider, receipt, gov_id, inside_near, not has_atty])

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

    earliest_report_date = None
    all_dates = [d for d in report_dates.values() if d]
    if family_report_dt: all_dates.append(family_report_dt.date())
    if all_dates: earliest_report_date = min(all_dates)
    delta_days = (earliest_report_date - incident_dt.date()).days if earliest_report_date else None
    triten_report_ok = (delta_days is not None) and (0 <= delta_days <= 14)

    # Validation
    if earliest_report_date and earliest_report_date < incident_dt.date():
        st.warning("Earliest report date is before the incident date. Please double-check.")

    # Wagstaff (reference only)
    wag_disq, reported_to_set = [], set(reported_to) if reported_to else set()
    if felony: wag_disq.append("Felony record → Wagstaff requires no felony history")
    if weapon == "Yes": wag_disq.append("Weapon involved → disqualified under Wagstaff")
    if client_weapon: wag_disq.append("Victim carrying a weapon → may disqualify under some firm rules")
    if verbal_only: wag_disq.append("Verbal abuse only → does not qualify")
    if attempt_only: wag_disq.append("Attempt/minor contact only → does not qualify")
    if has_atty: wag_disq.append("Already has attorney → cannot intake")

    within_24h_family_ok, missing_family_dt = True, False
    if reported_to_set == {"Family/Friends"}:
        if not family_report_dt:
            within_24h_family_ok = False; missing_family_dt = True
            wag_disq.append("Family/Friends-only selected but date/time was not provided")
        else:
            delta = family_report_dt - incident_dt
            within_24h_family_ok = (timedelta(0) <= delta <= timedelta(hours=24))
            if not within_24h_family_ok:
                wag_disq.append("Family/Friends-only report exceeded 24 hours after incident → fails Wagstaff rule")

    base_tier_ok = ("Tier 1" in tier_label) or ("Tier 2" in tier_label)
    wag_ok = common_ok and wagstaff_time_ok and within_24h_family_ok and base_tier_ok and not wag_disq

    # Triten (reference only)
    tri_disq = []
    if verbal_only: tri_disq.append("Verbal abuse only → does not qualify")
    if attempt_only: tri_disq.append("Attempt/minor contact only → does not qualify")
    if earliest_report_date is None: tri_disq.append("No report date provided for any channel")
    if not triten_report_ok: tri_disq.append("Report not within 2 weeks (based on earliest report date)")
    if has_atty: tri_disq.append("Already has attorney → cannot intake")
    triten_ok = common_ok and triten_report_ok and base_tier_ok and not tri_disq

    # Badges
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

    # Company policy (reference text only)
    if company == "Uber":
        st.info("Company rule: Uber → Wagstaff and Triten are options (priority often Triten if both eligible).")
    else:
        st.info("Company rule: Lyft → Triten only.")

    # NOTES (reasons)
    st.subheader("Eligibility Notes")
    st.markdown("### Wagstaff")
    if wag_ok:
        st.markdown(f"<div class='note-wag'>Meets screen.</div>", unsafe_allow_html=True)
    else:
        reasons = []
        if wag_disq: reasons.extend(wag_disq)
        if not wagstaff_time_ok: reasons.append("Past Wagstaff filing window (must file 45 days before SOL).")
        if not base_tier_ok: reasons.append("Tier unclear (select Tier 1 or Tier 2 qualifying acts).")
        if reasons:
            for r in reasons: st.markdown(f"<div class='note-wag'>{r}</div>", unsafe_allow_html=True)
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
            for r in reasons: st.markdown(f"<div class='note-tri'>{r}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='note-muted'>No specific reason captured.</div>", unsafe_allow_html=True)

    # SUMMARY TABLE
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
    }
    st.dataframe(pd.DataFrame([decision]), use_container_width=True, height=320)

    # ============== LIVE COACH PANELS (logic + emotion + hire + who we are) ==============
    st.header("Agent Coach · Talking Points")

    with st.expander("Educate for Logic (use when survivor seeks context)"):
        st.markdown("""
Survivors are coming forward about rideshares because Uber and Lyft have been found to improperly screen drivers.  
In 2018, **~3,000** sexual assaults were reported **that year alone**; including 2017 brings the total near **6,000**.  
Many incidents go unreported, so coming forward can help you and others get justice.
""")
        st.markdown("""
*Optional depth (use only if needed):* Since 2014, Uber knew dangerous drivers were on the platform and assaults were happening.  
They introduced a **$1 ‘Safe Rides Fee’** to pay for safety features, but much of it became revenue (hundreds of millions) without fixing core safety gaps. The fee was later renamed to **“booking fee.”**
""")

    with st.expander("Education for Emotion (validation + purpose)"):
        st.markdown("""
I’m sorry you’re going through this. I know this isn’t about the money, and we can’t change the pain you’ve endured.  
However, pursuing a settlement can provide closure and help protect others.
""")
        st.markdown("""
*Optional (if helpful):* Coming forward sends a message that rideshare companies cannot prioritize profits over safety.  
They failed to warn about known risks, which took away your right to make an informed decision.
""")

    with st.expander("Discuss & Summarize (when Tier 1/2 likely)"):
        st.markdown("""
It sounds like you may have a valid case to pursue a settlement because of what happened.  
The process is straightforward and not stressful: you **hire a law firm on contingency** — no upfront payments and nothing owed unless they win.
""")

    with st.expander("Hire a Law Firm (who we are + options)"):
        st.markdown("""**Wagstaff Law Firm** — Super Lawyers on staff (top ~5%), national leadership on corporate negligence, nine Plaintiff Steering Committees; holding Uber/Lyft accountable.""")
        st.markdown("""**Chaffin Luhana (Triten channel)** — Super Lawyers; 1,200+ five-star reviews; $1B+ recovered; focus on sexual assault nationwide; can connect clients with support such as **RAINN**.""")
        st.markdown("""**Estey & Bomberger** — Trial firm; sexual assault litigation; national reach.""")

    with st.expander("Settlements Timeframe (high-level)"):
        st.markdown("""
After initial motions and discovery, **four one-month Bellwether Test Trials** are scheduled focusing on different assault types.  
Their outcomes guide settlement ranges, reducing the need for you to retell your story. Your settlement will align with your experience.
""")

    with st.expander("Asking SSN (use only when green-lit by firm)"):
        st.markdown("""
We have one more item to protect your benefits and identity so any settlement goes to the right person.  
**May we collect your Social Security Number?**  
This prevents impersonation or relatives falsely claiming funds and avoids financial issues. We will not request banking details until a settlement is confirmed.
""")
        ssn_collect = st.toggle("Collected SSN now? (store securely per firm policy)", value=False)

    with st.expander("Asking ID (if not yet provided)"):
        st.markdown("""
**Text to send:**  
For identity verification please upload your ID by clicking here: **[your secure upload link]**.

**Why this matters**  
1. Verification prevents impersonation and false claims.  
2. Medical records can be requested under HIPAA.  
3. Ensures settlement funds go to the correct person (no banking details requested now).
""")

    with st.expander("Who We Are / Contact Cards (read as needed)"):
        st.markdown("""
**Triten / Chaffin Luhana LLP Injury Lawyers**  
615 Iron City Dr, Pittsburgh, PA 15205 · (412) 345-8144 · chaffinluhana.com
""")
        st.markdown("""
**Estey & Bomberger, LLP**  
2869 India St, San Diego, CA 92103 · (800) 260-7197 · ebtrialattorneys.com
""")
        st.markdown("""
**Wagstaff Law Firm**  
940 Lincoln St, Denver, CO 80203 · wagstafflawfirm.com
""")
        st.markdown("""
*Follow-up expectation:* Legal assistants will call within ~5 days to confirm next steps (e.g., Lorenia 213-347-9246 or Kim 213-770-1340).
""")

    with st.expander("Commitment & Keep Lines Open (closing)"):
        st.markdown("""
Thank you for doing this. I know you have the courage to continue and help women who can’t speak up.  
The attorneys will call to confirm details and your decision to move forward. All information remains confidential — keep your phone available for that call.
""")

    # EXPORT
    st.subheader("Export")
    export_df = pd.DataFrame([state_data]).assign(**decision)
    st.download_button("Download CSV (intake + decision + narrative)",
                       data=export_df.to_csv(index=False).encode("utf-8"),
                       file_name="intake_decision_coached.csv",
                       mime="text/csv")

    st.caption("Coach mode surfaces the right language at the right time. Nothing is sent automatically; it’s all on-screen guidance you can copy verbatim.")

# =========================
# APP ENTRY
# =========================
render_intake_and_decision()
