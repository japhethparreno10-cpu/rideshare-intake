import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time, date
from dateutil.relativedelta import relativedelta
from io import BytesIO

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
.note-muted {border:1px dashed #d1d5db; border-radius:8px; padding:10px 12px; margin:8px 0; background:#f9fafb; color:#374151;}
.script {border-left:4px solid #9ca3af; background:#f3f4f6; color:#111827; padding:12px 14px; border-radius:8px; margin:8px 0 12px 0; font-size:0.97rem;}
.callout {border-left:6px solid #2563eb; background:#eef2ff; color:#1e3a8a; padding:12px 14px; border-radius:12px; margin:8px 0 12px 0;}
.small {font-size: 0.9rem; color:#4b5563;}
hr {border:0; border-top:1px solid #e5e7eb; margin:12px 0;}
[data-testid="stDataFrame"] div, [data-testid="stTable"] div {font-size: 1rem;}
.copy {font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; white-space:pre-wrap;}
.kv {font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;}
</style>
""", unsafe_allow_html=True)

TODAY = datetime.now()

# =========================
# EXCEL ENGINE DETECTION
# =========================
try:
    import xlsxwriter  # noqa: F401
    XLSX_ENGINE = "xlsxwriter"
except Exception:
    try:
        import openpyxl  # noqa: F401
        XLSX_ENGINE = "openpyxl"
    except Exception:
        XLSX_ENGINE = None

# =========================
# SOL TABLES
# =========================
TORT_SOL = {
    # 1 year
    "Kentucky": 1, "Louisiana": 1, "Tennessee": 1,
    # 2 years
    "Alabama": 2, "Alaska": 2, "Arizona": 2, "California": 2, "Colorado": 2, "Connecticut": 2, "Delaware": 2,
    "Georgia": 2, "Hawaii": 2, "Idaho": 2, "Illinois": 2, "Indiana": 2, "Iowa": 2, "Kansas": 2, "Minnesota": 2,
    "Nevada": 2, "New Jersey": 2, "Ohio": 2, "Oklahoma": 2, "Oregon": 2, "Pennsylvania": 2, "Texas": 2,
    "Virginia": 2, "West Virginia": 2,
    # 3 years
    "Arkansas": 3, "D.C.": 3, "Maryland": 3, "Massachusetts": 3, "Michigan": 3, "Mississippi": 3, "Montana": 3,
    "New Hampshire": 3, "New Mexico": 3, "New York": 3, "North Carolina": 3, "Rhode Island": 3, "South Carolina": 3,
    "South Dakota": 3, "Vermont": 3, "Washington": 3, "Wisconsin": 3,
    # 4 years
    "Florida": 4, "Nebraska": 4, "Utah": 4, "Wyoming": 4,
    # 5 years
    "Missouri": 5,
    # 6 years
    "Maine": 6, "North Dakota": 6,
}
STATE_ALIAS = {"Washington DC": "D.C.", "District of Columbia": "D.C."}
STATES = sorted(set(list(TORT_SOL.keys()) + ["D.C."]))

SA_EXT = {
    "California":   {"penetration": None, "other": None,
                     "summary": "No SOL for touching of sexual body parts, rape, digital penetration, oral penetration, vaginal penetration, anal penetration, etc."},
    "New York":     {"penetration": 10,   "other": 10,
                     "summary": "10-year SOL for touching of sexual body parts, rape, digital penetration, oral penetration, vaginal penetration, anal penetration, etc."},
    "Texas":        {"penetration": 5,    "other": 2,
                     "summary": "5-year SOL for rape/penetration of mouth, anus, or vagina; 2-year SOL for all other conduct."},
    "Illinois":     {"penetration": None, "other": 2,
                     "summary": "No SOL for rape/penetration of mouth, anus, or vagina; 2-year SOL for all other conduct."},
    "Connecticut":  {"penetration": None, "other": 2,
                     "summary": "No SOL for rape/penetration of mouth, anus, or vagina; 2-year SOL for all other conduct."},
}

STATE_LIST_FORM = [
    "Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","Delaware","Florida","Georgia","Hawaii",
    "Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana","Maine","Maryland","Massachusetts","Michigan",
    "Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada","New Hampshire","New Jersey","New Mexico","New York",
    "North Carolina","North Dakota","Ohio","Oklahoma","Oregon","Pennsylvania","Rhode Island","South Carolina","South Dakota",
    "Tennessee","Texas","Utah","Vermont","Virginia","Washington","Washington DC","West Virginia","Wisconsin","Wyoming","Puerto Rico"
]

# =========================
# NON-LETHAL DEFENSIVE ITEMS (dropdown list)
# =========================
NON_LETHAL_ITEMS = [
    "Pepper Spray",
    "Personal Alarm",
    "Stun Gun",
    "Taser",
    "Self-Defense Keychain",
    "Tactical Flashlight",
    "Groin Kickers",
    "Personal Safety Apps",
    "Defense Flares",
    "Baton",
    "Kubotan",
    "Umbrella",
    "Whistle",
    "Combat Pen",
    "Pocket Knife",
    "Personal Baton",
    "Nunchaku",
    "Flashbang",
    "Air Horn",
    "Bear Spray",
    "Sticky Foam",
    "Tactical Scarf or Shawl",
    "Self-Defense Ring",
    "Hearing Protection",
]

# =========================
# OBJECTION SCRIPTS / REFERENCES
# =========================
OBJECTION_SCRIPTS = {
    "Incident Not Qualified":
        "I apologize, but the incident does not meet our firm's criteria. If that changes in the future, we'll contact you. "
        "In the meantime, please consider reaching out to other law firms.",
    "How much is the settlement":
        "I don't want to misinform you, as it really depends on the specifics of your case and the trauma involved. "
        "Factors like the incident and extent of damage are crucial. For example, in December 2022, the California Public Utilities "
        "Commission approved a $9 million settlement with Uber for not properly documenting and reporting sexual assault incidents.",
    "How much will the law firm charge me":
        "The standard fee is 40%, typical for law firms due to the risks involved. Our experienced lawyers can help you secure a larger "
        "settlement faster, and we’ll hire an expert witness to connect your health issues to your rideshare sexual assault case. "
        "You won’t pay anything upfront—we’ll handle your medical records and evidence gathering. "
        "Choosing a firm with seasoned professionals is crucial for achieving the best settlement. If we prove a link but don’t secure a settlement "
        "(which is rare), you won't owe anything.",
    "PC Disagreement Over 40% Fee":
        "I respect your decision, but the standard fee is 40%. Other firms may not charge less due to the uncertainty of securing a settlement. "
        "With our superlawyers and an expert witness, we’ll link your health issues to the rideshare sexual assault incident. You’re paying for convenience—"
        "there’s no need to gather records or go to court. If you proceed today, we can help with no upfront payment.",
    "Asking ID and other evidences":
        "To qualify for a settlement, it's crucial to retrieve your medical records. This ensures the funds go to the right person, protecting your benefits "
        "and strengthening your case. Please provide a copy of your government-issued ID and a selfie for verification. Additionally, any records, photos, "
        "or medication bottles as proof would be valuable. Your evidence is essential for us to help you effectively.",
    "Asking SSN":
        "The hospital must ensure they send the correct information. For legal purposes and proper documentation, we need your full name, address, date of birth, "
        "and Social Security number. I understand your concerns about sharing your Social Security number, but it’s essential for protecting your identity and ensuring "
        "that any settlement goes to the right person. This helps prevent relatives from falsely claiming the settlement and avoids potential financial issues. "
        "Your cooperation is vital for a smooth legal process.",
    "Asking last 4 digits - SSN":
        "Can I get the last four digits of your Social Security number for the HIPAA Release Form, which confirms your consent to release your medical records, "
        "and rest assured, they will remain private and confidential since law firms don’t file them and can be sanctioned if they do.",
    "I did not submit my information":
        "You probably filled out a survey or form online. If you or a loved one were involved in a rideshare sexual assault incident, we can connect you with top attorneys "
        "who are Super Lawyers. I'm here to help you pursue a settlement, and your case is important to us.",
    "Where are you from":
        "I'm calling from Dallas, Texas, representing the Advocate Rights Center, an intake center for ______ Law Firm. "
        "We assist clients in pursuing settlements related to rideshare sexual assault incidents.",
    "Scam Suspicions":
        "I understand your concern, but I won’t need your financial information or bank details. I only require your basic information to pursue your claim. "
        "Providing this information allows us to obtain essential records, like medical records and proof of injury, which are crucial for filing your claim and securing a settlement. "
        "Your cooperation is vital for building a strong case.",
    "Multi-District Litigation (MDL) vs. Class Action":
        "In multi-district litigation (MDL), settlements are based on each individual impact of their injuries from a rideshare sexual assault, ensuring fair compensation. "
        "On the other hand, class action lawsuits split settlements equally among all members, regardless of how much each person was affected.",
    "Class Action Clarification":
        "This isn't like a Class Action. Because each injury is different, the compensation is customized to match exactly what happened to you.",
    "I Need a Local Law Firm":
        "Claims about rideshare sexual assault incidents are now consolidated in the U.S. District Court for the Northern District of California under Judge Charles Breyer (MDL No. 3084). "
        "You don’t need an attorney licensed in your state anymore, making the process faster and outcomes more predictable. You can choose the law firm you prefer. "
        "We work with ______ Law, which has won hundreds of millions in liability settlements.",
    "What kind of claim is this?":
        "These are personal injury claims against the rideshare company for harm caused by incidents involving sexual assault. "
        "Victims have suffered injuries resulting in pain, suffering, and long-term trauma. The rideshare company is primarily responsible due to negligence in failing to properly screen drivers.",
    "Are settlements taxable?":
        "I'm not a tax expert and can't provide tax advice, but generally, settlements for personal injury or emotional/psychological damage (pain and suffering) are non-taxable. "
        "However, I can't confirm this definitively.",
    "What happens if I die?":
        "After you file the claim, the law firm will update it to name a new plaintiff, usually the estate administrator, since you can't represent yourself if you pass away. "
        "It's a good idea to create a will to ensure your assets go to your heirs as you want; otherwise, state laws will apply. "
        "A case manager will reach out after you sign the forms to verify your information and guide you through the process.",
    "Reasons for Using Plaid":
        "1) Verification: It helps confirm your identity and prevents impersonation, saving the law firm time and money on false claims.\n"
        "2) Medical Records: Your government ID allows us to obtain medical records while following privacy laws (HIPAA).\n"
        "3) Settlement Accuracy: We ensure settlement funds go to the right person and don’t ask for banking details until the law firm confirms the settlement.\n\n"
        "These steps are important for protecting your case and ensuring everything runs smoothly.",
    "Using Plaid: Quick Directions (verbal)":
        "To use Plaid, click the link, and you'll be taken to their platform. Here’s what to do:\n\n"
        "1. Enter the last four digits of your SSN.\n"
        "2. Allow access to your camera to take photos of the front and back of your driver’s license.\n"
        "3. Then, take a selfie by holding your phone up for about 10 seconds.\n"
        "This process matches your selfie with your driver’s license to confirm your identity.",
    "Has Attorney":
        "To avoid double representation issues, please ensure you don't have another attorney for your rideshare sexual assault case. "
        "If you do, we cannot assist you to protect your interests.",
    "Unanswered Client Callback Script":
        "The law firm has been trying to reach you to verify a few things. They might check in occasionally about your condition, "
        "especially since complications can affect your settlement.\n\n"
        "You can call them at (Number of Lawfirm). They might give you another number for direct contact with an attorney or paralegal, "
        "but this number will connect you to their office.\n\n"
        "Optional: If you can, let them know you have their number and will answer future calls. This builds trust and shows you’re engaged, "
        "which is important since they will invest time and resources in your case.",
    "RSA District Court?":
        "Claims about rideshare sexual assault incidents are now consolidated in the U.S. District Court for the Northern District of California under Judge Charles Breyer (MDL No. 3084).",
    "Rideshare Companies in Litigation":
        "Uber, Lyft, Via, Ola, Grab, Didi Chuxing, Bolt, Gett",
    "Settlement Claims in Rideshare Assault":
        "• Medical Expenses: Treatment and rehabilitation costs.\n"
        "• Emotional Distress: Compensation for psychological trauma.\n"
        "• Lost Wages: Income loss due to inability to work.\n"
        "• Punitive Damages: Penalties to deter misconduct.\n"
        "• Legal Fees: Reimbursement for attorney costs.\n"
        "• Pain and Suffering: Compensation for physical and emotional pain.\n"
        "• Future Medical Costs: Estimated ongoing treatment expenses.\n"
        "• Loss of Enjoyment: Diminished quality of life.\n"
        "• Property Damage: Reimbursement for damaged personal items.\n"
        "• Loss of Consortium: Claims for loss of companionship.",
    "Medical Office Three-Way Call":
        "We can do a three-way call with the medical office to confirm your injury. We'll ask them when you were last seen for your condition. "
        "With your permission, we can record the call and send it to the law firm. They just need proof that you’re a genuine claimant. "
        "This isn’t for evidence—your medical records will handle that—but to show that investing time and money in your case is worthwhile. "
        "They want to avoid claims that look like a lottery ticket. They aren’t asking for guarantees.",
    "Wagstaff Law Information":
        "Wagstaff Lawfirm\n940 Lincoln St, Denver, CO 80203\n303-376-6360\nhttps://www.wagstafflawfirm.com/\n\n"
        "About Us\nWagstaff Law Firm: National Mass Tort Attorneys with 40 years of experience. We offer a personal approach to help victims recover and hold negligent "
        "parties accountable for maximum compensation. Contact us at (972) 573-6040 or visit https://www.wagstafflawfirm.com/",
    "Instructions for Resending Rideshare Receipts":
        "Uber: Go to the Activity tab, select the ride, click the Receipt icon, and then choose resend email.\n\n"
        "Lyft: Open Lyft app > Ride history > Tap the ride > Scroll down > Tap 'Resend receipt' > Enter your email to send",
    "How to Report an Assault to Uber/Lyft (link)":
        "https://docs.google.com/document/d/1Oiljbf3oHqtoKDv2jArsXMIVw5hhuNrRiZ1MDl0aoqo/edit?usp=sharing",
    "Script for Irate Callers (link)":
        "https://docs.google.com/document/d/1wlQurtqG_0tVIUhBfHXL2R8fF58i8s64/edit?usp=sharing&ouid=116486877893425072265&rtpof=true&sd=true",
    "Responding to Law Firm (link)":
        "https://docs.google.com/document/d/1BNJoF14vqEkH2WojUC_H7AsWUmu-ZC1NVmvO0J_GN9Q/edit?usp=sharing",
    "Using Plaid: Quick Directions (doc link)":
        "https://docs.google.com/document/d/1P_jodMzz-2vc0vQsDbgCimCBDGDHyuNaFqyE7KmbO5Y/edit?usp=sharing",
    "ID and Proof Retrieval Script (link)":
        "https://docs.google.com/document/d/1DTcBIWg4NJfEgETe4bwagbz4refPSyoP/edit?usp=sharing&ouid=116486877893425072265&rtpof=true&sd=true",
    "Mailer – Commitment Script (link)":
        "https://docs.google.com/document/d/1VMxf5JcVIFN2ABXmkLHKdkvYJ6tfmSmIp0jlMrh7glE/edit?usp=sharing",
    "Esign Guide Text (link)":
        "https://docs.google.com/document/d/1e6sGJB8wRPwa2_sBEvLbDl4wUM4TsS8f46agwNWvIRE/edit?usp=sharing",
    "Esign Guide Email (link)":
        "https://docs.google.com/document/d/1zVTewqs7jtAB_yL0cdz8vz_8o-IfgoYVhj4KPNNG9M8/edit?usp=sharing",
    "Identity Verification Links (site)":
        "https://besthistorysites.net/",
    "PLAID Link":
        "https://advocaterightscenter.com/plaid_verification/",
    "How to Send Plaid Link to Clients (link)":
        "https://docs.google.com/document/d/1huakazfAU_-P3PORmcP5DLrdIn_pHRzGNjjdjnOWwVw/edit?usp=sharing",
    "How to Guide Clients in Plaid Text (link)":
        "https://docs.google.com/document/d/19Uj2gXI1WKOlnaVprvryvYipOgMAAum2gR4uDsMJ7B8/edit?usp=sharing",
    "SOP for Plaid (link)":
        "https://docs.google.com/document/d/1Rc_C3mqQ21CdpfbHAXzqDNernl32Jr-2/edit",
    "Call Transfers with C9 and Law Ruler (link)":
        "https://docs.google.com/document/d/1powoAbPlhqVV3q54ZlgFIZml70Iudrzh/edit?usp=sharing&ouid=116486877893425072265&rtpof=true&sd=true",
    "RSA - Objection Script (link)":
        "https://docs.google.com/document/d/14fYJyeWYuuIbQmwrzGMCkuvnVoIwqrKy/edit?usp=sharing&ouid=116486877893425072265&rtpof=true&sd=true",
    "Rideshare Waggy (SMS templates)":
        "Lorenia: 213-347-9246\n"
        "• We received your signed docs for your Rideshare Assault Claim. A paralegal from Wagstaff will call from 213-347-9246 within 5-10 business days.\n"
        "• Hi Monica, the paralegal for your Rideshare Assault Claim is trying to reach you. Call her at 213-347-9246 to reconfirm your details."
}

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

def join_list(values, dash_if_empty=True):
    if not values:
        return "—" if dash_if_empty else ""
    return ", ".join([str(v) for v in values])

def tier_and_aggravators(flags):
    t1 = bool(flags.get("Rape/Penetration") or flags.get("Forced Oral/Forced Touching"))
    t2 = bool(flags.get("Touching/Kissing w/o Consent") or flags.get("Indecent Exposure") or flags.get("Masturbation Observed"))
    aggr_kidnap = bool(flags.get("Kidnapping Off-Route w/ Threats"))
    aggr_imprison = bool(flags.get("False Imprisonment w/ Threats"))
    aggr = []
    if aggr_kidnap: aggr.append("Kidnapping w/ threats")
    if aggr_imprison: aggr.append("False imprisonment w/ threats")
    if t1: base = "Tier 1"
    elif t2: base = "Tier 2"
    else: base = "Unclear"
    label = f"{base} (+ Aggravators: {', '.join(aggr)})" if base in ("Tier 1","Tier 2") and aggr else base
    return label, aggr

def sa_category(flags):
    if flags.get("Rape/Penetration") or flags.get("Forced Oral/Forced Touching"):
        return "penetration"
    if flags.get("Touching/Kissing w/o Consent") or flags.get("Indecent Exposure") or flags.get("Masturbation Observed"):
        return "other"
    return None

def sol_rule_for(state, category):
    if category and state in SA_EXT:
        data = SA_EXT[state]
        years = data[category]
        summary = data["summary"]
        return years, f"{state}: {summary}", True
    years = TORT_SOL.get(state)
    return years, f"{state}: General tort SOL = {years} year(s).", False

def categorical_brief(flags):
    buckets = []
    if flags.get("Rape/Penetration"): buckets.append("rape/penetration")
    if flags.get("Forced Oral/Forced Touching"): buckets.append("forced oral/forced touching")
    if flags.get("Touching/Kissing w/o Consent"): buckets.append("unwanted touching/kissing")
    if flags.get("Indecent Exposure"): buckets.append("indecent exposure")
    if flags.get("Masturbation Observed"): buckets.append("masturbation observed")
    if flags.get("Kidnapping Off-Route w/ Threats"): buckets.append("kidnapping w/ threats")
    if flags.get("False Imprisonment w/ Threats"): buckets.append("false imprisonment w/ threats")
    return ", ".join(buckets) if buckets else "—"

def split_legal_name(full_legal: str):
    first = middle = last = ""
    if not full_legal:
        return first, middle, last
    parts = [p for p in full_legal.strip().split() if p]
    if len(parts) == 1:
        first = parts[0]
    elif len(parts) == 2:
        first, last = parts
    else:
        first, middle, last = parts[0], " ".join(parts[1:-1]), parts[-1]
    return first, middle, last

def calc_age(dob: date):
    if not dob: return ""
    today = date.today()
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return max(0, years)

# =========================
# APP
# =========================
st.title("Rideshare Intake Qualifier · Script-Calibrated (Vertical)")

def render():
    # ---------- INTRODUCTION ----------
    script_block(
        "INTRODUCTION\n"
        "Thank you for calling the Advocate Rights Center, this is **[Your Name]**. How are you doing today?\n\n"
        "May I have your **full name**, and then your **full legal name** exactly as it appears on your ID?\n\n"
        "Before we continue, may I have your **permission to record** this call for legal and training purposes? "
        "It will remain private and confidential, and it’s never filed publicly unless you approve and a case goes to court. "
        "Fewer than 1 in 1,000 cases ever do, since most resolve through settlement."
    )
    caller_full_name = st.text_input("Full name (as provided verbally)", key="caller_full_name")
    caller_legal_name = st.text_input("Full legal name (exact on ID)", key="caller_legal_name")
    consent_recording = st.toggle("Permission to record (private & confidential)", value=False, key="consent_recording")

    # Prior firm question (under recording consent)
    st.markdown("**As far as you can remember, have you signed up with any Law Firm to represent you on this case but then got disqualified for any reason?**")
    prior_firm_radio = st.radio("We still might be able to help but need to know.", ["No", "Yes"], horizontal=True, key="prior_firm_any")
    prior_firm_any = (prior_firm_radio == "Yes")
    prior_firm_note = ""
    if prior_firm_any:
        prior_firm_note = st.text_area("If yes, share anything you recall (optional — dates, firm name, reason):", key="prior_firm_note")
        script_block("“Thank you for sharing that. Prior disqualifications can happen for technical reasons and do not close the door here. "
                     "Knowing this helps us prevent any conflicts and move your file faster.”")
    else:
        script_block("“Thanks for confirming. That keeps the intake simple and avoids any duplicate-representation issues.”")

    st.markdown("---")

    # =========================
    # 1) Story & First-Level Qualification
    # =========================
    st.markdown("### 1) Story & First-Level Qualification")

    # Q1 — Narrative
    st.markdown("**Q1. In your own words, please feel free to describe what happened during the ride.**")
    narr = st.text_area("Caller narrative", key="q1_narr")
    if narr.strip():
        script_block(
            "“Thank you for trusting me with that. What you’ve shared is painful and important. "
            "You’re in control of this conversation, and we’ll move at your pace. "
            "If anything feels hard to say, we can take a moment and continue when you’re ready.”"
        )

    # Acts (under Q1)
    st.subheader("Acts (check all that apply)")
    rape = st.checkbox("Rape/Penetration", key="act_rape")
    forced_oral = st.checkbox("Forced Oral/Forced Touching", key="act_forced_oral")
    touching = st.checkbox("Touching/Kissing w/o Consent", key="act_touch")
    exposure = st.checkbox("Indecent Exposure", key="act_exposure")
    masturb = st.checkbox("Masturbation Observed", key="act_masturb")
    kidnap = st.checkbox("Kidnapping Off-Route w/ Threats (Tier-3 aggravator; must have Tier 1 or 2)", key="act_kidnap")
    imprison = st.checkbox("False Imprisonment w/ Threats (Tier-3 aggravator; must have Tier 1 or 2)", key="act_imprison")

    act_flags = {
        "Rape/Penetration": rape,
        "Forced Oral/Forced Touching": forced_oral,
        "Touching/Kissing w/o Consent": touching,
        "Indecent Exposure": exposure,
        "Masturbation Observed": masturb,
        "Kidnapping Off-Route w/ Threats": kidnap,
        "False Imprisonment w/ Threats": imprison
    }
    tier_label, aggr_list = tier_and_aggravators(act_flags)
    base_tier_ok = ("Tier 1" in tier_label) or ("Tier 2" in tier_label)

    # Q2 — Platform
    st.markdown("**Q2. Which rideshare platform was it?**")
    company = st.selectbox("Select platform", ["Uber", "Lyft", "Other"], key="q2_company")
    if company:
        script_block(f"“Thanks for confirming it was {company}. That helps us pull the right records and policies.”")

    # Pickup / Drop-off (extension to Q2)
    st.markdown("**Pickup / Drop-off (extension to Q2)**")
    st.caption("Let’s anchor the timeline and route.")
    pickup = st.text_input("Pickup location (address/description)", key="pickup")
    dropoff = st.text_input("Drop-off location (address/description)", key="dropoff")
    if pickup.strip() or dropoff.strip():
        script_block(
            "“Thank you — those locations help lock in the route and jurisdiction. "
            "If you remember nearby landmarks or cross-streets, we can add those too. You’re doing great.”"
        )

    # Q3 — Confident receipt request (uses PC name)
    st.markdown("**Q3. Receipts / Proof**")
    pc_name = caller_full_name or caller_legal_name or "there"
    st.markdown(
        f"<div class='callout'>"
        f"<b>{pc_name}</b>, we need a copy of the ride receipt — "
        f"<u>both</u> the <b>Email Copy</b> and the <b>In-App Receipt</b> (or a <b>screenshot of the receipt</b>). "
        f"These are some of the strongest pieces of proof we can attach to your file."
        f"</div>", unsafe_allow_html=True
    )
    receipt_evidence = st.multiselect(
        "What can you provide as receipt evidence?",
        ["PDF", "Email", "Screenshot of Receipt", "In-App Receipt (screenshot)", "Other"],
        key="receipt_evidence"
    )
    receipt_evidence_other = st.text_input("If Other, describe", key="receipt_evidence_other")
    if receipt_evidence_other and "Other" not in receipt_evidence:
        receipt_evidence.append(f"Other: {receipt_evidence_other.strip()}")
    if receipt_evidence:
        script_block("“Perfect — those receipts and screenshots directly link the ride to your account and timestamp the trip.”")

    # Uploads (includes audio/video; counts for Wagstaff evidence)
    proof_uploads = st.file_uploader(
        "Upload now (ride receipt, therapy/medical note, police confirmation, audio/video) — images, PDFs, audio, or video",
        type=["pdf", "png", "jpg", "jpeg", "heic", "mp4", "mov", "m4a", "mp3", "wav"],
        accept_multiple_files=True,
        key="proof_uploads"
    )
    uploaded_files = proof_uploads or []
    uploaded_names = [f.name for f in uploaded_files]
    any_pdf_uploaded = any(n.lower().endswith(".pdf") for n in uploaded_names)
    any_av_uploaded = any(n.lower().endswith(ext) for n in uploaded_names for ext in (".mp4",".mov",".m4a",".mp3",".wav"))
    if uploaded_names:
        script_block("“Thanks for those uploads — I see them here and will attach them to your file.”")

    # SMS flow (wording change)
    st.markdown("**SMS for Documentation**")
    script_block(
        "“I’m going to send you an SMS containing my email address. "
        "You can send the necessary documentation later today, or even as we speak — whichever is easier.”"
    )
    sms_phone = st.text_input("Phone number where you receive SMS", key="sms_phone")
    phone_new_radio = st.radio("Is this a new phone number, or did you recently change your phone number?", ["No", "Yes — new/recently changed"], horizontal=True, key="sms_is_new")
    if sms_phone:
        # mirror this to best phone for follow-up
        st.session_state["caller_phone"] = sms_phone
        if phone_new_radio.startswith("Yes"):
            script_block("“Thanks — just a heads up: if it’s new, some verification tools (like Plaid) may briefly show a mismatch. We can note that.”")
        else:
            script_block("“Great — we’ll use this as your best contact number going forward.”")
    st.button("Mark SMS sent (placeholder)", key="btn_sms_sent")

    # ---- EDUCATION #1 ---- (verbatim)
    script_block(
        "HOW THIS HAPPENED →  EDUCATE CLIENT / SAFETY ZONE\n"
        "Well, let me tell you what people have uncovered about Rideshares and why people like you are coming forward. "
        "And again, I appreciate you trusting us with this.\n\n"
        "Uber & Lyft have been exposed for improperly screening drivers, failing to remove dangerous drivers, and misrepresenting its safety practices.\n\n"
        "For example, the New York Times uncovered sealed court documents showing that over 400,000 incidents of sexual assault and misconduct were reported to Uber between 2017
