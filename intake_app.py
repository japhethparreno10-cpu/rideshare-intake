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
.script {border-left:4px solid #9ca3af; background:#f3f4f6; color:#111827; padding:12px 14px; border-radius:8px; margin:8px 0 12px 0; font-size:0.97rem; white-space:pre-wrap;}
.callout {border-left:6px solid #2563eb; background:#eef2ff; color:#1e3a8a; padding:12px 14px; border-radius:12px; margin:8px 0 12px 0;}
.small {font-size: 0.9rem; color:#4b5563;}
hr {border:0; border-top:1px solid #e5e7eb; margin:12px 0;}
[data-testid="stDataFrame"] div, [data-testid="stTable"] div {font-size: 1rem;}
.copy {font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; white-space:pre-wrap;}
.kv {font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; white-space:pre-wrap;}
/* Qualifier level ribbons */
.qual {padding:10px 12px; border-radius:10px; color:#111827; margin:8px 0 6px 0; font-weight:600;}
.lvl-yellow {background:#fef3c7; border:1px solid #fde68a;}
.lvl-orange {background:#ffedd5; border:1px solid #fdba74;}
.lvl-lgreen {background:#dcfce7; border:1px solid #86efac;}
.lvl-green  {background:#d1fae5; border:1px solid #6ee7b7;}
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
        "and Social Security number.",
    "Asking last 4 digits - SSN":
        "I understand your concerns about sharing your Social Security number, but it’s essential for protecting your identity and ensuring that any settlement goes to the right person. "
        "This helps prevent relatives from falsely claiming the settlement and avoids potential financial issues. Your cooperation is vital for a smooth legal process.",
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
        "https://docs.google.com/document/d/1e6sGJB8wRPwa2_sBEvLbDl4wUM4Ts8f46agwNWvIRE/edit?usp=sharing",
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

    # Prior firm question
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

    st.markdown("<div class='qual lvl-yellow'>Qualification Level 1</div>", unsafe_allow_html=True)

    # =========================
    # 1) Story & First-Level Qualification
    # =========================
    st.markdown("### 1) Story & First-Level Qualification")

    # Q1 — Narrative
    # Q1 — Narrative
    # Q1 — Narrative
    st.markdown("**Q1. In your own words, please feel free to describe what happened during the ride.**")
    narr = st.text_area("Caller narrative", key="q1_narr")

    # Empathy/acknowledgement right after the caller speaks
    pc_name_for_empathy = caller_full_name or caller_legal_name or ""
    if narr.strip():
    script_block(
        f"""“{(pc_name_for_empathy + ', ') if pc_name_for_empathy else ''}thank you for trusting me with that.
    I’m so sorry this happened to you. What you shared matters, and you did nothing to deserve it.

    You’re in control of this conversation. If you need to pause, take a break, or skip any question, just let me know—we’ll go entirely at your pace.

    If anything feels overwhelming, we can take a breath together and return to it when you’re ready.”"""
    )
    script_block(
        "“To make sure I understood correctly, I’ll briefly reflect back what I heard in neutral, non-graphic terms. "
        "Please correct me if I miss anything—or tell me if you’d prefer not to revisit any part.”"
    )

    script_block(
        "“To make sure I understood correctly, I’ll briefly reflect back what I heard in neutral, non-graphic terms. "
        "Please correct me if I miss anything—or tell me if you’d prefer not to revisit any part.”"
    )


    # Acts (under Q1)
    st.subheader("Acts (check all that apply)")
    rape = st.checkbox("Rape/Penetration", key="act_rape")
    forced_oral = st.checkbox("Forced Oral/Forced Touching", key="act_forced_oral")
    touching = st.checkbox("Touching/Kissing w/o Consent", key="act_touch")
    exposure = st.checkbox("Indecent Exposure", key="act_exposure")
    masturb = st.checkbox("Masturbation Observed", key="act_masturb")
    verbal_only = st.checkbox("Verbal Abuse only (No Sexual Acts)", key="act_verbal_only")
    attempt_only = st.checkbox("Attempt/minor contact only", key="act_attempt_only")
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
        script_block("“Thanks for confirming the platform. That helps us pull the right records and policies.”")

    # Education #1 (Part A) — placed above Pickup/Drop-off
    script_block(
        "HOW THIS HAPPENED →  EDUCATE CLIENT / SAFETY ZONE\n"
        "Well, let me tell you what people have uncovered about Rideshares and why people like you are coming forward. And again, I appreciate you trusting us with this.\n\n"
        "Uber & Lyft have been exposed for improperly screening drivers, failing to remove dangerous drivers, and misrepresenting its safety practices.\n\n"
        "For example, the New York Times uncovered sealed court documents showing that over 400,000 incidents of sexual assault and misconduct were reported to Uber between 2017 and 2022 . . . which is about 1 incident every 8 minutes."
    )

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

    # Q3 — Receipts / Proof
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

    # Uploads
    proof_uploads = st.file_uploader(
        "Upload now (ride receipt, therapy/medical note, police confirmation, audio/video) — images, PDFs, audio, or video",
        type=["pdf","png","jpg","jpeg","heic","mp4","mov","m4a","mp3","wav"],
        accept_multiple_files=True,
        key="proof_uploads"
    )
    uploaded_files = proof_uploads or []
    uploaded_names = [f.name for f in uploaded_files]
    any_pdf_uploaded = any(n.lower().endswith(".pdf") for n in uploaded_names)
    any_av_uploaded = any(n.lower().endswith(ext) for n in uploaded_names for ext in (".mp4",".mov",".m4a",".mp3",".wav"))
    if uploaded_names:
        script_block("“Thanks for those uploads — I see them here and will attach them to your file.”")

    # SMS flow
    st.markdown("**SMS for Documentation**")
    script_block(
        "“I’m going to send you an SMS containing my email address. "
        "You can send the necessary documentation later today, or even as we speak — whichever is easier.”"
    )
    sms_phone = st.text_input("Phone number where you receive SMS", key="sms_phone")
    sms_is_new = st.radio("Is this a new phone number, or did you recently change your phone number?",
                          ["No", "Yes — new/recently changed"], horizontal=True, key="sms_is_new")
    if sms_phone:
        st.session_state["caller_phone"] = sms_phone
        if sms_is_new == "Yes — new/recently changed":
            script_block("“Got it — thanks. I’ll note this is a new number in case any verification systems (like Plaid) flag a mismatch.”")
        else:
            script_block("“Great — I’ll use this as your best contact number going forward.”")
    st.button("Mark SMS sent (placeholder)", key="btn_sms_sent")

    # Education #1 (Part B)
    script_block(
        "[[ Now when you consider that Uber originally only reported about 12,500 incidents during that same period, you can argue the company has been seriously misleading the level of safety it offers passengers. ]]\n\n"
        "Now, we know many people don’t report these incidents. So, coming forward helps you and others obtain justice and compensation. "
        "[[ And, it truly does help force Uber & Lyft to pay for their negligence, and provide real safety measures so these incidents stop happening.]]"
    )

    st.markdown("<div class='qual lvl-orange'>Qualification Level 2</div>", unsafe_allow_html=True)

    # =========================
    # 3) Second-Level Qualification (Reporting & Timing)
    # =========================
    st.markdown("### 3) Second-Level Qualification (Reporting & Timing)")

    # Q4 — Date/Time
    st.markdown("**Q4. Do you remember the date this happened?**")
    has_incident_date = st.toggle("Caller confirms they know the date", value=False, key="q4_hasdate")
    incident_date = st.date_input("Select Incident Date", value=TODAY.date(), key="q4_date") if has_incident_date else None
    incident_time = st.time_input("Incident Time (for timing rules)", value=time(21, 0), key="time_for_calc")
    if has_incident_date and incident_date:
        script_block("“Thanks — the specific date lets the attorneys verify deadlines and request the correct records.”")

    # Q5 — Reporting
    st.markdown("**Q5. Did you report the incident to anyone?** (Uber/Lyft, Police, Physician, Therapist, Family/Friend)")
    st.caption("Choose everything that applies — even telling a trusted person helps build the timeline.")
    reported_to = st.multiselect(
        "Select all that apply",
        ["Rideshare Company","Physician","Friend or Family Member","Therapist","Police Department","NO (DQ, UNLESS TIER 1 OR MINOR)"],
        key="q5_reported"
    )
    if reported_to:
        script_block(f"“Thank you — noting {', '.join(reported_to)} helps us build a reliable timeline for your case.”")

    # Per-channel details
    report_dates = {}
    family_report_dt = None

    # Family/Friend
    fam_first = fam_last = fam_phone = ""
    if "Friend or Family Member" in reported_to:
        st.markdown("**Family/Friend Contact Details**")
        fam_first = st.text_input("First name (Family/Friend)", key="fam_first")
        fam_last  = st.text_input("Last name (Family/Friend)", key="fam_last")
        fam_phone = st.text_input("Phone number (Family/Friend)", key="fam_phone")
        ff_date = st.date_input("Date informed Family/Friend", value=TODAY.date(), key="q5a_dt_ff")
        ff_time = st.time_input("Time informed Family/Friend", value=time(21,0), key="q5a_tm_ff")
        report_dates["Family/Friends"] = ff_date
        family_report_dt = datetime.combine(ff_date, ff_time)

    # Physician
    phys_name = phys_fac = phys_addr = ""
    if "Physician" in reported_to:
        st.markdown("**Physician Details**")
        phys_name = st.text_input("Physician Name", key="phys_name")
        phys_fac  = st.text_input("Clinic/Hospital Name", key="phys_fac")
        phys_addr = st.text_input("Clinic/Hospital Address", key="phys_addr")
        report_dates["Physician"] = st.date_input("Date reported to Physician", value=TODAY.date(), key="q5a_dt_phys")

    # Therapist
    ther_name = ther_fac = ther_addr = ""
    if "Therapist" in reported_to:
        st.markdown("**Therapist Details**")
        ther_name = st.text_input("Therapist Name", key="ther_name")
        ther_fac  = st.text_input("Clinic/Hospital Name", key="ther_fac")
        ther_addr = st.text_input("Clinic/Hospital Address", key="ther_addr")
        report_dates["Therapist"] = st.date_input("Date reported to Therapist", value=TODAY.date(), key="q5a_dt_ther")

    # Police
    police_station = police_addr = ""
    if "Police Department" in reported_to:
        st.markdown("**Police Details**")
        police_station = st.text_input("Name of Police Station", key="police_station")
        police_addr    = st.text_input("Police Station Address", key="police_addr")
        report_dates["Police"] = st.date_input("Date reported to Police", value=TODAY.date(), key="q5a_dt_police")

    # Rideshare company channel
    rep_rs_company = ""
    if "Rideshare Company" in reported_to:
        st.markdown("**Rideshare Company (reported)**")
        rep_rs_company = st.selectbox("Which company did you report to?", ["Uber", "Lyft"], key="rep_rs_company")
        report_dates["Rideshare company"] = st.date_input("Date reported to Rideshare company", value=TODAY.date(), key="q5a_dt_rs")

    # If NOT reported to rideshare company: show suggestion
    if "Rideshare Company" not in reported_to:
        target = company if company in ("Uber","Lyft") else "the rideshare company"
        script_block(f"Are you open if the Atty would request for you to report to {target} to strengthen your case?")

    # Q6 — Scope
    st.markdown("**Q6. Did the incident happen inside the car, just outside, or did it continue after you exited?**")
    scope_choice = st.selectbox(
        "Select scope",
        ["Inside the car", "Just outside the car", "Furtherance from the car", "Unclear"],
        key="scope_choice"
    )
    inside_near = scope_choice in ["Inside the car", "Just outside the car", "Furtherance from the car"]
    if scope_choice and scope_choice != "Unclear":
        script_block(f"“Got it — {scope_choice.lower()}. That helps confirm it occurred within the rideshare’s safety responsibility.”")

    # Education #2 — Safe Rides Fee
    script_block(
        "Education Insert #2 — “Safe Rides Fee”\n"
        "Jay: “____, what’s especially troubling is that Uber and Lyft have had knowledge of these dangers since at least 2014.\n"
        "That year, Uber introduced a $1 ‘Safe Rides Fee’ — claiming it funded driver checks and safety upgrades. "
        "But investigations found that most of the $500 million collected went to profit, not safety.\n"
        "They later just renamed it a ‘booking fee.’ Survivors were paying for safety that never arrived.”"
    )

    st.markdown("<div class='qual lvl-lgreen'>Qualification Level 3</div>", unsafe_allow_html=True)

    # =========================
    # 5) Injury & Case-Support
    # =========================
    st.markdown("### 5) Injury & Case-Support Questions")

    # Q7 — Injuries
    st.markdown("**Q7. Were you injured physically, or have you experienced emotional effects afterward?**")
    injury_physical = st.checkbox("Physical injury", key="inj_physical")
    injury_emotional = st.checkbox("Emotional effects (anxiety, nightmares, etc.)", key="inj_emotional")
    injuries_summary = st.text_area("If comfortable, briefly describe injuries/effects", key="injuries_summary")
    if injury_physical or injury_emotional or injuries_summary.strip():
        script_block("“I’m sorry you’re dealing with these effects. Your health matters, and we’ll reflect this in the case.”")

    # Q8 — Treatment (only if injured)
    provider_name = provider_facility = ""
    therapy_start = first_visit = last_visit = None
    if injury_physical or injury_emotional or injuries_summary.strip():
        st.markdown("**Q8. Have you spoken to a doctor, therapist, or counselor?**")
        provider_name = st.text_input("Provider name (optional)", key="provider_name")
        provider_facility = st.text_input("Facility/Clinic (optional)", key="provider_facility")
        first_visit = st.date_input("Date of the first visit", value=None, key="first_visit")
        last_visit = st.date_input("Date of the last visit", value=None, key="last_visit")
        therapy_toggle = st.toggle("Add therapy start date (if applicable)", key="therapy_toggle", value=False)
        therapy_start = st.date_input("Therapy start date (if any)", value=TODAY.date(), key="therapy_start") if therapy_toggle else None
        if provider_name.strip() or provider_facility.strip() or therapy_start or first_visit or last_visit:
            script_block("“Thank you — treatment notes are strong, objective support for your experience.”")

    # Q9 — Meds
    st.markdown("**Q9. Do you take any medications related to this?**")
    medication_name = st.text_input("Medication (optional)", key="medication_name")
    pharmacy_name = st.text_input("Pharmacy (optional)", key="pharmacy_name")
    if medication_name.strip() or pharmacy_name.strip():
        script_block("“Understood. Pharmacy records help connect treatment to what you went through.”")

    # Education #3 — Law Firm & Contingency
    script_block(
        "Education Insert #3 — Law Firm & Contingency\n"
        "Jay: “____, based on what you’ve told me, you Might have a valid case. Here’s how pursuing a settlement works:\n"
        "You hire the law firm on a contingency basis — no upfront costs, no out-of-pocket fees. You only owe if they win you a recovery.\n"
        "We are the intake center for The Wagstaff Law Firm. Their attorneys are nationally recognized — many named Super Lawyers (top 5% of all attorneys). "
        "Judges across the country have appointed them to nine national Plaintiff Steering Committees, reserved for the top trial lawyers in corporate negligence cases.\n"
        "They’re now applying that same leadership to hold Uber and Lyft accountable for failing survivors like you.”"
    )

    st.markdown("<div class='qual lvl-green'>Qualification Level 4</div>", unsafe_allow_html=True)

    # =========================
    # Contact & Screening
    # =========================
    st.markdown("### Contact & Screening")
    caller_phone = st.text_input("Best phone number", value=st.session_state.get("caller_phone", ""), key="caller_phone")
    caller_email = st.text_input("Best email", key="caller_email")
    state = st.selectbox("Incident state", STATES, index=(STATES.index("California") if "California" in STATES else 0), key="q_state")

    st.markdown("**Rideshare submission & response (if any)**")
    rs_submit_how = st.text_input("How did you submit to Uber/Lyft? (email/app/other)", key="q8_submit_how")
    rs_received_response = st.toggle("Company responded", value=False, key="q9_resp_toggle")
    rs_response_detail = st.text_input("If yes, what did they say? (optional)", key="q9_resp_detail")

    st.markdown("**Standard Screening**")
    gov_id = st.toggle("Government ID provided", value=False, key="elig_id")
    female_rider = st.toggle("Female rider", value=False, key="elig_female")
    rider_not_driver = st.toggle("Caller was the rider (not the driver)", value=True, key="elig_rider_not_driver")
    has_atty = st.toggle("Already has an attorney", value=False, key="elig_atty")

    st.markdown("**Character disclosure (does not affect your case outcome — for preparation only)**")
    script_block("This will not affect your case. So the law firm can be prepared for any character issues, do you have any felonies or criminal history?")
    felony_answer = st.radio("Please select one", ["No", "Yes"], horizontal=True, key="q10_felony")
    felony = (felony_answer == "Yes")

    # ===== Weapons / Force =====
    st.markdown("**Did the driver threaten to us or actually use any weapons? Or use means of force during the sexual assault, such as gun, knife, or choking?**")
    driver_used_weapon = st.radio("Select one", ["No", "Yes"], horizontal=True, key="driver_used_weapon")
    driver_force_detail = ""
    if driver_used_weapon == "Yes":
        driver_force_detail = st.text_area("If yes, please elaborate.", key="driver_force_detail")
        script_block("Okay, [repeat type of weapon or means of force]. That’s very serious and the details help paint a full picture of the situation. I’m so sorry that happened.")
    else:
        script_block("Okay, although there was no weapon, this is still a very serious situation and does not change the magnitude of the incident.")

    # Wagstaff-only victim weapon question
    st.markdown("**Were you carrying a weapon at the time of the assault? (Wagstaff eligibility only)**")
    client_weapon_ans = st.radio("Select one", ["No", "Yes"], horizontal=True, key="client_weapon")
    client_weapon = (client_weapon_ans == "Yes")

    non_lethal_options = [
        "Pepper Spray","Personal Alarm","Stun Gun","Taser","Self-Defense Keychain","Tactical Flashlight","Groin Kickers",
        "Personal Safety Apps","Defense Flares","Baton","Kubotan","Umbrella","Whistle","Combat Pen","Pocket Knife",
        "Personal Baton","Nunchaku","Flashbang","Air Horn","Bear Spray","Sticky Foam","Tactical Scarf or Shawl",
        "Self-Defense Ring","Hearing Protection"
    ]
    lethal_flags = {"Firearm": False, "Knife": False, "Other lethal": False}
    nonlethal_selected = []
    if client_weapon:
        st.caption("(Personal defense tools like pepper spray/mace may not be a weapon.)")
        nonlethal_selected = st.multiselect("If yes, select any **non-lethal defensive items** (these generally do not disqualify for Wagstaff):",
                                            non_lethal_options, key="nonlethal_items")
        lethal_flags["Firearm"] = st.checkbox("Firearm", key="client_firearm")
        lethal_flags["Knife"] = st.checkbox("Knife (lethal intent)", key="client_knife")
        lethal_flags["Other lethal"] = st.checkbox("Other lethal weapon", key="client_other_lethal")
        script_block("Okay, thank you for that. And I appreciate your honesty. But based upon the current guidelines, the law firm may not be accepting cases where the victim had a weapon.")
    else:
        script_block("Okay, you did not have a weapon with you. That’s all we need on that part — thank you for confirming.")

    # Declines specific to Triten from Acts:
    # (already captured via 'verbal_only' and 'attempt_only' under Acts)

    # =========================
    # Settlement Process + Education #4
    # =========================
    st.markdown("### Settlement Process")
    script_block(
        "Here’s what to expect: after discovery, the court schedules four bellwether test trials — real trials that guide settlement ranges for everyone else.\n"
        "That means you won’t have to retell your story in court. Your records and documents will speak for you, and your settlement will be based on your individual experience."
    )
    script_block(
        "Education Insert #4 — Timeline for Settlement Distribution\n"
        "Jay: “____, once the bellwether trials conclude, those results usually spark settlement negotiations. "
        "That’s when distributions begin — survivors don’t have to wait for every trial to finish. "
        "The test results give both sides the framework to resolve cases sooner.”"
    )

    # =========================
    # Identity for Records (Full SSN + last4 fallback)
    # =========================
    st.markdown("### Identity for Records")
    pc_name_local = caller_full_name or caller_legal_name or "there"
    st.markdown(f"**{pc_name_local}, I need your Social Security Number.**")

    # SSN education split into TWO separate blocks (not together)
    script_block(
        "The hospital must ensure they send the correct information. For legal purposes and proper documentation, "
        "we need your full name, address, date of birth, and Social Security number."
    )
    script_block(
        "I understand your concerns about sharing your Social Security number, but it’s essential for protecting your identity "
        "and ensuring that any settlement goes to the right person. This helps prevent relatives from falsely claiming the settlement "
        "and avoids potential financial issues. Your cooperation is vital for a smooth legal process."
    )

    full_ssn = st.text_input("Social Security Number (###-##-####)", key="full_ssn")
    st.caption("If you prefer, you can share just the **last 4 digits**; those are often enough for HIPAA releases.")
    ssn_last4 = st.text_input("SSN last 4 (optional)", max_chars=4, key="ssn_last4")
    full_ssn_on_file = bool(full_ssn.strip())

    # ========= Calculations =========
    used_date = (incident_date or TODAY.date())
    incident_time_obj = incident_time or time(0, 0)
    incident_dt = datetime.combine(used_date, incident_time_obj)

    category = "penetration" if (rape or forced_oral) else ("other" if (touching or exposure or masturb) else None)
    sol_state = STATE_ALIAS.get(state, state)
    sol_years, sol_rule_text, used_sa = sol_rule_for(sol_state, category)

    if sol_years is None:
        sol_end = None
        file_by_deadline = None
        sol_time_ok = True
    else:
        sol_end = incident_dt + relativedelta(years=+int(sol_years))
        file_by_deadline = sol_end - timedelta(days=45)
        sol_time_ok = TODAY <= sol_end

    # earliest report math
    all_dates = [d for d in report_dates.values() if d]
    if family_report_dt:
        all_dates.append(family_report_dt.date())
    earliest_report_date = min(all_dates) if all_dates else None
    delta_days = (earliest_report_date - incident_dt.date()).days if earliest_report_date else None

    earliest_channels = []
    if earliest_report_date:
        for k, v in report_dates.items():
            if v == earliest_report_date:
                earliest_channels.append(k)
    earliest_is_family = (earliest_channels == ["Family/Friends"]) or (set(earliest_channels) == {"Family/Friends"})

    # ===== Eligibility =====
    # Wagstaff — accepts Uber or Lyft; requires report (or audio/video), no felony, scope, tier, SOL OK, no atty, no (lethal) client weapon
    has_allowed_report = any(ch in report_dates for ch in ["Rideshare company","Police","Therapist","Physician"]) or ("Family/Friends" in report_dates)
    within_24h_family_ok = True
    if set(report_dates.keys()) == {"Family/Friends"}:
        if not family_report_dt:
            within_24h_family_ok = False
        else:
            delta_hours = (family_report_dt - incident_dt).total_seconds() / 3600.0
            within_24h_family_ok = (0 <= delta_hours <= 24.0)
    wag_report_ok = (has_allowed_report and (within_24h_family_ok or not set(report_dates.keys()) == {"Family/Friends"})) or any_av_uploaded
    wag_common_ok = (not has_atty) and inside_near and base_tier_ok and sol_time_ok and (company in ("Uber","Lyft"))
    wag_no_felony = (not felony)
    client_weapon_lethal = client_weapon and (lethal_flags["Firearm"] or lethal_flags["Knife"] or lethal_flags["Other lethal"])
    wag_weapon_ok = not client_weapon_lethal  # ONLY Wagstaff declines if victim carried lethal weapon
    wag_ok = wag_common_ok and wag_report_ok and wag_no_felony and wag_weapon_ok

    # Triten — requires Email/PDF receipt, ID, female rider, not driver, report (family within 14d), no atty, tier, scope, SOL OK, Uber/Lyft, declines verbal/attempt-only
    triten_receipt_ok = ("Email" in receipt_evidence) or ("PDF" in receipt_evidence) or any_pdf_uploaded
    triten_id_ok = bool(gov_id)
    triten_gender_ok = bool(female_rider)
    triten_role_ok = bool(rider_not_driver)
    triten_report_any = bool(report_dates) or bool(family_report_dt)
    triten_family_14_ok = True
    if triten_report_any and earliest_is_family:
        triten_family_14_ok = (delta_days is not None) and (0 <= delta_days <= 14)
    triten_no_atty = (not has_atty)
    triten_tier_ok = base_tier_ok and (not verbal_only) and (not attempt_only)
    triten_scope_ok = inside_near
    triten_sol_ok = sol_time_ok
    triten_company_ok = (company in ("Uber","Lyft"))
    triten_ok = all([
        triten_receipt_ok, triten_id_ok, triten_gender_ok, triten_role_ok,
        triten_report_any, triten_family_14_ok, triten_no_atty, triten_tier_ok,
        triten_scope_ok, triten_sol_ok, triten_company_ok
    ])

    # =========================
    # Eligibility Snapshot
    # =========================
    st.subheader("Eligibility Snapshot")
    colA, colB, colC = st.columns(3)
    with colA:
        st.markdown("<div class='badge-note'>Tier</div>", unsafe_allow_html=True)
        badge(base_tier_ok, tier_label if tier_label != "Unclear" else "Tier unclear")
    with colB:
        st.markdown("<div class='badge-note'>Wagstaff</div>", unsafe_allow_html=True)
        badge(wag_ok, "Eligible" if wag_ok else "Not Eligible")
    with colC:
        st.markdown("<div class='badge-note'>Triten</div>", unsafe_allow_html=True)
        badge(triten_ok, "Eligible" if triten_ok else "Not Eligible")

    # =========================
    # Assign Law Firm
    # =========================
    st.subheader("Assign Law Firm")
    firm_options = ["Wagstaff Law Firm", "Triten Law Group", "Other (type name)"]
    if wag_ok:
        default_idx = 0
    elif triten_ok:
        default_idx = 1
    else:
        default_idx = 2
    assigned_firm_choice = st.selectbox("Choose firm for this PC", firm_options, index=default_idx, key="assigned_firm_choice")
    custom_firm_name = ""
    if assigned_firm_choice == "Other (type name)":
        custom_firm_name = st.text_input("Enter firm name", key="custom_firm_name").strip()

    def firm_header_and_short(choice, custom):
        if choice == "Wagstaff Law Firm":
            return "RIDESHARE Waggy | Retained:", "Waggy", "Wagstaff Law Firm"
        if choice == "Triten Law Group":
            return "RIDESHARE Triten | Retained:", "Triten", "Triten Law Group"
        name = custom or "Other Firm"
        return f"RIDESHARE {name} | Retained:", name, name

    note_header, firm_short, assigned_firm_name = firm_header_and_short(assigned_firm_choice, custom_firm_name)

    # =========================
    # Diagnostics
    # =========================
    st.subheader("Eligibility Diagnostics")

    # Wagstaff Diagnostic + Reasons Not Eligible
    st.markdown("#### Wagstaff")
    wag_lines = []
    wag_lines.append(f"• Tier = {tier_label}.")
    wag_lines.append(f"• Report OK? {'Yes' if wag_report_ok else 'No'} (allowed channels or audio/video evidence).")
    if set(report_dates.keys()) == {"Family/Friends"}:
        if family_report_dt:
            delta_hours = (family_report_dt - incident_dt).total_seconds() / 3600.0
            wag_lines.append(f"• Family-only report delta: {delta_hours:.1f} hours → {'OK (≤24h)' if (0 <= delta_hours <= 24.0) else 'Not OK (>24h)'}")
        else:
            wag_lines.append("• Family-only selected but time not provided.")
    wag_lines.append(f"• No attorney: {not has_atty}")
    wag_lines.append(f"• Inside/near scope: {inside_near}")
    wag_lines.append(f"• Felony: {'No' if not felony else 'Yes (DQ)'}")
    wag_lines.append(f"• Victim carried lethal weapon: {'Yes (DQ)' if client_weapon_lethal else 'No'}")
    wag_lines.append(f"• Company: {company}")
    if sol_years is None:
        wag_lines.append(f"• SOL: No SOL per SA extension ({sol_rule_text}) → timing OK.")
    else:
        if sol_time_ok:
            wag_lines.append(f"• SOL open until {fmt_dt(sol_end)} ({sol_rule_text}).")
        else:
            wag_lines.append(f"• SOL passed — {fmt_dt(sol_end)} ({sol_rule_text}).")
    st.markdown("<div class='kv'>" + "\n".join(wag_lines) + "</div>", unsafe_allow_html=True)

    wag_reasons = []
    if company not in ("Uber","Lyft"): wag_reasons.append("Company must be Uber or Lyft.")
    if not wag_report_ok: wag_reasons.append("Assault must be reported to a qualifying channel or have audio/video evidence.")
    if set(report_dates.keys()) == {"Family/Friends"} and not within_24h_family_ok:
        wag_reasons.append("Family/Friend-only report must be within 24 hours of the incident.")
    if not inside_near: wag_reasons.append("Incident must be inside/just outside/in furtherance from the car.")
    if not base_tier_ok: wag_reasons.append("Tier 1 or Tier 2 conduct must be present.")
    if not sol_time_ok: wag_reasons.append("Statute of limitations appears expired.")
    if has_atty: wag_reasons.append("Already represented by an attorney.")
    if felony: wag_reasons.append("Wagstaff currently does not accept felony history.")
    if client_weapon_lethal: wag_reasons.append("Wagstaff declines cases where the victim carried a lethal weapon.")
    st.markdown("**Reasons Not Eligible — Wagstaff**")
    st.markdown(f"<div class='kv'>{'• ' + '\\n• '.join(wag_reasons) if wag_reasons else '—'}</div>", unsafe_allow_html=True)

    # Triten Diagnostic + Reasons Not Eligible
    st.markdown("#### Triten")
    tri_lines = []
    tri_lines.append(f"• Tier = {tier_label}.")
    tri_lines.append(f"• Receipt (Email/PDF): {'Yes' if triten_receipt_ok else 'No'}")
    tri_lines.append(f"• Government ID: {'Yes' if triten_id_ok else 'No'}")
    tri_lines.append(f"• Female rider: {'Yes' if triten_gender_ok else 'No'}")
    tri_lines.append(f"• Rider (not driver): {'Yes' if triten_role_ok else 'No'}")
    if triten_report_any:
        if earliest_is_family:
            tri_lines.append(f"• Earliest report via Family/Friends; Δ days = {delta_days} → {'OK (≤14d)' if triten_family_14_ok else 'Not OK'}")
        else:
            tri_lines.append("• Report present via accepted channel.")
    else:
        tri_lines.append("• No report captured.")
    tri_lines.append(f"• No attorney: {'Yes' if triten_no_atty else 'No'}")
    tri_lines.append(f"• Scope inside/near: {'Yes' if triten_scope_ok else 'No'}")
    tri_lines.append(f"• SOL OK: {'Yes' if triten_sol_ok else 'No'}")
    tri_lines.append(f"• Company: {company}")
    st.markdown("<div class='kv'>" + "\n".join(tri_lines) + "</div>", unsafe_allow_html=True)

    triten_reasons = []
    if not triten_receipt_ok: triten_reasons.append("Must provide rideshare receipt (Email or PDF).")
    if not triten_id_ok: triten_reasons.append("Government ID is required.")
    if not triten_gender_ok: triten_reasons.append("Only rider claims from women are accepted.")
    if not triten_role_ok: triten_reasons.append("Claim must be as rider (not driver).")
    if not triten_report_any: triten_reasons.append("Incident must be reported (at least one channel).")
    if triten_report_any and earliest_is_family and not triten_family_14_ok:
        triten_reasons.append("Family/Friend report must be within 14 days.")
    if has_atty: triten_reasons.append("Cannot proceed if already represented by an attorney.")
    if not base_tier_ok or verbal_only or attempt_only: triten_reasons.append("Tier 1 or Tier 2 conduct must be present (declines verbal-only or attempt-only).")
    if not inside_near: triten_reasons.append("Incident must be inside/just outside/in furtherance from the car.")
    if not sol_time_ok: triten_reasons.append("Statute of limitations appears expired.")
    if company not in ("Uber","Lyft"): triten_reasons.append("Company must be Uber or Lyft.")
    st.markdown("**Reasons Not Eligible — Triten**")
    st.markdown(f"<div class='kv'>{'• ' + '\\n• '.join(triten_reasons) if triten_reasons else '—'}</div>", unsafe_allow_html=True)

    # =========================
    # Summary
    # =========================
    st.subheader("Summary")
    sol_end_str = ("No SOL" if sol_years is None else (fmt_dt(sol_end) if sol_end else "—"))
    file_by_str = ("N/A (No SOL)" if sol_years is None else (fmt_dt(file_by_deadline) if file_by_deadline else "—"))
    report_dates_str = "; ".join([f"{k}: {fmt_date(v)}" for k, v in report_dates.items()]) if report_dates else "—"
    family_dt_str = fmt_dt(family_report_dt) if family_report_dt else "—"

    decision = {
        "Assigned Firm": assigned_firm_name,
        "Full Name": caller_full_name,
        "Legal Name": caller_legal_name,
        "Consent Recording": consent_recording,
        "Phone": caller_phone,
        "Email": caller_email,
        "Company": company,
        "State": state,
        "Tier": tier_label,
        "SA category for SOL": category or "—",
        "Using SA extension?": "Yes" if (category and sol_state in SA_EXT) else "No (general tort)",
        "SOL rule applied": sol_rule_text,
        "SOL End (est.)": sol_end_str,
        "File-by (SOL-45d)": file_by_str,
        "Reported Dates": report_dates_str,
        "Family/Friends Report (DateTime)": family_dt_str,
        "Wagstaff Eligible?": "Eligible" if wag_ok else "Not Eligible",
        "Triten Eligible?": "Eligible" if triten_ok else "Not Eligible",
    }
    st.dataframe(pd.DataFrame([decision]), use_container_width=True, height=360)

    # =========================
    # Detailed Report — Statement of the Case
    # =========================
    st.subheader("Detailed Report — Elements of Statement of the Case for RIDESHARE")

    acts_selected = [k for k, v in act_flags.items() if v and k not in ("Kidnapping Off-Route w/ Threats", "False Imprisonment w/ Threats")]
    aggr_selected = [k for k in ("Kidnapping Off-Route w/ Threats","False Imprisonment w/ Threats") if act_flags.get(k)]

    line_items = []
    def add_line(num, text): line_items.append(f"{num}. {text}")

    add_line(1,  f"Caller Full / Legal: {caller_full_name or '—'} / {caller_legal_name or '—'}")
    add_line(2,  f"Assigned Firm: {assigned_firm_name}")
    add_line(3,  f"Platform: {company}")
    add_line(4,  f"Receipt Evidence: {join_list(receipt_evidence)} | Files: {', '.join(uploaded_names) if uploaded_names else '—'}")
    add_line(5,  f"Incident Date/Time: {(fmt_date(incident_date) if incident_date else 'UNKNOWN')} {incident_time.strftime('%H:%M') if incident_time else ''}")
    add_line(6,  f"Reported to: {join_list(list(reported_to))} | Dates: {', '.join([f'{k}: {fmt_date(v)}' for k,v in report_dates.items()]) if report_dates else '—'}")
    if "Friend or Family Member" in reported_to:
        add_line(6.1, f"Family/Friend Contact: {(fam_first or '—')} {(fam_last or '')} | Phone: {fam_phone or '—'}")
    if "Physician" in reported_to:
        add_line(6.2, f"Physician: {phys_name or '—'} | Clinic/Hospital: {phys_fac or '—'} | Address: {phys_addr or '—'}")
    if "Therapist" in reported_to:
        add_line(6.3, f"Therapist: {ther_name or '—'} | Clinic/Hospital: {ther_fac or '—'} | Address: {ther_addr or '—'}")
    if "Police Department" in reported_to:
        add_line(6.4, f"Police Station: {police_station or '—'} | Address: {police_addr or '—'}")
    if "Rideshare Company" in reported_to:
        add_line(6.5, f"Rideshare Company (reported): {rep_rs_company or '—'}")
    add_line(7,  f"Where it happened (scope): {scope_choice}")
    add_line(8,  f"Pickup → Drop-off: {pickup or '—'} → {dropoff or '—'} | State: {state}")
    add_line(9,  f"Injuries — Physical: {'Yes' if injury_physical else 'No'}, Emotional: {'Yes' if injury_emotional else 'No'} | Details: {injuries_summary or '—'}")
    add_line(10, f"Provider: {provider_name or '—'} | Facility: {provider_facility or '—'} | First visit: {fmt_date(first_visit) if first_visit else '—'} | Last visit: {fmt_date(last_visit) if last_visit else '—'} | Therapy start: {fmt_date(therapy_start) if therapy_start else '—'}")
    add_line(11, f"Medication: {medication_name or '—'} | Pharmacy: {pharmacy_name or '—'}")
    add_line(12, f"Submission: {rs_submit_how or '—'} | Company responded: {'Yes' if rs_received_response else 'No'} | Detail: {rs_response_detail or '—'}")
    add_line(13, f"Phone / Email: {caller_phone or '—'} / {caller_email or '—'}")
    add_line(14, f"Screen — Gov ID: {'Yes' if gov_id else 'No'} | Female: {'Yes' if female_rider else 'No'} | Rider (not driver): {'Yes' if rider_not_driver else 'No'} | Felony: {'Yes' if felony else 'No'} | Has Atty: {'Yes' if has_atty else 'No'} | SSN captured: {'Yes' if full_ssn_on_file or ssn_last4 else 'No'}")
    add_line(15, f"Victim carried weapon (Wagstaff only): {'Yes' if client_weapon else 'No'} | Non-lethal items: {join_list(nonlethal_selected)} | Lethal carried: {'Yes' if client_weapon_lethal else 'No'}")
    add_line(16, f"Driver weapon/force used/threatened: {driver_used_weapon} | Detail: {driver_force_detail or '—'}")
    add_line(17, f"Acts selected: {join_list(acts_selected)} | Aggravators: {join_list(aggr_selected)} | Verbal-only: {'Yes' if verbal_only else 'No'} | Attempt-only: {'Yes' if attempt_only else 'No'}")
    add_line(18, f"Tier: {tier_label}")
    add_line(19, f"SOL rule applied: {sol_rule_text} | SOL end: {('No SOL' if sol_years is None else fmt_dt(sol_end))} | File-by (SOL−45d): {file_by_str}")
    if earliest_report_date is not None:
        add_line(20, f"Earliest report: {fmt_date(earliest_report_date)} via {', '.join(earliest_channels) if earliest_channels else '—'} (Δ = {delta_days} day[s])")
    else:
        add_line(20, "Earliest report: —")
    add_line(21, f"Wagstaff Eligibility: {'Eligible' if wag_ok else 'Not Eligible'}")
    add_line(22, f"Triten Eligibility: {'Eligible' if triten_ok else 'Not Eligible'}")
    add_line(23, f"Prior Firm Signed/Disqualified: {'Yes' if prior_firm_any else 'No'}{(' — ' + prior_firm_note) if (prior_firm_any and prior_firm_note) else ''}")

    elements = "\n".join([str(x) for x in line_items])
    st.markdown(f"<div class='copy'>{elements}</div>", unsafe_allow_html=True)

    # =========================
    # Law Firm Note (Copy & Send)
    # =========================
    st.subheader("Law Firm Note (Copy & Send)")

    # Source dropdown (reflect in note)
    source_options = [
        "Client Referral","DMEI","DMEI Rideshare","Facebook","FB Rideshare","FB Rideshare Assault",
        "FB RS Lawsuit","Main Office Line","Web Form Submission","Website Phone Call"
    ]
    marketing_source = st.selectbox("Marketing Source", options=source_options, index=0, key="marketing_source")

    # PLAID / ID specifics
    note_gdrive = st.text_input("GDrive URL", value="", key="note_gdrive")
    note_plaid_passed = st.checkbox("PLAID Passed", value=False, key="note_plaid_passed")

    id_types = ["Driver's License","State ID","Passport","Tribal ID","Military ID","Consular ID","Other"]
    note_id_type = st.selectbox("ID Provided (PLAID)", id_types, index=0, key="note_id_type")
    note_id_other = ""
    if note_id_type == "Other":
        note_id_other = st.text_input("If Other, specify ID type", key="note_id_other")

    # Receipt reflection per platform
    ev_flags = {
        "PDF": ("PDF" in receipt_evidence) or any_pdf_uploaded,
        "Screenshot": ("Screenshot of Receipt" in receipt_evidence),
        "Email": ("Email" in receipt_evidence),
        "In-App": ("In-App Receipt (screenshot)" in receipt_evidence),
    }
    ev_parts = []
    if ev_flags["PDF"]: ev_parts.append("PDF receipt")
    if ev_flags["Screenshot"]: ev_parts.append("Screenshot")
    if ev_flags["Email"]: ev_parts.append("Email")
    if ev_flags["In-App"]: ev_parts.append("In-App")
    receipts_line = ""
    if company in ("Uber","Lyft") and ev_parts:
        receipts_line = f"{company} — " + "; ".join(ev_parts)

    note_extra = st.text_area("Additional note (optional)", value="", key="note_extra")

    # Auto-append Reporting details into note
    reporting_lines = []
    if report_dates:
        reporting_lines.append("Reporting Details:")
        if "Rideshare company" in report_dates:
            reporting_lines.append(f"• Rideshare company: {rep_rs_company or '—'} on {fmt_date(report_dates['Rideshare company'])}")
        if "Police" in report_dates:
            reporting_lines.append(f"• Police: {police_station or '—'} ({police_addr or '—'}) on {fmt_date(report_dates['Police'])}")
        if "Therapist" in report_dates:
            reporting_lines.append(f"• Therapist: {ther_name or '—'} at {ther_fac or '—'} ({ther_addr or '—'}) on {fmt_date(report_dates['Therapist'])}")
        if "Physician" in report_dates:
            reporting_lines.append(f"• Physician: {phys_name or '—'} at {phys_fac or '—'} ({phys_addr or '—'}) on {fmt_date(report_dates['Physician'])}")
        if "Family/Friends" in report_dates:
            fam_dt_str = fmt_dt(family_report_dt) if family_report_dt else fmt_date(report_dates["Family/Friends"])
            reporting_lines.append(f"• Family/Friends: {fam_first or '—'} {fam_last or ''} (☎ {fam_phone or '—'}) at {fam_dt_str}")
    reporting_block = "\n".join(reporting_lines)

    # Tier summary for note
    tier_case_str = "Unclear"
    if tier_label.startswith("Tier 1"):
        tier_case_str = "1 Case"
    elif tier_label.startswith("Tier 2"):
        tier_case_str = "2 Case"

    created_str = TODAY.strftime("%B %d, %Y")
    company_upper = (company or "").upper()
    full_legal_for_note = caller_legal_name or caller_full_name or ""

    # Build note in required order
    note_lines = [
        f"{note_header}",
        f"Client: {full_legal_for_note}".strip(),
        f"Rideshare: {company_upper}",
        f"Tier: {tier_case_str}",
        f"Source: {marketing_source}",
        f"Date Created: {created_str}",
        f"Full SSN: {'Yes' if full_ssn_on_file else 'No'}",
    ]
    if receipts_line:
        note_lines.append(f"Receipts: {receipts_line}")
    if note_id_type:
        note_lines.append(f"ID Provided: {note_id_other if note_id_type=='Other' else note_id_type}")
    if note_plaid_passed:
        note_lines.append("PLAID: Passed")
    if note_gdrive:
        note_lines.append(f"Gdrive: {note_gdrive}")
    if reporting_block:
        note_lines.append(reporting_block)
    if prior_firm_any:
        note_lines.append(f"Prior firm signed/disqualified: YES{(' — ' + prior_firm_note) if prior_firm_note else ''}")
    if note_extra:
        note_lines.append(f"Note: {note_extra}")

    lawfirm_note = "\n".join(note_lines)
    st.markdown(f"<div class='copy'>{lawfirm_note}</div>", unsafe_allow_html=True)

    st.download_button(
        "Download Law Firm Note (.txt)",
        data=lawfirm_note.encode("utf-8"),
        file_name="lawfirm_note.txt",
        mime="text/plain"
    )

    # Notepad-friendly Detailed Report
    detailed_report_txt = "Detailed Report — Elements of Statement of the Case for RIDESHARE\n\n" + elements
    st.download_button(
        "Download Detailed Report (.txt)",
        data=detailed_report_txt.encode("utf-8"),
        file_name="statement_of_case.txt",
        mime="text/plain"
    )

    # =========================
    # Objection Scripts / Legend / References
    # =========================
    st.markdown("---")
    st.header("Objection Script / Legend / References")
    obj_key = st.selectbox(
        "Select a script or reference",
        sorted(list(OBJECTION_SCRIPTS.keys())),
        index=0,
        key="obj_script_select"
    )
    obj_text = OBJECTION_SCRIPTS.get(obj_key, "")
    if obj_text.startswith("http"):
        st.markdown(f"[Open reference link]({obj_text})")
    else:
        script_block(obj_text)

    # =========================
    # Firm-Specific Client Contact Details (Bottom)
    # =========================
    st.markdown("---")
    st.header("Firm-Specific Client Contact Details")

    pre_first, pre_mid, pre_last = split_legal_name(caller_legal_name)
    pre_email = caller_email or ""
    pre_home = ""
    pre_cell = st.session_state.get("caller_phone", "") or ""
    pre_city = ""
    pre_state_idx = STATE_LIST_FORM.index(state) if state in STATE_LIST_FORM else 0
    pre_zip = ""

    client_contact_text = []

    if assigned_firm_name == "Triten Law Group":
        st.subheader("TriTen – Intake CLIENT CONTACT DETAILS")

        tri_first = st.text_input("First Name", value=pre_first, key="tri_first")
        tri_middle = st.text_input("Middle Name", value=pre_mid, key="tri_middle")
        tri_last = st.text_input("Last Name", value=pre_last, key="tri_last")

        tri_maiden = st.text_input("Maiden Name (if applicable)", key="tri_maiden")
        tri_pref_name = st.text_input("Preferred Name", key="tri_pref_name")
        tri_email = st.text_input("Primary Email", value=pre_email, key="tri_email")

        tri_addr = st.text_input("Mailing Address", key="tri_addr")
        tri_city = st.text_input("City", value=pre_city, key="tri_city")
        tri_state = st.selectbox("State", STATE_LIST_FORM, index=pre_state_idx, key="tri_state")
        tri_zip = st.text_input("Zip", value=pre_zip, key="tri_zip")

        tri_home_phone = st.text_input("Home Phone No.", value=pre_home, key="tri_home_phone")
        tri_cell_phone = st.text_input("Cell Phone No.", value=pre_cell, key="tri_cell_phone")
        tri_best_time = st.text_input("Best Time to Contact", key="tri_best_time")
        tri_pref_method = st.selectbox("Preferred Method of Contact", ["Phone", "Email", "Phone & Email"], index=2, key="tri_pref_method")

        tri_dob = st.date_input("Date of Birth (mm-dd-yyyy)", value=None, key="tri_dob",
                                min_value=date(1969,1,1), max_value=date.today())
        tri_age = calc_age(tri_dob) if tri_dob else ""
        st.caption(f"Age: {tri_age if tri_age!='' else '—'}")

        # Reflect full SSN captured above into TriTen field
        tri_ssn = st.text_input("Social Security No.", value=(full_ssn if full_ssn else ""), key="tri_ssn")

        tri_claim_for = st.radio("Does the claim pertain to you or another person?", ["Myself","Someone else"], horizontal=True, key="tri_claim_for")
        tri_marital = st.selectbox("Current marital status", ["Single","Married","Divorced","Widowed"], key="tri_marital")

        # Affirmation
        st.markdown("---")
        st.markdown("**Affirmation**")
        tri_affirmation = st.radio(
            "[Having just confirmed all the answers you have provided in response to all the questions] "
            "Do you hereby affirm that the information submitted by you is true and correct in all respects, "
            "including whether you've ever signed up with another law firm?",
            ["Yes", "No"], horizontal=True, key="tri_affirmation"
        )
        st.markdown("**INTAKE ENDS HERE**")

        client_contact_text = [
            "CLIENT CONTACT DETAILS — TriTen",
            f"Name: {tri_first} {tri_middle} {tri_last}".strip(),
            f"Maiden: {tri_maiden}",
            f"Preferred: {tri_pref_name}",
            f"Email: {tri_email}",
            f"Address: {tri_addr}, {tri_city}, {tri_state} {tri_zip}",
            f"Home: {tri_home_phone} | Cell: {tri_cell_phone}",
            f"Best Time: {tri_best_time} | Pref Method: {tri_pref_method}",
            f"DOB: {fmt_date(tri_dob) if tri_dob else '—'} (Age: {tri_age if tri_age!='' else '—'})",
            f"SSN: {tri_ssn}",
            f"Claim For: {tri_claim_for} | Marital: {tri_marital}",
            f"Affirmation: {tri_affirmation}",
        ]

    elif assigned_firm_name == "Wagstaff Law Firm":
        st.subheader("Wagstaff – CLIENT CONTACT DETAILS")

        wag_first = st.text_input("First Name", value=pre_first, key="wag_first")
        wag_middle = st.text_input("Middle Name", value=pre_mid, key="wag_middle")
        wag_last = st.text_input("Last Name", value=pre_last, key="wag_last")

        wag_email = st.text_input("Primary Email", value=pre_email, key="wag_email")
        wag_addr = st.text_input("Mailing Address", key="wag_addr")
        wag_city = st.text_input("City", value=pre_city, key="wag_city")
        wag_state = st.selectbox("State", STATE_LIST_FORM, index=pre_state_idx, key="wag_state")
        wag_zip = st.text_input("Zip", value=pre_zip, key="wag_zip")
        wag_home_phone = st.text_input("Home Phone No.", value=pre_home, key="wag_home_phone")
        wag_cell_phone = st.text_input("Cell Phone No.", value=pre_cell, key="wag_cell_phone")
        wag_best_time = st.text_input("Best Time to Contact", value="", key="wag_best_time")
        wag_pref_method = st.selectbox("Preferred Method of Contact", ["Phone", "Email", "Phone & Email"], index=2, key="wag_pref_method")

        wag_dob = st.date_input("Date of Birth (mm-dd-yyyy)", value=None, key="wag_dob",
                                min_value=date(1969,1,1), max_value=date.today())
        wag_age = calc_age(wag_dob) if wag_dob else ""
        st.caption(f"Age: {wag_age if wag_age!='' else '—'}")

        # Reflect full SSN captured above into Wagstaff field
        wag_ssn = st.text_input("Social Security No.", value=(full_ssn if full_ssn else ""), key="wag_ssn")

        wag_claim_for = st.radio("Does the claim pertain to you or another person?", ["Myself","Someone Else"], horizontal=True, key="wag_claim_for")

        st.caption(f"Prior firm signed/disqualified earlier: {'Yes' if prior_firm_any else 'No'}"
                   f"{(' — ' + prior_firm_note) if (prior_firm_any and prior_firm_note) else ''}")

        st.subheader("INJURED PARTY DETAILS")
        inj_full = st.text_input("Injured/Deceased Party's Full Name (First, Middle, & Last Name)",
                                 value=f"{wag_first} {wag_middle} {wag_last}".strip(), key="wag_inj_full")
        inj_gender_default = "Female" if female_rider else "—"
        inj_gender = st.text_input("Injured Party Gender", value=inj_gender_default, key="wag_inj_gender")
        inj_dob = st.date_input("Injured/Deceased Party's DOB (mm-dd-yyyy)", value=None, key="wag_inj_dob",
                                min_value=date(1969,1,1), max_value=date.today())

        client_contact_text = [
            "CLIENT CONTACT DETAILS — Wagstaff",
            f"Name: {wag_first} {wag_middle} {wag_last}".strip(),
            f"Email: {wag_email}",
            f"Address: {wag_addr}, {wag_city}, {wag_state} {wag_zip}",
            f"Home: {wag_home_phone} | Cell: {wag_cell_phone}",
            f"Best Time: {wag_best_time} | Pref Method: {wag_pref_method}",
            f"DOB: {fmt_date(wag_dob) if wag_dob else '—'} (Age: {wag_age if wag_age!='' else '—'})",
            f"SSN: {wag_ssn}",
            f"Claim For: {wag_claim_for}",
            f"Injured Party: {inj_full} | Gender: {inj_gender} | DOB: {fmt_date(inj_dob) if inj_dob else '—'}",
            f"Prior Firm Signed/Disqualified: {'Yes' if prior_firm_any else 'No'}{(' — ' + prior_firm_note) if (prior_firm_any and prior_firm_note) else ''}",
        ]

    else:
        st.info("Select a firm above to reveal the tailored contact section.")

    # =========================
    # EXPORTS (TXT/CSV/XLSX)
    # =========================
    st.subheader("Export")

    earliest_channels_str = ", ".join(earliest_channels) if earliest_channels else ""

    export_payload = {
        # Assignment
        "AssignedFirm": assigned_firm_name,
        "AssignedFirmShort": firm_short,
        "LawFirmNoteHeader": note_header,
        # Caller
        "FullName": caller_full_name,
        "LegalName": caller_legal_name,
        "ConsentRecording": consent_recording,
        "Phone": caller_phone,
        "Email": caller_email,
        # Prior firm info
        "PriorFirmSigned": prior_firm_any,
        "PriorFirmNote": prior_firm_note,
        # Ride
        "Company": company, "Pickup": pickup, "Dropoff": dropoff, "State": state,
        "IncidentDate": fmt_date(incident_date) if incident_date else "UNKNOWN",
        "IncidentTime": incident_time.strftime("%H:%M"),
        # Evidence
        "ReceiptEvidence": ", ".join(receipt_evidence) if receipt_evidence else "",
        "UploadedFiles": ", ".join(uploaded_names) if uploaded_names else "",
        "AnyPDFUploaded": any_pdf_uploaded,
        "AnyAudioVideoUploaded": any_av_uploaded,
        # Reporting
        "ReportedTo": ", ".join(reported_to) if reported_to else "",
        "ReportDates": "; ".join([f"{k}: {fmt_date(v)}" for k, v in report_dates.items()]) if report_dates else "",
        "FamilyReportDateTime": (fmt_dt(family_report_dt) if family_report_dt else "—"),
        "FamilyFirstName": fam_first, "FamilyLastName": fam_last, "FamilyPhone": fam_phone,
        "PhysicianName": phys_name, "PhysicianClinicHospital": phys_fac, "PhysicianAddress": phys_addr,
        "TherapistName": ther_name, "TherapistClinicHospital": ther_fac, "TherapistAddress": ther_addr,
        "PoliceStation": police_station, "PoliceAddress": police_addr,
        "ReportedRideshareCompany": rep_rs_company,
        # Submission/response
        "SubmittedHow": rs_submit_how, "CompanyResponded": rs_received_response, "CompanyResponseDetail": rs_response_detail,
        # Health
        "InjuryPhysical": injury_physical, "InjuryEmotional": injury_emotional, "InjuriesSummary": injuries_summary,
        "ProviderName": provider_name, "ProviderFacility": provider_facility,
        "FirstVisit": fmt_date(first_visit) if first_visit else "—",
        "LastVisit": fmt_date(last_visit) if last_visit else "—",
        "TherapyStartDate": fmt_date(therapy_start) if therapy_start else "—",
        "Medication": medication_name, "Pharmacy": pharmacy_name,
        # Identity
        "FullSSN": full_ssn, "SSN_Last4": ssn_last4, "FullSSN_OnFile": full_ssn_on_file,
        # Screening
        "GovIDProvided": gov_id, "FemaleRider": female_rider, "RiderNotDriver": rider_not_driver, "HasAttorney": has_atty, "Felony": felony,
        "ClientWeapon": client_weapon, "ClientWeaponNonLethal": ", ".join(nonlethal_selected) if nonlethal_selected else "",
        "ClientWeaponLethal": client_weapon_lethal, "DriverUsedWeaponOrForce": driver_used_weapon, "DriverForceDetail": driver_force_detail,
        "VerbalOnly": verbal_only, "AttemptOnly": attempt_only,
        # Acts
        "Acts_RapePenetration": rape, "Acts_ForcedOralForcedTouch": forced_oral, "Acts_TouchingKissing": touching,
        "Acts_Exposure": exposure, "Acts_Masturbation": masturb, "Agg_Kidnap": kidnap, "Agg_Imprison": imprison,
        "Acts_Selected": ", ".join(acts_selected) if acts_selected else "", "Aggravators_Selected": ", ".join(aggr_selected) if aggr_selected else "",
        # SOL
        "SA_Category": category or "—", "SA_Extension_Used": (STATE_ALIAS.get(state, state) in SA_EXT) and bool(category),
        "SOL_Rule_Text": sol_rule_text, "SOL_Years": ("No SOL" if sol_years is None else sol_years),
        "SOL_End": ("No SOL" if sol_years is None else fmt_dt(sol_end)), "FileBy": ("N/A (No SOL)" if sol_years is None else fmt_dt(file_by_deadline)),
        "Earliest_Report_Date": (fmt_date(earliest_report_date) if earliest_report_date else "—"),
        "Earliest_Report_Channels": earliest_channels_str, "Earliest_Is_Family": earliest_is_family,
        "Earliest_Report_DeltaDays": (None if earliest_report_date is None else int(delta_days if delta_days is not None else -9999)),
        # Eligibility
        "Eligibility_Wagstaff": "Eligible" if wag_ok else "Not Eligible",
        "Eligibility_Triten": "Eligible" if triten_ok else "Not Eligible",
        "Wag_NotEligible_Reasons": "; ".join(wag_reasons) if wag_reasons else "",
        "Triten_NotEligible_Reasons": "; ".join(triten_reasons) if triten_reasons else "",
        # Notes & Marketing (incl ID/PLAID, receipts)
        "MarketingSource": marketing_source,
        "LawFirmNote": lawfirm_note,
        "ID_Type_PLAID": (note_id_other if note_id_type=='Other' else note_id_type),
        "PLAID_Passed": note_plaid_passed,
        "Receipts_Note": receipts_line,
        "GDriveURL": note_gdrive,
        # Statement-of-case text
        "Elements_Report": elements.strip()
    }

    # Add firm-specific contact fields to export
    if assigned_firm_name == "Triten Law Group":
        export_payload.update({
            "TriTen_FirstName": st.session_state.get("tri_first",""),
            "TriTen_MiddleName": st.session_state.get("tri_middle",""),
            "TriTen_LastName": st.session_state.get("tri_last",""),
            "TriTen_MaidenName": st.session_state.get("tri_maiden",""),
            "TriTen_PreferredName": st.session_state.get("tri_pref_name",""),
            "TriTen_Email": st.session_state.get("tri_email",""),
            "TriTen_Address": st.session_state.get("tri_addr",""),
            "TriTen_City": st.session_state.get("tri_city",""),
            "TriTen_State": st.session_state.get("tri_state",""),
            "TriTen_Zip": st.session_state.get("tri_zip",""),
            "TriTen_HomePhone": st.session_state.get("tri_home_phone",""),
            "TriTen_CellPhone": st.session_state.get("tri_cell_phone",""),
            "TriTen_BestTime": st.session_state.get("tri_best_time",""),
            "TriTen_PrefMethod": st.session_state.get("tri_pref_method",""),
            "TriTen_DOB": fmt_date(st.session_state.get("tri_dob")) if st.session_state.get("tri_dob") else "",
            "TriTen_Age": calc_age(st.session_state.get("tri_dob")) if st.session_state.get("tri_dob") else "",
            "TriTen_SSN": st.session_state.get("tri_ssn", full_ssn),
            "TriTen_ClaimFor": st.session_state.get("tri_claim_for",""),
            "TriTen_Marital": st.session_state.get("tri_marital",""),
            "TriTen_Affirmed": st.session_state.get("tri_affirmation",""),
        })
    elif assigned_firm_name == "Wagstaff Law Firm":
        export_payload.update({
            "Wag_FirstName": st.session_state.get("wag_first",""),
            "Wag_MiddleName": st.session_state.get("wag_middle",""),
            "Wag_LastName": st.session_state.get("wag_last",""),
            "Wag_Email": st.session_state.get("wag_email",""),
            "Wag_Address": st.session_state.get("wag_addr",""),
            "Wag_City": st.session_state.get("wag_city",""),
            "Wag_State": st.session_state.get("wag_state",""),
            "Wag_Zip": st.session_state.get("wag_zip",""),
            "Wag_HomePhone": st.session_state.get("wag_home_phone",""),
            "Wag_CellPhone": st.session_state.get("wag_cell_phone",""),
            "Wag_BestTime": st.session_state.get("wag_best_time",""),
            "Wag_PrefMethod": st.session_state.get("wag_pref_method",""),
            "Wag_DOB": fmt_date(st.session_state.get("wag_dob")) if st.session_state.get("wag_dob") else "",
            "Wag_Age": calc_age(st.session_state.get("wag_dob")) if st.session_state.get("wag_dob") else "",
            "Wag_SSN": st.session_state.get("wag_ssn", full_ssn),
            "Wag_ClaimFor": st.session_state.get("wag_claim_for",""),
            "Wag_PriorFirmSigned": prior_firm_any,
            "Wag_PriorFirmNote": prior_firm_note,
            "Wag_InjuredFullName": st.session_state.get("wag_inj_full",""),
            "Wag_InjuredGender": st.session_state.get("wag_inj_gender",""),
            "Wag_InjuredDOB": fmt_date(st.session_state.get("wag_inj_dob")) if st.session_state.get("wag_inj_dob") else "",
        })

    df_export = pd.DataFrame([export_payload])

    # Formatted Excel (center + wrap) if engine present
    xlsx_data = None
    xlsx_msg = ""
    if XLSX_ENGINE:
        try:
            xlsx_buf = BytesIO()
            with pd.ExcelWriter(xlsx_buf, engine=XLSX_ENGINE) as writer:
                df_export.to_excel(writer, index=False, sheet_name="Intake")
                if XLSX_ENGINE == "xlsxwriter":
                    workbook  = writer.book
                    worksheet = writer.sheets["Intake"]
                    fmt = workbook.add_format({"align": "center", "valign": "top", "text_wrap": True})
                    for col_idx in range(len(df_export.columns)):
                        worksheet.set_column(col_idx, col_idx, 28, fmt)
                    worksheet.freeze_panes(1, 0)
                elif XLSX_ENGINE == "openpyxl":
                    ws = writer.sheets["Intake"]
                    from openpyxl.styles import Alignment
                    alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)
                    for col_cells in ws.columns:
                        for cell in col_cells:
                            cell.alignment = alignment
                    for col in ws.columns:
                        col_letter = col[0].column_letter
                        ws.column_dimensions[col_letter].width = 28
                    ws.freeze_panes = "A2"
            xlsx_data = xlsx_buf.getvalue()
        except Exception as e:
            xlsx_msg = f"Excel export temporarily unavailable ({type(e).__name__}). Use TXT or CSV."
    else:
        xlsx_msg = "Excel engine not installed. Add 'xlsxwriter' or 'openpyxl' to requirements.txt to enable formatted Excel."

    if xlsx_data:
        st.download_button(
            "Download Excel (formatted .xlsx)",
            data=xlsx_data,
            file_name="intake_decision.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info(xlsx_msg)

    st.download_button(
        "Download CSV (legacy)",
        data=df_export.to_csv(index=False).encode("utf-8"),
        file_name="intake_decision.csv",
        mime="text/csv"
    )

    # NEW: Client Contact Details (.txt)
    if client_contact_text:
        client_contact_blob = "\n".join(client_contact_text)
        st.download_button(
            "Download Client Contact Details (.txt)",
            data=client_contact_blob.encode("utf-8"),
            file_name="client_contact_details.txt",
            mime="text/plain"
        )

render()



