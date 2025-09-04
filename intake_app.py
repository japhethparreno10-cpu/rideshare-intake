import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# ---------- PAGE SETUP ----------
st.set_page_config(page_title="Rideshare Intake Qualifier", layout="wide")

# Bigger typography / spacing
st.markdown("""
<style>
h1 {font-size: 2.0rem !important;}
h2 {font-size: 1.5rem !important; margin-top: 0.6rem;}
h3 {font-size: 1.25rem !important;}
.section {padding: 0.5rem 0 0.25rem 0;}
.badge-ok   {background:#16a34a; color:white; padding:12px 16px; border-radius:12px; font-size:22px; text-align:center;}
.badge-no   {background:#dc2626; color:white; padding:12px 16px; border-radius:12px; font-size:22px; text-align:center;}
.badge-note {background:#1f2937; color:#f9fafb; padding:8px 12px; border-radius:10px; font-size:14px; display:inline-block;}
/* widen data table fonts */
[data-testid="stDataFrame"] div, [data-testid="stTable"] div {font-size: 1rem;}
</style>
""", unsafe_allow_html=True)

# ---------- CONSTANTS ----------
TODAY = datetime(2025, 9, 4)

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

STATES = sorted(set(list(TORT_SOL.keys()) + list(WD_SOL.keys()) + ["D.C."]))

# ---------- HELPERS ----------
def derive_tier(data) -> str:
    t1 = data["Rape/Penetration"] or data["Forced Oral/Forced Touching"]
    t2 = data["Touching/Kissing w/o Consent"] or data["Indecent Exposure"] or data["Masturbation Observed"]
    t3 = data["Kidnapping Off-Route w/ Threats"] or data["False Imprisonment w/ Threats"]
    if t1: return "Tier 1"
    if t2: return "Tier 2"
    if t3: return "Tier 3"
    return "Unclear"

def add_years(date_obj, years):
    return date_obj + relativedelta(years=+int(years))

def fmt_date(dt):
    return dt.strftime("%Y-%m-%d") if dt else "—"

def badge(ok: bool, label: str):
    css = "badge-ok" if ok else "badge-no"
    st.markdown(f"<div class='{css}'>{label}</div>", unsafe_allow_html=True)

# ---------- UI ----------
st.title("Rideshare Intake Qualifier")

# ========== INTAKE (TOP, FULL-WIDTH) ==========
st.markdown("<div class='section'></div>", unsafe_allow_html=True)
st.header("Intake")

# core requirements
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

# dis/qualifiers (kept near core toggles)
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
    # MOVED HERE: under Acts section
    felony = st.toggle("Client has felony record", value=False)

st.subheader("Wrongful Death")
wd_col1, wd_col2 = st.columns([1,2])
with wd_col1:
    wd = st.toggle("Wrongful Death?", value=False)
with wd_col2:
    date_of_death = st.date_input("Date of Death", value=datetime(2025,8,10)) if wd else None

# ========== DECISION (BOTTOM, FULL-WIDTH, BIG) ==========
st.markdown("<div class='section'></div>", unsafe_allow_html=True)
st.header("Decision")

# pack intake
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

tier = derive_tier(data)

# common reqs
common_ok = all([
    data["Female Rider"],
    data["Receipt"],
    data["ID"],
    data["InsideNear"],
    not data["HasAtty"]
])

# SOL calculations
sol_years = TORT_SOL.get(state)
sol_end = add_years(data["IncidentDate"], sol_years) if sol_years else None
wagstaff_deadline = (sol_end - timedelta(days=45)) if sol_end else None
wagstaff_time_ok = (TODAY <= wagstaff_deadline) if wagstaff_deadline else True

# Triten: report within 2 weeks
triten_report_ok = (data["ReportedDate"] - data["IncidentDate"]).days <= 14

# SA note
sa_note = ""
if state in SA_EXT and tier in ("Tier 1","Tier 2"):
    sa_note = (f"{state}: rape/penetration SOL = {SA_EXT[state]['rape_penetration']}"
               if tier=="Tier 1" else
               f"{state}: other touching SOL = {SA_EXT[state]['other_touching']}")

