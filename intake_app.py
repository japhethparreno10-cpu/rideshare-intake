import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta

# ---------- PAGE SETUP ----------
st.set_page_config(page_title="Rideshare Intake Qualifier", layout="wide")

st.markdown("""
<style>
h1 {font-size: 2.0rem !important;}
h2 {font-size: 1.5rem !important; margin-top: 0.6rem;}
.section {padding: 0.5rem 0 0.25rem 0;}
.badge-ok   {background:#16a34a; color:white; padding:12px 16px; border-radius:12px; font-size:22px; text-align:center;}
.badge-no   {background:#dc2626; color:white; padding:12px 16px; border-radius:12px; font-size:22px; text-align:center;}
.badge-note {background:#1f2937; color:#f9fafb; padding:8px 12px; border-radius:10px; font-size:14px; display:inline-block;}
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

NON_LETHAL_ITEMS = [
    "Pepper Spray","Personal Alarm","Stun Gun","Taser","Self-Defense Keychain","Tactical Flashlight",
    "Groin Kickers","Personal Safety Apps","Defense Flares","Baton","Kubotan","Umbrella","Whistle",
    "Combat Pen","Pocket Knife","Personal Baton","Nunchaku","Flashbang","Air Horn","Bear Spray",
    "Sticky Foam","Tactical Scarf/Shawl","Self-Defense Ring","Hearing Protection"
]

STATES = sorted(set(list(TORT_SOL.keys()) + list(WD_SOL.keys()) + ["D.C."]))

# ---------- HELPERS ----------
def tier_and_aggravators(data):
    t1 = bool(data["Rape/Penetration"] or data["Forced Oral/Forced Touching"])
    t2 = bool(data["Touching/Kissing w/o Consent"] or data["Indecent Exposure"] or data["Masturbation Observed"])
    aggr_kidnap = bool(data["Kidnapping Off-Route w/ Threats"])
    aggr_imprison = bool(data["False Imprisonment w/ Threats"])
    aggr = []
    if aggr_kidnap: aggr.append("Kidnapping")
    if aggr_imprison: aggr.append("False imprisonment")

    if t1:
        base = "Tier 1"
    elif t2:
        base = "Tier 2"
    else:
        base = "Unclear"

    if base in ("Tier 1","Tier 2") and aggr:
        label = f"{base} (+ {', '.join(aggr)})"
    else:
        label = base

    return label, (base in ("Tier 1","Tier 2") and len(aggr) > 0)

def fmt_date(dt): return dt.strftime("%Y-%m-%d") if dt else "—"
def fmt_dt(dt): return dt.strftime("%Y-%m-%d %H:%M") if dt else "—"
def badge(ok, label): st.markdown(f"<div class='{'badge-ok' if ok else 'badge-no'}'>{label}</div>", unsafe_allow_html=True)

# ---------- UI ----------
st.title("Rideshare Intake Qualifier")

with st.expander("Injury & Sexual Assault: Tiers and State SOL Extensions (Reference)"):
    st.markdown("""
**Tier 1**  
- Rape or sodomy  
- Forcing someone to touch themselves  
- Forcing someone to perform oral sex  

**Tier 2**  
- Touching/kissing mouth/private parts without consent  
- Indecent exposure  
- Masturbation in front of someone without consent  

**Tier 3 (Aggravators, must have Tier 1 or 2)**  
- Kidnapping off-route with threats  
- False imprisonment with threats  

**State Sexual Assault SOL Extensions**  
- CA: No SOL for penetration/touching  
- NY: 10 years for penetration/touching  
- TX: 5 years penetration / 2 years other  
- IL: No SOL penetration / 2 years other  
- CT: No SOL penetration / 2 years other  
""")

# === Intake ===
st.header("Intake")
col1,col2,col3 = st.columns(3)
with col1: client = st.text_input("Client Name")
with col2: company = st.selectbox("Rideshare company", ["Uber","Lyft"])
with col3: state = st.selectbox("Incident State", STATES, index=STATES.index("California"))

row2 = st.columns(6)
with row2[0]: female_rider = st.toggle("Female rider", True)
with row2[1]: receipt = st.toggle("Receipt provided", True)
with row2[2]: gov_id = st.toggle("ID provided", True)
with row2[3]: inside_near = st.toggle("Incident inside/near car", True)
with row2[4]: has_atty = st.toggle("Already has attorney", False)
with row2[5]: incident_time = st.time_input("Incident Time", time(21,0))
incident_date = st.date_input("Incident Date", datetime(2025,8,1))

reported_to = st.multiselect("Reported To", [
    "Rideshare company","Police","Therapist","Medical professional","Physician","Family/Friends","Audio/Video evidence"
], default=["Police"])

report_dates = {}
if "Rideshare company" in reported_to:
    report_dates["Rideshare company"] = st.date_input("Date reported to Rideshare company", incident_date)
if "Police" in reported_to:
    report_dates["Police"] = st.date_input("Date reported to Police", incident_date)
if "Therapist" in reported_to:
    report_dates["Therapist"] = st.date_input("Date reported to Therapist", incident_date)
if "Medical professional" in reported_to:
    report_dates["Medical professional"] = st.date_input("Date reported to Medical professional", incident_date)
if "Physician" in reported_to:
    report_dates["Physician"] = st.date_input("Date reported to Physician", incident_date)
if "Audio/Video evidence" in reported_to:
    report_dates["Audio/Video evidence"] = st.date_input("Date of Audio/Video evidence", incident_date)

family_report_dt=None
if "Family/Friends" in reported_to:
    fr_c1,fr_c2 = st.columns(2)
    d=fr_c1.date_input("Date reported to Family/Friends", incident_date)
    t=fr_c2.time_input("Time reported to Family/Friends", incident_time)
    family_report_dt=datetime.combine(d,t)

# Disqualifiers
dq1,dq2,dq3 = st.columns(3)
with dq1: weapon=st.selectbox("Weapon involved?",["No","Non-lethal defensive (e.g., pepper spray)","Yes"])
with dq2: verbal_only=st.toggle("Verbal abuse only",False)
with dq3: attempt_only=st.toggle("Attempt/minor contact only",False)

# Acts
st.subheader("Acts")
c1,c2=st.columns(2)
with c1:
    rape=st.checkbox("Rape/Penetration")
    forced_oral=st.checkbox("Forced Oral/Touching")
    touching=st.checkbox("Touching/Kissing without consent")
with c2:
    exposure=st.checkbox("Indecent Exposure")
    masturb=st.checkbox("Masturbation Observed")
    kidnap=st.checkbox("Kidnapping Off-Route w/ Threats")
    imprison=st.checkbox("False Imprisonment w/ Threats")
    felony=st.toggle("Client has felony record",False)

# Wrongful Death
st.subheader("Wrongful Death")
wd_col1,wd_col2=st.columns([1,2])
with wd_col1: wd=st.toggle("Wrongful Death?",False)
with wd_col2: date_of_death=st.date_input("Date of Death", datetime(2025,8,10)) if wd else None

# === Decision ===
st.header("Decision")
incident_dt=datetime.combine(incident_date,incident_time)
data={"Company":company,"State":state,"IncidentDateTime":incident_dt,
      "ReportedTo":reported_to,"ReportDates":report_dates,"FamilyReportDateTime":family_report_dt,
      "Felony":felony,"Weapon":weapon,"VerbalOnly":verbal_only,"AttemptOnly":attempt_only,
      "Rape/Penetration":rape,"Forced Oral/Forced Touching":forced_oral,
      "Touching/Kissing w/o Consent":touching,"Indecent Exposure":exposure,"Masturbation Observed":masturb,
      "Kidnapping Off-Route w/ Threats":kidnap,"False Imprisonment w/ Threats":imprison,
      "WrongfulDeath":wd,"DateOfDeath":datetime.combine(date_of_death,time(12)) if wd and date_of_death else None}

tier_label,_=tier_and_aggravators(data)
common_ok=all([female_rider,receipt,gov_id,inside_near,not has_atty])

sol_years=TORT_SOL.get(state)
sol_end=incident_dt+relativedelta(years=+int(sol_years)) if sol_years else None
wagstaff_deadline=(sol_end-timedelta(days=45)) if sol_end else None
wagstaff_time_ok=(TODAY<=wagstaff_deadline) if wagstaff_deadline else True

# Triten earliest report date
earliest=None
all_dates=[d for d in report_dates.values() if d]
if family_report_dt: all_dates.append(family_report_dt.date())
if all_dates: earliest=min(all_dates)
triten_report_ok=(earliest-incident_dt.date()).days<=14 if earliest else False

# Wagstaff disqualifiers
wag_disq=[]
if felony: wag_disq.append("Felony record")
if weapon=="Yes": wag_disq.append("Weapon involved")
if verbal_only: wag_disq.append("Verbal abuse only")
if attempt_only: wag_disq.append("Attempt/minor contact only")
if has_atty: wag_disq.append("Already has attorney")
within24=True
if set(reported_to)=={"Family/Friends"}:
    if not family_report_dt: within24=False; wag_disq.append("Family/Friends-only, no date/time")
    else:
        delta=family_report_dt-incident_dt
        within24=(timedelta(0)<=delta<=timedelta(hours=24))
        if not within24: wag_disq.append("Family/Friends-only report exceeded 24h")
base_tier_ok=("Tier 1" in tier_label or "Tier 2" in tier_label)
wag_ok=common_ok and wagstaff_time_ok and within24 and base_tier_ok and not wag_disq

# Triten disqualifiers
tri_disq=[]
if verbal_only: tri_disq.append("Verbal abuse only")
if attempt_only: tri_disq.append("Attempt/minor contact only")
if has_atty: tri_disq.append("Already has attorney")
if not earliest: tri_disq.append("No report date")
if not triten_report_ok: tri_disq.append("Not within 2 weeks")
triten_ok=common_ok and triten_report_ok and base_tier_ok and not tri_disq

# === Company Rule update ===
if company=="Uber":
    company_note="Uber → Wagstaff and Triten"
elif company=="Lyft":
    company_note="Lyft → Triten only"
    wag_ok=False
    if "Company rule: Lyft → Triten only." not in wag_disq:
        wag_disq.append("Company rule: Lyft → Triten only.")

# Badges
colA,colB,colC=st.columns(3)
with colA: badge(True,tier_label)
with colB: badge(wag_ok,"Wagstaff Eligible" if wag_ok else "Wagstaff Not Eligible")
with colC: badge(triten_ok,"Triten Eligible" if triten_ok else "Triten Not Eligible")

# Reasons
wag_reasons="; ".join(wag_disq) if wag_disq else ("Meets screen." if wag_ok else "—")
tri_reasons="; ".join(tri_disq) if tri_disq else ("Meets screen." if triten_ok else "—")

decision={"Rideshare Company Rule":company_note,"Tier":tier_label,
          "General Tort SOL (yrs)":sol_years,"SOL End":fmt_dt(sol_end) if sol_end else "—",
          "Wagstaff Deadline (SOL-45d)":fmt_dt(wagstaff_deadline) if wagstaff_deadline else "—",
          "Wagstaff Notes":wag_reasons,"Triten Notes":tri_reasons}

df=pd.DataFrame([decision])
st.dataframe(df,use_container_width=True)

if weapon=="Non-lethal defensive (e.g., pepper spray)":
    st.info("Non-lethal defensive item allowed. Examples: "+", ".join(NON_LETHAL_ITEMS))
