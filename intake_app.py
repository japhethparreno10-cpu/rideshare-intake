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
STATE_ALIAS = {"Washington DC": "D.C.", "District of Columbia": "D.C."}
STATES = sorted(set(list(TORT_SOL.keys()) + list(WD_SOL.keys()) + ["D.C."]))

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

def tier_and_aggravators(data):
    t1 = bool(data.get("Rape/Penetration") or data.get("Forced Oral/Forced Touching"))
    t2 = bool(data.get("Touching/Kissing w/o Consent") or data.get("Indecent Exposure") or data.get("Masturbation Observed"))
    aggr_kidnap = bool(data.get("Kidnapping Off-Route w/ Threats"))
    aggr_imprison = bool(data.get("False Imprisonment w/ Threats"))
    aggr = []
    if aggr_kidnap: aggr.append("Kidnapping w/ threats")
    if aggr_imprison: aggr.append("False imprisonment w/ threats")
    if t1: base = "Tier 1"
    elif t2: base = "Tier 2"
    else: base = "Unclear"
    label = f"{base} (+ Aggravators: {', '.join(aggr)})" if base in ("Tier 1","Tier 2") and aggr else base
    return label, (base in ("Tier 1","Tier 2") and len(aggr) > 0)

# =========================
# MAIN PAGE
# =========================
st.title("Rideshare Intake Qualifier · with Agent Coach")