# WD note
wd_note = ""
if data["WrongfulDeath"] and data["DateOfDeath"] and state in WD_SOL:
    wd_deadline = add_years(data["DateOfDeath"], WD_SOL[state])
    wd_note = f"Wrongful Death SOL: {WD_SOL[state]} years → deadline {fmt_date(wd_deadline)}"

# firm screens
wag_disq = []
if data["Felony"]: wag_disq.append("Felony record")
if data["Weapon"] == "Yes": wag_disq.append("Weapon involved")
if data["VerbalOnly"]: wag_disq.append("Verbal only")
if data["AttemptOnly"]: wag_disq.append("Attempt/minor contact")
if data["HasAtty"]: wag_disq.append("Already has attorney")
wag_ok = common_ok and wagstaff_time_ok and (tier in ("Tier 1","Tier 2","Tier 3")) and len(wag_disq) == 0

tri_disq = []
if data["VerbalOnly"]: tri_disq.append("Verbal only")
if data["AttemptOnly"]: tri_disq.append("Attempt/minor contact")
if data["HasAtty"]: tri_disq.append("Already has attorney")
triten_ok = common_ok and triten_report_ok and (tier in ("Tier 1","Tier 2","Tier 3")) and len(tri_disq) == 0

# Company rule: Uber → Wagstaff only; Lyft → both
company_note = "Uber → Wagstaff only" if company=="Uber" else "Lyft → Wagstaff or Triten"
if company=="Uber":
    triten_ok = False

# badges row (big, no scrolling)
b1, b2, b3 = st.columns([1,1,1])
with b1:
    st.markdown(f"<div class='badge-note'>Tier</div>", unsafe_allow_html=True)
    badge(True, tier if tier!="Unclear" else "Tier unclear")
with b2:
    st.markdown(f"<div class='badge-note'>Wagstaff</div>", unsafe_allow_html=True)
    badge(wag_ok, "Eligible" if wag_ok else "Not Eligible")
with b3:
    st.markdown(f"<div class='badge-note'>Triten</div>", unsafe_allow_html=True)
    badge(triten_ok, "Eligible" if triten_ok else "Not Eligible")

# wide summary table
decision = {
    "Rideshare Company Rule": company_note,
    "General Tort SOL (yrs)": sol_years,
    "SOL End (est.)": fmt_date(sol_end),
    "Wagstaff file-by (SOL-45d)": fmt_date(wagstaff_deadline),
    "Sexual Assault Extension Note": sa_note if sa_note else "—",
    "Wagstaff Reasons/Notes": (
        "Meets screen."
        if wag_ok else
        "; ".join(filter(None, [
            "Missing common reqs (female rider, receipt, ID, inside/near car, no attorney)." if not common_ok else "",
            "Past Wagstaff filing window (needs 45 days before SOL)." if not wagstaff_time_ok else "",
            ("Disqualifications: " + ", ".join(wag_disq)) if wag_disq else "",
            "Tier unclear; add details." if tier == "Unclear" else ""
        ]))
    ),
    "Triten Reasons/Notes": (
        "Meets screen."
        if triten_ok else
        "; ".join(filter(None, [
            "Missing common reqs (female rider, receipt, ID, inside/near car, no attorney)." if not common_ok else "",
            "Report not within 2 weeks." if not triten_report_ok else "",
            ("Disqualifications: " + ", ".join(tri_disq)) if tri_disq else "",
            "Tier unclear; add details." if tier == "Unclear" else "",
            "Company rule: Uber → Wagstaff only." if company == "Uber" else ""
        ]))
    ),
    "Wrongful Death Note": wd_note if wd_note else "—"
}
df = pd.DataFrame([decision])
st.dataframe(df, use_container_width=True, height=300)

# export
st.subheader("Export")
export_df = pd.concat([pd.DataFrame([data]), df], axis=1)
csv_bytes = export_df.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV (intake + decision)", data=csv_bytes, file_name="intake_decision.csv", mime="text/csv")

st.caption("Rules: Wagstaff (strict: no felonies, no weapons, no attempts/verbal; file 45 days before SOL) vs Triten (felonies OK, weapons OK if reported; report within 2 weeks). Company rule: Uber → Wagstaff only; Lyft → both. Layout is vertical for clearer presentation.")
