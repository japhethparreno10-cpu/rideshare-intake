import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# ---------- PAGE SETUP ----------
st.set_page_config(page_title="Rideshare Intake Qualifier", layout="wide")

# Bigger typography / spacing and clear badges
st.markdown("""
<style>
h1 {font-size: 2.0rem !important;}
h2 {font-size: 1.5rem !important; margin-top: 0.6rem;}
h3 {font-size: 1.25rem !important;}
.section {padding: 0.5rem 0 0.25rem 0;}
.badge-ok   {background:#16a34a; color:white; padding:12px 16px; border-radius:12px; font-size:22px; text-align:center;}
.badge-no   {background:#dc2626; color:white; padding:12px 16px; border-radius:12px; font-size:22px; text-align:center;}
.badge-note {background:#1f2937; color:#f9fafb; padding:8px 12px; border-radius:10px; font-size:14px; display:inline-block;}
[data-testid="stDataFrame"] div, [data-testid="stTable"] div {font-size: 1rem;}
</style>
""", unsafe_allow_html=True)

# ---------- CONSTANTS ----------
TODAY = datetime(2025, 9, 4)  # current context date

# General tort SOL by state (years)
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

# Wrongful death SOL by state (years)
WD_SOL = {
    "Alabama":2,"Alaska":2,"Arizona":2,"Arkansas":3,"California":2,"Colorado":2,"Connecticut":2,"Delaware":2,
    "Florida":2,"Georgia":2,"Hawaii":2,"Idaho":2,"Illinois":2,"Indiana":2,"Iowa":2,"Kansas":2,"Kentucky":1,
    "Louisiana":1,"Maine":6,"Maryland":3,"Massachusetts":3,"Michigan":3,"Minnesota":3,"Mississippi":3,"Missouri":3,
    "Montana":3,"Nebraska":2,"Nevada":2,"New Hampshire":3,"New Jersey":2,"New Mexico":3,"New York":2,
    "North Carolina":2,"North Dakota":6,"Ohio":2,"Oklahoma":2,"Oregon":3,"Pennsylvania":2,"Rhode Island":3,
    "South Carolina":3,"South Dakota":3,"Tennessee":1,"Texas":2,"Utah":2,"Vermont":2,"Virginia":2,"Washington":3,
    "West Virginia":2,"Wisconsin":3,"Wyoming":2
}

# Sexual assault SOL extensions quick reference
SA_EXT = {
    "California":{"rape_penetration":"No SOL","other_touching":"No SOL"},
    "New York":{"rape_penetration":"10 years","other_touching":"10 years"},
    "Texas":{"rape_penetration":"5 years","other_touching":"2 years"},
    "Illinois":{"rape_penetration":"No SOL","other_touching":"2 years"},
    "Connecticut":{"rape_penetration":"No SOL","other_touching":"2 years"},
}

# Non-lethal defensive items list (displayed when chosen)
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

# ---------- HELPERS ----------
def tier_and_aggravators(data):
    """
    Implements severity-first tiering exactly as specified:
    - Tier 1 has priority: rape/sodomy; forced oral; forced touching.
    - Tier 2 next: touching/kissing mouth/private parts; indecent exposure; masturbation.
    - Tier 3 is NOT a standalone tier. It is an aggravator that requires Tier 1 or Tier 2:
        - Kidnapping (off-route) w/ clear sexual or extreme physical threats
        - False imprisonment w/ clear sexual or extreme physical threats
    Returns (tier_label, aggravators_list).
    """
    t1 = bool(data["Rape/Penetration"] or data["Forced Oral/Forced Touching"])
    t2 = bool(data["Touching/Kissing w/o Consent"] or data["Indecent Exposure"] or data["Masturbation Observed"])
    aggr_kidnap = bool(data["Kidnapping Off-Route w/ Threats"])
    aggr_imprison = bool(data["False Imprisonment w/ Threats"])
    aggr = []
    if aggr_kidnap: aggr.append("Kidnapping w/ threats")
    if aggr_imprison: aggr.append("False imprisonment w/ threats")

    # Severity-first: pick Tier 1 if present, else Tier 2, else Unclear.
    if t1:
        base = "Tier 1"
    elif t2:
        base = "Tier 2"
    else:
        # If only kidnapping/imprisonment are checked without any Tier 1/2 act,
        # this does NOT constitute Tier 3 per the rule "must have Tier 1 or 2".
        base = "Unclear"

    # Label with aggravators if (and only if) base is Tier 1 or Tier 2 and aggravators were checked
    if base in ("Tier 1","Tier 2") and aggr:
        label = f"{base} (+ Aggravators: {', '.join(aggr)})"
    else:
        label = base

    # Also return a machine-friendly bool to say if aggravators are present while valid (T1/T2)
    valid_aggravators = (base in ("Tier 1","Tier 2")) and len(aggr) > 0
    return label, valid_aggravators

def add_years(date_obj, years):
    return date_obj + relativedelta(years=+int(years))

