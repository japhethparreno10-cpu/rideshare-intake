def render_intake_and_decision():
    st.header("Intake")

    # ---- 2-column grid matching your screenshot order ----
    L, R = st.columns(2)

    # ========== LEFT COLUMN ==========
    with L:
        # 1. Free narrative
        st.markdown("**1. I know it’s not always easy to talk about the incident and we appreciate you trusting us with these details.**  \n**Can you please describe what happened in your own words. (Allow claimant to speak freely.)**")
        narr = st.text_area(" ", key="q1_narr")
        script_block('Agent Response: Thank you for sharing that with me. You said "[mirror key words]" — and that sounds incredibly difficult. I want you to know this space is confidential, and you\'re doing the right thing by speaking up.')

        # 3. Receipt (toggle OFF by default + scripted how-to)
        st.markdown("**3. Are you able to reproduce the ride share receipt to show proof of the ride? (If not, DQ)**")
        receipt = st.toggle("Receipt provided (email/app/PDF)", value=False, key="q3_receipt_toggle")
        if not receipt:
            st.markdown("**If Yes:** Okay, that’s great you can get the receipt for the ride. That is one of the most important pieces of proof we need that will link your rideshare trip to the incident.")
            st.markdown("**If No:** Okay, so you cannot check it in your email or on the app? That is one of the most important pieces of proof we need that will link your rideshare trip to the incident. *[Refer the claimant to instructions on obtaining the receipt through email or the app.]*")
            st.markdown("<div class='callout'><b>Text to send:</b><br><span class='copy'>Forward your receipt to <b>jay@advocaterightscenter.com</b> by selecting the ride in Ride History and choosing “Resend Receipt.”<br>(Msg Rates Apply. Txt STOP to cancel/HELP for help)</span></div>", unsafe_allow_html=True)
            st.markdown("<div class='copy'>Forward your receipt to <b>jay@advocaterightscenter.com</b><br>(Msg Rates Apply. Txt STOP to cancel/HELP for help)</div>", unsafe_allow_html=True)

        # 5. Reported to (multi)
        st.markdown("**5. Did you report the incident to anyone, like the Rideshare Company, Police, Therapist, Physician, or Friend or Family Member?**")
        reported_to = st.multiselect(
            "Select all that apply",
            ["Rideshare Company","Physician","Friend or Family Member","Therapist","Police Department","NO (DQ, UNLESS TIER 1 OR MINOR)"],
            key="q5_reported"
        )
        if reported_to:
            script_block("If Reported: Okay, that’s good that you reported it to [repeat answer] — thank you. That helps show you took steps to get help, and that can support your case. It takes a lot of strength.")
        else:
            script_block("If Not Reported: Okay, so you didn’t tell anyone that might be able to corroborate your story. That can make it difficult to pursue. Let me speak with my supervisor, but based upon the guidelines, the law firm may not be accepting cases where the victim did not report it to anyone.")

        # capture dates for any selected channels (used by Triten 14-day logic)
        report_dates = {}
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
            report_dates["Family/Friends"] = ff_date  # store date; we’ll also keep datetime separately
            family_report_dt = datetime.combine(ff_date, ff_time)
        else:
            family_report_dt = None

        # 7. Inside/just-outside scope (toggle OFF + your exact script)
        st.markdown("**7. Did the incident occur while utilizing the Rideshare service, either inside or just outside the vehicle?**")
        inside_near = st.toggle("Mark ON once confirmed 'inside/just outside/started near car'", value=False, key="q7_inside")
        if not inside_near:
            script_block("Did the incident occur while utilizing the Rideshare service, either inside or just outside the vehicle?")
        else:
            script_block("If Yes: Okay. So, it happened [repeat where happened]. Thank you. Knowing where it happened while using the Rideshare helps confirm that it’s within the scope of the Rideshare’s responsibility, which includes providing a safe means of transportation.")

        # 9. Response from Uber/Lyft (toggle + optional details)
        st.markdown("**9. Did you receive a response from Uber or Lyft?**")
        rs_received_response = st.toggle("Mark ON if a response was received", value=False, key="q9_resp_toggle")
        rs_response_detail = st.text_input("If yes, what did they say? (optional)", key="q9_resp_detail")
        script_block("Agent Response: Got it — so they [did/did not] respond. That can be really frustrating, especially when you're expecting someone to acknowledge what happened.")

    # ========== RIGHT COLUMN ==========
    with R:
        # 2. Which rideshare company
        st.markdown("**2. Which Rideshare company did you use?**")
        company = st.selectbox(" ", ["Uber","Lyft","Other"], key="q2_company")
        script_block("Agent Response: [Rideshare company name], got it. That helps the law firm determine who may be held responsible and verify who operated the ride at the time. You’re doing great.")

        # 4. Date of incident (if they know)
        st.markdown("**4. Do you have the Date the incident occurred?**")
        has_incident_date = st.toggle("Mark ON once claimant confirms they know the date", value=False, key="q4_hasdate")
        incident_date = None
        if has_incident_date:
            incident_date = st.date_input("Select Incident Date", value=TODAY.date(), key="q4_date")
            script_block("Agent Response: Got it. The date was [repeat date]. The timing really helps us document everything properly and connect the incident with the Rideshare trip. So thank you for that.")
        else:
            script_block("If date is unknown now, continue intake and note context clues (ride history, calendar, texts) to help locate it later.")

        # 6. State of incident
        st.markdown("**6. What state this this happen?**")
        STATES_sorted = sorted(set(list(TORT_SOL.keys()) + list(WD_SOL.keys()) + ["D.C."]))
        state = st.selectbox("Incident State", STATES_sorted, index=(STATES_sorted.index("California") if "California" in STATES_sorted else 0), key="q6_state")
        script_block("Agent Response: Okay. [Repeat state]. Thank you.")

        # 8. If submitted to Rideshare: how did you submit?
        st.markdown("**8. If submitted to Rideshare:  How did you submit the report to Uber or Lyft?**")
        rs_submit_how = st.text_input("email / app / other", key="q8_submit_how")
        if rs_submit_how.strip():
            script_block("Agent Response: Okay, so you submitted it through [email/app]. That’s helpful — thank you for sharing that. Some survivors have used the app, and others reached out by email, so either is totally fine.")

        # 10. Felonies / criminal history (toggle OFF + explanation)
        st.markdown("**10. So the law firm can be prepared for any character issues, do you have any felonies or criminal history?**")
        felony = st.toggle("Mark ON only if they confirm a felony/criminal history", value=False, key="q10_felony")
        script_block("If Yes: We ask this to ensure there are no legal issues that could impact or weaken your case. It helps us prepare in case the other side tries to use your past against you. This is a standard part of handling your case and doesn’t reflect on your character.")

    # ===== Additional switches the app needs for eligibility (kept OFF by default) =====
    st.markdown("---")
    st.caption("Eligibility switches (leave OFF until verified)")
    colE1, colE2, colE3 = st.columns(3)
    with colE1:
        female_rider = st.toggle("Female rider", value=False, key="elig_female")
        if not female_rider:
            script_block("Confirm rider identity if applicable. This aligns with firm screening rules.")
    with colE2:
        gov_id = st.toggle("ID provided", value=False, key="elig_id")
        if not gov_id:
            script_block("""We’ll need a government ID to ensure any settlement is paid to the right person. 
We do **not** ask for bank details now.  
• Prevents impersonation  
• Allows HIPAA records requests  
• Ensures funds go to the correct person""")
    with colE3:
        has_atty = st.toggle("Already has an attorney", value=False, key="elig_atty")
        if has_atty:
            script_block("Because another attorney already represents you on this claim, we can’t proceed with intake.")

    # Optional driver/client weapon + attempt/verbal granularity (all OFF)
    colX1, colX2, colX3, colX4 = st.columns(4)
    with colX1:
        weapon = st.selectbox("Driver used/threatened weapon?", ["No","Non-lethal defensive (e.g., pepper spray)","Yes"], key="elig_driver_weapon")
    with colX2:
        client_weapon = st.toggle("Client carrying a weapon?", value=False, key="elig_client_weapon")
    with colX3:
        verbal_only = st.toggle("Verbal abuse only (no sexual acts)", value=False, key="elig_verbal_only")
    with colX4:
        attempt_only = st.toggle("Attempt/minor contact only", value=False, key="elig_attempt_only")

    # Acts (Tier logic)
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

    # ========= Decision & Summary (unchanged logic) =========
    incident_time = st.time_input("Incident Time", value=time(21, 0), key="time_for_calc")
    incident_dt = datetime.combine((incident_date or TODAY.date()), incident_time)

    # Build state payload for tier/eligibility
    state_data = {
        "Narrative": narr,
        "Company": company,
        "State": state,
        "IncidentDateTime": incident_dt,
        "Receipt": receipt,
        "ID": gov_id,
        "InsideNear": inside_near,
        "HasAtty": has_atty,
        "Female Rider": female_rider,
        "Felony": felony,
        "Weapon": weapon,
        "ClientCarryingWeapon": client_weapon,
        "VerbalOnly": verbal_only,
        "AttemptOnly": attempt_only,
        "Rape/Penetration": rape,
        "Forced Oral/Forced Touching": forced_oral,
        "Touching/Kissing w/o Consent": touching,
        "Indecent Exposure": exposure,
        "Masturbation Observed": masturb,
        "Kidnapping Off-Route w/ Threats": kidnap,
        "False Imprisonment w/ Threats": imprison,
        "ReportedTo": [("NO" if "NO (DQ, UNLESS TIER 1 OR MINOR)" in reported_to else x) for x in reported_to],
        "ReportDates": report_dates,
        "FamilyReportDateTime": family_report_dt if "Friend or Family Member" in reported_to else None,
        "RS_Submit_How": rs_submit_how,
        "RS_Received_Response": rs_received_response,
        "RS_Response_Detail": rs_response_detail
    }

    # Tier + aggravators
    tier_label, _ = tier_and_aggravators(state_data)
    base_tier_ok = ("Tier 1" in tier_label) or ("Tier 2" in tier_label)

    # SOL + Wagstaff timing
    sol_lookup_state = {"Washington DC": "D.C.", "District of Columbia": "D.C."}.get(state, state)
    sol_years = TORT_SOL.get(sol_lookup_state)
    if sol_years:
        sol_end = incident_dt + relativedelta(years=+int(sol_years))
        wagstaff_deadline = sol_end - timedelta(days=45)
        wagstaff_time_ok = TODAY <= wagstaff_deadline
    else:
        sol_end = wagstaff_deadline = None
        wagstaff_time_ok = True

    # Triten earliest report <=14d
    all_dates = [d for d in report_dates.values() if d]
    if state_data["FamilyReportDateTime"]: all_dates.append(state_data["FamilyReportDateTime"].date())
    earliest_report_date = min(all_dates) if all_dates else None
    delta_days = (earliest_report_date - incident_dt.date()).days if earliest_report_date else None
    triten_report_ok = (delta_days is not None) and (0 <= delta_days <= 14)

    # Validation
    if earliest_report_date and earliest_report_date < incident_dt.date():
        st.warning("Earliest report date is before the incident date. Please double-check.")

    # Wagstaff disqualifiers
    wag_disq, reported_to_set = [], set(reported_to)
    if felony: wag_disq.append("Felony record → Wagstaff requires no felony history")
    if weapon == "Yes": wag_disq.append("Weapon involved → disqualified under Wagstaff")
    if client_weapon: wag_disq.append("Victim carrying a weapon → may disqualify under some firm rules")
    if verbal_only: wag_disq.append("Verbal abuse only → does not qualify")
    if attempt_only: wag_disq.append("Attempt/minor contact only → does not qualify")
    if has_atty: wag_disq.append("Already has attorney → cannot intake")

    within_24h_family_ok, missing_family_dt = True, False
    if reported_to_set == {"Friend or Family Member"}:
        if not state_data["FamilyReportDateTime"]:
            within_24h_family_ok = False; missing_family_dt = True
            wag_disq.append("Family/Friends-only selected but date/time was not provided")
        else:
            delta = state_data["FamilyReportDateTime"] - incident_dt
            within_24h_family_ok = (timedelta(0) <= delta <= timedelta(hours=24))
            if not within_24h_family_ok:
                wag_disq.append("Family/Friends-only report exceeded 24 hours after incident → fails Wagstaff rule")

    common_ok = all([female_rider, receipt, gov_id, inside_near, not has_atty])
    wag_ok = common_ok and wagstaff_time_ok and within_24h_family_ok and base_tier_ok and not wag_disq

    tri_disq = []
    if verbal_only: tri_disq.append("Verbal abuse only → does not qualify")
    if attempt_only: tri_disq.append("Attempt/minor contact only → does not qualify")
    if earliest_report_date is None: tri_disq.append("No report date provided for any channel")
    if not triten_report_ok: tri_disq.append("Report not within 2 weeks (based on earliest report date)")
    if has_atty: tri_disq.append("Already has attorney → cannot intake")
    triten_ok = common_ok and triten_report_ok and base_tier_ok and not tri_disq

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

    # Summary
    st.subheader("Summary")
    def fmt_date(dt): return dt.strftime("%Y-%m-%d") if dt else "—"
    def fmt_dt(dt): return dt.strftime("%Y-%m-%d %H:%M") if dt else "—"
    report_dates_str = "; ".join([f"{k}: {fmt_date(v)}" for k, v in report_dates.items()]) if report_dates else "—"
    family_dt_str = fmt_dt(state_data["FamilyReportDateTime"]) if state_data["FamilyReportDateTime"] else "—"
    decision = {
        "Tier (severity-first)": tier_label,
        "General Tort SOL (yrs)": TORT_SOL.get(sol_lookup_state,"—"),
        "SOL End (est.)": fmt_dt(sol_end) if sol_end else "—",
        "Wagstaff file-by (SOL-45d)": fmt_dt(wagstaff_deadline) if wagstaff_deadline else "—",
        "Reported Dates (by channel)": report_dates_str,
        "Reported to Family/Friends (DateTime)": family_dt_str,
    }
    st.dataframe(pd.DataFrame([decision]), use_container_width=True, height=320)

    # Export
    st.subheader("Export")
    export_df = pd.DataFrame([state_data]).assign(**decision)
    st.download_button("Download CSV (intake + decision + narrative)",
                       data=export_df.to_csv(index=False).encode("utf-8"),
                       file_name="intake_decision_coached.csv",
                       mime="text/csv")