def render_intake_and_decision():
    try:
        incident_date = None
        family_report_dt = None
        report_dates = {}

        st.header("Intake")

        L, R = st.columns(2)

        # ================= LEFT =================
        with L:
            st.markdown("**1. Describe what happened (allow claimant to speak freely).**")
            narr = st.text_area(" ", key="q1_narr")
            script_block('Agent Response: Thank you for sharing that with me. You said "[mirror key words]" — and that sounds incredibly difficult. This space is confidential.')

            st.markdown("**3. Are you able to reproduce the ride share receipt to show proof of the ride? (If not, DQ)**")
            receipt = st.toggle("Receipt provided (email/app/PDF)", value=False, key="q3_receipt_toggle")
            if not receipt:
                st.markdown("**If Yes:** Great — the receipt links the trip to the incident.")
                st.markdown("**If No:** Please check your email/app; it’s one of the most important pieces of proof.")
                st.markdown("<div class='callout'><b>Text to send:</b><br><span class='copy'>Forward your receipt to <b>jay@advocaterightscenter.com</b> by selecting the ride in Ride History and choosing “Resend Receipt.”<br>(Msg Rates Apply. Txt STOP to cancel/HELP for help)</span></div>", unsafe_allow_html=True)
                st.markdown("<div class='copy'>Forward your receipt to <b>jay@advocaterightscenter.com</b><br>(Msg Rates Apply. Txt STOP to cancel/HELP for help)</div>", unsafe_allow_html=True)

            st.markdown("**5. Did you report the incident to anyone (Company/Police/Therapist/Physician/Family)?**")
            reported_to = st.multiselect(
                "Select all that apply",
                ["Rideshare Company","Physician","Friend or Family Member","Therapist","Police Department","NO (DQ, UNLESS TIER 1 OR MINOR)"],
                key="q5_reported"
            )
            if reported_to:
                script_block("If Reported: Good — reporting to [repeat answer] shows you sought help and supports your case.")
            else:
                script_block("If Not Reported: That can make a case harder; we may still proceed in certain Tier 1/minor situations.")

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
            script_block("Agent Response: Got it — they [did/did not] respond. That can be frustrating when you expect acknowledgement.")

        # ================= RIGHT =================
        with R:
            st.markdown("**2. Which Rideshare company did you use?**")
            company = st.selectbox(" ", ["Uber","Lyft","Other"], key="q2_company")
            script_block("Agent Response: [Rideshare company], got it. That helps determine responsibility and verify the operator.")

            st.markdown("**4. Do you have the Date the incident occurred?**")
            has_incident_date = st.toggle("Mark ON once claimant confirms they know the date", value=False, key="q4_hasdate")
            if has_incident_date:
                incident_date = st.date_input("Select Incident Date", value=TODAY.date(), key="q4_date")
                script_block("Agent Response: Got it. The date was [repeat date]. That connects the incident to the trip.")
            else:
                script_block("If date is unknown now, note context clues (ride history, calendar, texts) to locate it later.")

            st.markdown("**6. What state did this happen?**")
            state = st.selectbox("Incident State", STATES, index=(STATES.index("California") if "California" in STATES else 0), key="q6_state")
            script_block("Agent Response: Okay. [Repeat state]. Thank you.")

            st.markdown("**8. If submitted to Rideshare: how did you submit? (email/app/other)**")
            rs_submit_how = st.text_input("email / app / other", key="q8_submit_how")
            if rs_submit_how.strip():
                script_block("Agent Response: You submitted via [email/app]. Either method is fine — thanks for sharing.")

            st.markdown("**10. Do you have any felonies or criminal history?**")
            felony = st.toggle("Mark ON only if they confirm a felony/criminal history", value=False, key="q10_felony")
            script_block("If Yes: This helps us prepare for character attacks; it’s standard and doesn’t reflect on your worth.")

        # ===== Eligibility helpers (OFF by default) =====
        st.markdown("---")
        st.caption("Eligibility switches (leave OFF until verified)")
        colE1, colE2, colE3 = st.columns(3)
        with colE1:
            female_rider = st.toggle("Female rider", value=False, key="elig_female")
            if not female_rider:
                script_block("Confirm rider identity if applicable. This aligns with screening rules.")
        with colE2:
            gov_id = st.toggle("ID provided", value=False, key="elig_id")
            if not gov_id:
                script_block("""We’ll need a government ID to ensure any settlement is paid to the right person.
We do **not** ask for bank details now.
• Prevents impersonation
• Allows HIPAA requests
• Ensures funds go to the correct person""")
        with colE3:
            has_atty = st.toggle("Already has an attorney", value=False, key="elig_atty")
            if has_atty:
                script_block("If another attorney already represents you on this claim, we can’t proceed with intake.")

        # Optional incident detail flags (OFF)
        colX1, colX2, colX3, colX4 = st.columns(4)
        with colX1:
            weapon = st.selectbox("Driver used/threatened weapon?", ["No","Non-lethal defensive (e.g., pepper spray)","Yes"], key="elig_driver_weapon")
        with colX2:
            client_weapon = st.toggle("Client carrying a weapon?", value=False, key="elig_client_weapon")
        with colX3:
            verbal_only = st.toggle("Verbal abuse only (no sexual acts)", value=False, key="elig_verbal_only")
        with colX4:
            attempt_only = st.toggle("Attempt/minor contact only", value=False, key="elig_attempt_only")

        # Acts (Tier)
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

        # ========= Decision & Summary =========
        incident_time = st.time_input("Incident Time (for timing rules)", value=time(21, 0), key="time_for_calc")
        safe_incident_date = incident_date or TODAY.date()
        incident_dt = datetime.combine(safe_incident_date, incident_time)

        state_data = {
            "Rape/Penetration": rape,
            "Forced Oral/Forced Touching": forced_oral,
            "Touching/Kissing w/o Consent": touching,
            "Indecent Exposure": exposure,
            "Masturbation Observed": masturb,
            "Kidnapping Off-Route w/ Threats": kidnap,
            "False Imprisonment w/ Threats": imprison
        }
        tier_label, _ = tier_and_aggravators(state_data)
        base_tier_ok = ("Tier 1" in tier_label) or ("Tier 2" in tier_label)

        # SOL + Wagstaff timing
        sol_lookup_state = STATE_ALIAS.get(state, state)
        sol_years = TORT_SOL.get(sol_lookup_state)
        if sol_years:
            sol_end = incident_dt + relativedelta(years=+int(sol_years))
            wagstaff_deadline = sol_end - timedelta(days=45)
            wagstaff_time_ok = TODAY <= wagstaff_deadline
        else:
            sol_end = None
            wagstaff_deadline = None
            wagstaff_time_ok = True  # states not in table won't block Wagstaff on timing

        # Triten earliest report <= 14d
        all_dates = [d for d in report_dates.values() if d]
        if family_report_dt: all_dates.append(family_report_dt.date())
        earliest_report_date = min(all_dates) if all_dates else None
        delta_days = (earliest_report_date - incident_dt.date()).days if earliest_report_date else None
        triten_report_ok = (delta_days is not None) and (0 <= delta_days <= 14)

        if earliest_report_date and earliest_report_date < incident_dt.date():
            st.warning("Earliest report date is before the incident date. Please double-check.")

        # Wagstaff disqualifiers + company rule
        wag_disq = []
        if felony: wag_disq.append("Felony record → Wagstaff requires no felony history")
        if weapon == "Yes": wag_disq.append("Weapon involved → disqualified under Wagstaff")
        if client_weapon: wag_disq.append("Victim carrying a weapon → may disqualify")
        if verbal_only: wag_disq.append("Verbal abuse only → does not qualify")
        if attempt_only: wag_disq.append("Attempt/minor contact only → does not qualify")
        if has_atty: wag_disq.append("Already has attorney → cannot intake")

        # Only Family/Friends reporting must be within 24h
        within_24h_family_ok = True
        if set(reported_to) == {"Friend or Family Member"}:
            if not family_report_dt:
                within_24h_family_ok = False
                wag_disq.append("Family/Friends-only selected but date/time was not provided")
            else:
                delta = family_report_dt - incident_dt
                within_24h_family_ok = (timedelta(0) <= delta <= timedelta(hours=24))
                if not within_24h_family_ok:
                    wag_disq.append("Family/Friends-only report exceeded 24 hours → fails Wagstaff rule")

        # Core screen must-haves
        common_ok = bool(female_rider and receipt and gov_id and inside_near and (not has_atty))

        wag_ok_core = common_ok and wagstaff_time_ok and within_24h_family_ok and base_tier_ok and (not wag_disq)

        # Company policy (Uber only for Wagstaff; Triten ok for Uber & Lyft)
        wag_ok = wag_ok_core and (company == "Uber")
        if company == "Lyft" and wag_ok_core:
            wag_disq.append("Company rule: Lyft → Wagstaff not available (Triten only).")

        # Triten rules
        tri_disq = []
        if verbal_only: tri_disq.append("Verbal abuse only → does not qualify")
        if attempt_only: tri_disq.append("Attempt/minor contact only → does not qualify")
        if earliest_report_date is None: tri_disq.append("No report date provided for any channel")
        if not triten_report_ok: tri_disq.append("Earliest report not within 2 weeks")
        if has_atty: tri_disq.append("Already has attorney → cannot intake")

        triten_ok = bool(common_ok and triten_report_ok and base_tier_ok and (not tri_disq))

        # Badges
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

        # Notes
        st.subheader("Eligibility Notes")
        st.markdown("### Wagstaff")
        if wag_ok:
            st.markdown(f"<div class='note-wag'>Meets screen for Wagstaff (Uber only).</div>", unsafe_allow_html=True)
        else:
            reasons = []
            reasons.extend(wag_disq)
            if not wagstaff_time_ok: reasons.append("Past Wagstaff timing (must file 45 days before SOL).")
            if not base_tier_ok: reasons.append("Tier unclear (needs Tier 1 or Tier 2 acts).")
            if reasons:
                for r in reasons: st.markdown(f"<div class='note-wag'>{r}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='note-muted'>No specific reason captured.</div>", unsafe_allow_html=True)

        st.markdown("### Triten")
        if triten_ok:
            st.markdown(f"<div class='note-tri'>Meets screen for Triten.</div>", unsafe_allow_html=True)
        else:
            reasons = []
            reasons.extend(tri_disq)
            if not base_tier_ok: reasons.append("Tier unclear (needs Tier 1 or Tier 2 acts).")
            if reasons:
                for r in reasons: st.markdown(f"<div class='note-tri'>{r}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='note-muted'>No specific reason captured.</div>", unsafe_allow_html=True)

        # Summary
        st.subheader("Summary")
        sol_end_str = fmt_dt(sol_end) if sol_years else "—"
        wag_deadline_str = fmt_dt(wagstaff_deadline) if sol_years else "—"
        report_dates_str = "; ".join([f"{k}: {fmt_date(v)}" for k, v in report_dates.items()]) if report_dates else "—"
        family_dt_str = fmt_dt(family_report_dt) if family_report_dt else "—"
        decision = {
            "Company": company,
            "Tier (severity-first)": tier_label,
            "General Tort SOL (yrs)": TORT_SOL.get(sol_lookup_state,"—"),
            "SOL End (est.)": sol_end_str,
            "Wagstaff file-by (SOL-45d)": wag_deadline_str,
            "Reported Dates (by channel)": report_dates_str,
            "Reported to Family/Friends (DateTime)": family_dt_str,
        }
        st.dataframe(pd.DataFrame([decision]), use_container_width=True, height=320)

        # ---- Diagnostics (to see why eligibility flips) ----
        with st.expander("Diagnostics (for you only)"):
            diag = {
                "female_rider": female_rider, "receipt": receipt, "gov_id": gov_id,
                "inside_near": inside_near, "has_atty": has_atty,
                "base_tier_ok": base_tier_ok, "tier_label": tier_label,
                "sol_years": sol_years, "wagstaff_deadline_ok_today<=deadline": wagstaff_time_ok,
                "earliest_report_date": fmt_date(earliest_report_date),
                "incident_date_used": fmt_date(incident_dt.date()),
                "report_delta_days": (None if delta_days is None else int(delta_days)),
                "triten_report_ok (<=14d)": triten_report_ok,
                "wag_ok_core(no company rule)": wag_ok_core,
                "wag_ok_final": wag_ok,
                "triten_ok_final": triten_ok
            }
            st.write(diag)

        # Export
        st.subheader("Export")
        export_payload = {
            "Narrative": narr, "Company": company, "State": state,
            "IncidentDate": fmt_date(incident_dt.date()), "IncidentTime": incident_time.strftime("%H:%M"),
            "Receipt": receipt, "ID": gov_id, "InsideNear": inside_near, "HasAtty": has_atty,
            "FemaleRider": female_rider, "Felony": felony, "DriverWeapon": weapon,
            "ClientCarryingWeapon": client_weapon, "VerbalOnly": verbal_only, "AttemptOnly": attempt_only,
            "Acts_Tier1_RapePenetration": rape, "Acts_Tier1_ForcedOralTouching": forced_oral,
            "Acts_Tier2_TouchingKissing": touching, "Acts_Tier2_Exposure": exposure,
            "Acts_Tier2_MasturbationObserved": masturb, "Aggravator_Kidnap": kidnap, "Aggravator_Imprison": imprison,
            "ReportedTo": [("NO" if "NO (DQ, UNLESS TIER 1 OR MINOR)" in reported_to else x) for x in reported_to],
            "ReportDates": {k: fmt_date(v) for k,v in report_dates.items()},
            "FamilyReportDateTime": fmt_dt(family_report_dt) if family_report_dt else "—",
            "RS_Submit_How": rs_submit_how, "RS_Received_Response": rs_received_response,
            "RS_Response_Detail": rs_response_detail,
            "Eligibility_Wagstaff": "Eligible" if wag_ok else "Not Eligible",
            "Eligibility_Triten": "Eligible" if triten_ok else "Not Eligible",
            **decision
        }
        export_df = pd.DataFrame([export_payload])
        st.download_button("Download CSV (intake + decision + diagnostics)",
                           data=export_df.to_csv(index=False).encode("utf-8"),
                           file_name="intake_decision.csv",
                           mime="text/csv")

    except Exception as e:
        st.error("Something went wrong while rendering the page.")
        st.exception(e)

# =========================
# RUN
# =========================
render_intake_and_decision()