def fmt_date(dt):
    return dt.strftime("%Y-%m-%d") if dt else "—"

def badge(ok: bool, label: str):
    css = "badge-ok" if ok else "badge-no"
    st.markdown(f"<div class='{css}'>{label}</div>", unsafe_allow_html=True)

# ---------- UI ----------
st.title("Rideshare Intake Qualifier")

# Helpful references
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

with st.expander("Elements of Statement of the Case (for RIDESHARE)"):
    st.markdown("""
1. Date of ride  
2. Name of PC  
3. “reserved a ride with [name of Rideshare company]”  
4. General description of pick-up and drop-off (e.g., home → work)  
5. Purpose of ride (only if not self-evident)  
6. Brief/categorical description (assaulted, unwanted touching, groped, kidnapped, etc.)  
7. Person or entity PC reported incident to  
""")

with st.expander("Contacts"):
    st.markdown("""
**Triten Law** — 1015 15th Street NW, Washington, DC 20005 — **202-519-6715**  
**Wagstaff Legal Assistants:** Lorenia 213-347-9246 • Kim 213-770-1340 • Nate 623-254-7182  
*(Triten booking link: not yet available)*
""")

# ========== INTAKE (TOP, FULL-WIDTH) ==========
st.markdown("<div class='section'></div>", unsafe_allow_html=True)
st.header("Intake")

top1, top2, top3 = st.columns([1,1,1])
with top1:
    client = st.text_input("Client Name", placeholder="e.g., Jane Doe")
with top2:
    company = st.selectbox("Rideshare company", ["Uber", "Lyft"])
with top3:
    state = st.selectbox("Incident State", STATES, index=STATES.index("California") if "California" in STATES else 0)

row2 = st.columns(5)
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

dates1, dates2, dates3 = st.columns([1,1,2])
with dates1:
    incident_date = st.date_input("Incident Date", value=datetime(2025,8,1))
with dates2:
    reported_date = st.date_input("Reported Date", value=datetime(2025,8,5))
with dates3:
    reported_to = st.multiselect("Reported To (choose all that apply)",
                                 ["Rideshare company","Police","Therapist","Medical professional","Family/Friends","Audio/Video evidence"],
                                 default=["Police"])

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
    felony = st.toggle("Client has felony record", value=False)  # moved under Acts

st.subheader("Wrongful Death")
wd_col1, wd_col2 = st.columns([1,2])
with wd_col1:
    wd = st.toggle("Wrongful Death?", value=False)
with wd_col2:
    date_of_death = st.date_input("Date of Death", value=datetime(2025,8,10)) if wd else None

# ========== DECISION (BOTTOM, FULL-WIDTH, BIG) ==========
st.markdown("<div class='section'></div>", unsafe_allow_html=True)
st.header("Decision")

# Pack intake
data = {
    "Client Name": client,
    "Female Rider": female_rider,
    "Receipt": receipt,
    "ID": gov_id,
    "InsideNear": inside_near,
    "HasAtty": has_atty,
    "Company": company,
    "State": state,
    "IncidentDate": datetime.combine(incident_date, datetime.min.time()),
    "ReportedDate": datetime.combine(reported_date, datetime.min.time()),
    "ReportedTo": reported_to,
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
    "DateOfDeath": datetime.combine(date_of_death, datetime.min.time()) if wd and date_of_death else None
}

# Tier with severity-first + aggravators requirement
tier_label, has_valid_aggravators = tier_and_aggravators(data)

# Common requirements (both firms)
common_ok = all([
    data["Female Rider"],
    data["Receipt"],
    data["ID"],
    data["InsideNear"],
    not data["HasAtty"]
])

# SOL math
sol_years = TORT_SOL.get(state)
sol_end = add_years(data["IncidentDate"], sol_years) if sol_years else None
wagstaff_deadline = (sol_end - timedelta(days=45)) if sol_end else None
wagstaff_time_ok = (TODAY <= wagstaff_deadline) if wagstaff_deadline else True

# Triten reporting window
triten_report_ok = (data["ReportedDate"] - data["IncidentDate"]).days <= 14

# SA note
sa_note = ""
if state in SA_EXT and ("Tier 1" in tier_label or "Tier 2" in tier_label):
    if "Tier 1" in tier_label:
        sa_note = f"{state}: rape/penetration SOL = {SA_EXT[state]['rape_penetration']}" if state in SA_EXT else ""
    else:
        sa_note = f"{state}: other touching SOL = {SA_EXT[state]['other_touching']}" if state in SA_EXT else ""

# Wrongful death note
wd_note = ""
if data["WrongfulDeath"] and data["DateOfDeath"] and state in WD_SOL:
    wd_deadline = add_years(data["DateOfDeath"], WD_SOL[state])
    wd_note = f"Wrongful Death SOL: {WD_SOL[state]} years → deadline {fmt_date(wd_deadline)}"

# ---------- WAGSTAFF RULES (explicit reasons) ----------
wag_disq = []
if data["Felony"]:
    wag_disq.append("Felony record → Wagstaff requires no felony history")
if data["Weapon"] == "Yes":
    wag_disq.append("Weapon involved → disqualified under Wagstaff")
if data["VerbalOnly"]:
    wag_disq.append("Verbal abuse only → does not qualify")
if data["AttemptOnly"]:
    wag_disq.append("Attempt/minor contact only → does not qualify")
if data["HasAtty"]:
    wag_disq.append("Already has attorney → cannot intake")

# Family/Friends-only same-day rule
reported_to_set = set(data["ReportedTo"]) if data["ReportedTo"] else set()
same_day_family_ok = True
if reported_to_set and reported_to_set == {"Family/Friends"}:
    same_day_family_ok = (data["ReportedDate"].date() == data["IncidentDate"].date())
    if not same_day_family_ok:
        wag_disq.append("Reported only to Family/Friends, but not on same day → fails Wagstaff reporting rule")

# Wagstaff eligibility
base_tier_ok = ("Tier 1" in tier_label) or ("Tier 2" in tier_label)  # Unclear does not pass
wag_ok = (
    common_ok and wagstaff_time_ok and same_day_family_ok and base_tier_ok and len(wag_disq) == 0
)

# ---------- TRITEN RULES (explicit reasons) ----------
tri_disq = []
if data["VerbalOnly"]:
    tri_disq.append("Verbal abuse only → does not qualify")
if data["AttemptOnly"]:
    tri_disq.append("Attempt/minor contact only → does not qualify")
if data["HasAtty"]:
    tri_disq.append("Already has attorney → cannot intake")
if not triten_report_ok:
    tri_disq.append("Report not within 2 weeks → Triten requirement")

triten_ok = common_ok and triten_report_ok and base_tier_ok and len(tri_disq) == 0

# Company rule: Uber → Wagstaff only; Lyft → both
company_note = "Uber → Wagstaff only" if company=="Uber" else "Lyft → Wagstaff or Triten"
if company=="Uber":
    triten_ok = False
    if "Company rule: Uber → Wagstaff only." not in tri_disq:
        tri_disq.append("Company rule: Uber → Wagstaff only.")

# Badges row (big)
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

# Decision table (wide)
# Build explicit reasons text (bulleted-like string)
def reasons_text(ok, disq_list, common_ok, time_ok, same_day_ok, base_tier_ok, firm):
    if ok:
        return "Meets screen."
    reasons = []
    if not common_ok:
        reasons.append("Missing common requirements (must be female rider, have receipt & ID, incident inside/near car, and no current attorney).")
    if firm == "Wagstaff" and not time_ok:
        reasons.append("Past Wagstaff filing window (must file 45 days before SOL).")
    if firm == "Wagstaff" and not same_day_ok and reported_to_set == {"Family/Friends"}:
        reasons.append("Reported only to Family/Friends, but not on same day.")
    if not base_tier_ok:
        reasons.append("Tier unclear (select Tier 1 or Tier 2 qualifying acts).")
    if disq_list:
        reasons.extend(disq_list)
    return " ; ".join(reasons)

wag_reasons = reasons_text(wag_ok, wag_disq, common_ok, wagstaff_time_ok, same_day_family_ok, base_tier_ok, "Wagstaff")
tri_reasons = reasons_text(triten_ok, tri_disq, common_ok, True, True, base_tier_ok, "Triten")

decision = {
    "Rideshare Company Rule": company_note,
    "Tier (severity-first)": tier_label,
    "General Tort SOL (yrs)": sol_years,
    "SOL End (est.)": fmt_date(sol_end),
    "Wagstaff file-by (SOL-45d)": fmt_date(wagstaff_deadline),
    "Sexual Assault Extension Note": sa_note if sa_note else "—",
    "Wagstaff Reasons/Notes": wag_reasons if wag_reasons else "—",
    "Triten Reasons/Notes": tri_reasons if tri_reasons else "—",
    "Wrongful Death Note": wd_note if wd_note else "—"
}

# If non-lethal defensive item selected, add explanatory note with list
if data["Weapon"] == "Non-lethal defensive (e.g., pepper spray)":
    decision["Weapon Note"] = "Allowed (non-lethal defensive item). Examples: " + "; ".join(NON_LETHAL_ITEMS)

df = pd.DataFrame([decision])
st.dataframe(df, use_container_width=True, height=380)

# Export block
st.subheader("Export")
export_df = pd.concat([pd.DataFrame([data]), df], axis=1)
csv_bytes = export_df.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV (intake + decision)", data=csv_bytes, file_name="intake_decision.csv", mime="text/csv")

st.caption("Wagstaff: no felonies, no weapons (non-lethal defensive allowed), no verbal/attempt-only; file 45 days before SOL; Family/Friends-only reports must be same day. Triten: felonies OK, weapons OK, report within 2 weeks. Uber → Wagstaff only; Lyft → both. Tiering is severity-first; kidnapping/false imprisonment are aggravators that require Tier 1 or 2.")
