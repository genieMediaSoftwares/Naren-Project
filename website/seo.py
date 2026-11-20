"""Search presentation and navigation for existing pages; no clinical claims."""

ORIGIN = "https://www.narenultrasound.in"
CLINIC_ID = ORIGIN + "/#clinic"

# Public URL improvement for the truncated TIFFA slug reported by Ubersuggest.
# Database slugs stay intact; reverse() and the converter share this mapping.
ARTICLE_PUBLIC_SLUGS = {
    "your-babys-first-detailed-health-check-understandi": "tiffa-scan-guide",
}

# Exact category labels already displayed on the existing services page.
SERVICE_ENTITIES = (
    ("antenatal-gynecological-scans", "Antenatal & Gynecological Scans"),
    ("routine-scans", "Routine Scans"),
    ("paediatric-scans", "Paediatric Scans"),
    ("doppler-scans", "Doppler Scans"),
    ("usg-guided-procedures", "USG Guided Procedures"),
    ("usg-small-parts", "USG Small Parts"),
)

PAGE_METADATA = {
    "home": ("Ultrasound Scan in Visakhapatnam | Naren Ultrasound", "Explore ultrasound and fetal medicine services at Naren Ultrasound in Maharanipeta, Visakhapatnam. View scan services, clinic details and appointments."),
    "about": ("About Naren Ultrasound | Visakhapatnam", "Learn about Naren Ultrasound & Fetal Medicine Center in Maharanipeta, Visakhapatnam, its ultrasound services and patient-focused approach."),
    "services": ("Ultrasound Scan Services in Visakhapatnam | Naren Ultrasound", "Explore pregnancy, NT, TIFFA, abdominal, paediatric and Doppler ultrasound services at Naren Ultrasound in Visakhapatnam. Enquire about appointments."),
    "doctors": ("Dr. Naren Satya | Naren Ultrasound Visakhapatnam", "Read the profile of Dr. Naren Satya at Naren Ultrasound & Fetal Medicine Center in Visakhapatnam and explore the clinic's ultrasound services."),
    "gallery": ("Ultrasound Services Gallery | Naren Ultrasound Vizag", "Browse ultrasound service images from Naren Ultrasound in Visakhapatnam. Explore antenatal, routine, paediatric and Doppler services and appointment options."),
    "patient_info": ("Ultrasound Appointments in Visakhapatnam | Naren Ultrasound", "Find clinic hours, patient information and ultrasound appointment options at Naren Ultrasound in Maharanipeta, Visakhapatnam."),
    "contact": ("Contact & Directions | Naren Ultrasound Visakhapatnam", "Find the address, phone numbers, clinic hours and directions for Naren Ultrasound in Maharanipeta, Visakhapatnam. Contact the clinic for scan enquiries."),
    "blog_list": ("Pregnancy Ultrasound Guides | Naren Ultrasound", "Browse articles on TIFFA, NT, dating, viability, growth and fetal echo scans, including twin pregnancy topics, from Naren Ultrasound in Visakhapatnam."),
}

# Exact existing slugs: metadata only; the stored title and article stay intact.
ARTICLE_TOPICS = {
    "what-is-a-fetal-anomaly-scan": ("Fetal Anomaly Scan: Purpose & What to Expect", "fetal anomaly scans, their purpose and what to expect at an appointment"),
    "your-babys-first-detailed-health-check-understandi": ("TIFFA Scan: Meaning & What to Expect", "TIFFA scan terminology and what an ultrasound appointment involves"),
    "twin-tiffa-scan-a-complete-guide-for-parents": ("Twin TIFFA Scan: A Guide for Parents", "TIFFA scans in twin pregnancies and questions to discuss with your doctor"),
    "what-is-amniotic-fluid-how-doctors-check-it": ("Amniotic Fluid: Meaning & Assessment", "amniotic fluid and its assessment during pregnancy"),
    "nuchal-translucency-scan-a-complete-guide": ("NT Scan in Pregnancy: A Patient Guide", "nuchal translucency (NT) scans and questions to discuss at your pregnancy appointment"),
    "twin-nuchal-translucency-scan-a-complete-guide-of": ("Twin NT Scan: A Guide for Parents", "nuchal translucency (NT) scans in twin pregnancies"),
    "what-is-a-fetal-echo-scan-every-parent-should-know": ("Fetal Echo in Pregnancy: What to Expect", "fetal echocardiography in pregnancy and what to discuss with your doctor"),
    "twins-fetal-echo-a-complete-guide-for-parents": ("Fetal Echo for Twins: A Patient Guide", "fetal echocardiography in twin pregnancies and appointment questions"),
    "the-dating-scan-detailed-explanation-of-the-dating": ("Dating Scan: A Guide for Expectant Parents", "pregnancy dating scans and questions about gestational age and due dates"),
    "twin-dating-scan-detailed-explanation-of-twin-dati": ("Twin Dating Scan: A Guide for Parents", "dating scans for twin pregnancies and questions for your appointment"),
    "early-tiffa-scan-baby-early-development": ("Early TIFFA Scan: A Patient Guide", "early TIFFA scans and questions to discuss with your pregnancy care team"),
    "twin-early-tiffa-scan-what-you-need-to-know-as-a-p": ("Twin Early TIFFA Scan: A Patient Guide", "early TIFFA scans in twin pregnancies and appointment questions"),
    "early-pregnancy-viability-scan-the-complete-guide": ("Early Pregnancy Viability Scan Guide", "early pregnancy viability scans and what to discuss with your doctor"),
    "twin-viability-scan-what-it-checks-and-why-it-matt": ("Twin Viability Scan: A Guide for Parents", "viability scans in twin pregnancies and questions for your doctor"),
    "late-tiffa-anomaly-scan-what-it-checks-and-why-it": ("Late TIFFA / Anomaly Scan: A Patient Guide", "later TIFFA or anomaly assessments and questions to discuss with your doctor"),
    "twin-late-tiffa-anomaly-scan-what-you-need-to-know": ("Twin Late TIFFA Scan: A Patient Guide", "later TIFFA or anomaly assessments in twin pregnancies"),
    "routine-growth-scan-what-it-checks-and-why-it-matt": ("Growth Scan in Pregnancy: A Patient Guide", "pregnancy growth scans and questions about ultrasound and Doppler assessment"),
    "twin-routine-growth-scan-what-it-checks-and-why-it": ("Twin Growth Scan: A Guide for Parents", "growth scans in twin pregnancies and questions to discuss with your doctor"),
}

# Full descriptions have a single, explicit presentation source. These do not
# overwrite the CMS article, its stored title, authorship or review history.
ARTICLE_DESCRIPTIONS = {
    "what-is-a-fetal-anomaly-scan": "Read an introduction to fetal anomaly scans and prepare questions about the assessment, appointment and discussion of findings.",
    "your-babys-first-detailed-health-check-understandi": "Explore TIFFA scan terminology and prepare questions for your pregnancy care team about the ultrasound appointment and findings.",
    "twin-tiffa-scan-a-complete-guide-for-parents": "Explore TIFFA scan terminology for twin pregnancies and prepare questions for your clinician before a fetal ultrasound appointment.",
    "what-is-amniotic-fluid-how-doctors-check-it": "Read an introduction to amniotic fluid and questions to discuss with your pregnancy care team about ultrasound assessment.",
    "nuchal-translucency-scan-a-complete-guide": "Explore nuchal translucency scan terminology and questions to discuss with your pregnancy care team before an NT scan appointment.",
    "twin-nuchal-translucency-scan-a-complete-guide-of": "Explore nuchal translucency scans in twin pregnancies and prepare questions to discuss with your clinician about the assessment.",
    "what-is-a-fetal-echo-scan-every-parent-should-know": "Explore fetal echocardiography in pregnancy and questions to discuss with your doctor about the assessment and appointment.",
    "twins-fetal-echo-a-complete-guide-for-parents": "Explore fetal echocardiography terminology in twin pregnancies and questions to discuss with your clinician before the appointment.",
    "the-dating-scan-detailed-explanation-of-the-dating": "Explore pregnancy dating scan terminology and questions to discuss with your clinician about gestational age and estimated due dates.",
    "twin-dating-scan-detailed-explanation-of-twin-dati": "Read an introduction to dating scans in twin pregnancies and prepare questions for your pregnancy care team about your appointment.",
    "early-tiffa-scan-baby-early-development": "Explore early TIFFA scan terminology and questions to discuss with your pregnancy care team about an assessment and appointment.",
    "twin-early-tiffa-scan-what-you-need-to-know-as-a-p": "Explore early TIFFA assessment in twin pregnancies and questions to discuss with your clinician before an ultrasound appointment.",
    "early-pregnancy-viability-scan-the-complete-guide": "Read an introduction to early pregnancy viability scans and prepare questions to discuss with your doctor before an ultrasound appointment.",
    "twin-viability-scan-what-it-checks-and-why-it-matt": "Read an introduction to viability scans in twin pregnancies and questions to discuss with your doctor about your assessment.",
    "late-tiffa-anomaly-scan-what-it-checks-and-why-it": "Read about later TIFFA and anomaly assessments, with questions to ask your clinician about the purpose and details of your appointment.",
    "twin-late-tiffa-anomaly-scan-what-you-need-to-know": "Read about later TIFFA and anomaly assessments in twin pregnancies, including appointment questions for your pregnancy care team.",
    "routine-growth-scan-what-it-checks-and-why-it-matt": "Read about pregnancy growth scans and prepare questions for your doctor about ultrasound assessment, reports and follow-up discussions.",
    "twin-routine-growth-scan-what-it-checks-and-why-it": "Read about growth scans in twin pregnancies and questions to ask your doctor about ultrasound appointments, findings and follow-up.",
}

ARTICLE_GROUPS = (
    ("what-is-a-fetal-anomaly-scan", "your-babys-first-detailed-health-check-understandi", "twin-tiffa-scan-a-complete-guide-for-parents", "early-tiffa-scan-baby-early-development", "twin-early-tiffa-scan-what-you-need-to-know-as-a-p", "late-tiffa-anomaly-scan-what-it-checks-and-why-it", "twin-late-tiffa-anomaly-scan-what-you-need-to-know"),
    ("nuchal-translucency-scan-a-complete-guide", "twin-nuchal-translucency-scan-a-complete-guide-of"),
    ("the-dating-scan-detailed-explanation-of-the-dating", "twin-dating-scan-detailed-explanation-of-twin-dati"),
    ("early-pregnancy-viability-scan-the-complete-guide", "twin-viability-scan-what-it-checks-and-why-it-matt"),
    ("routine-growth-scan-what-it-checks-and-why-it-matt", "twin-routine-growth-scan-what-it-checks-and-why-it", "what-is-amniotic-fluid-how-doctors-check-it"),
    ("what-is-a-fetal-echo-scan-every-parent-should-know", "twins-fetal-echo-a-complete-guide-for-parents"),
)


def related_article_slugs(slug):
    """Candidate links only; views must still filter unpublished/deleted posts."""
    return next((tuple(s for s in group if s != slug) for group in ARTICLE_GROUPS if slug in group), ())


# These are summaries of services already listed on /services/, not clinical
# instructions. Prices, preparation and timing remain questions for the clinic.
SERVICE_GUIDES = (
    {
        "title": "TIFFA / Anomaly Scans",
        "description": "TIFFA and anomaly scans are listed among our antenatal services. Explore the existing patient guides and contact the clinic about an appointment.",
        "fragment": "antenatal-gynecological-scans",
        "slugs": ("your-babys-first-detailed-health-check-understandi", "what-is-a-fetal-anomaly-scan", "twin-tiffa-scan-a-complete-guide-for-parents"),
    },
    {
        "title": "Nuchal Translucency (NT) Scans",
        "description": "Find our existing guides to NT scans in singleton and twin pregnancies. Ask the clinic about scan availability, preparation instructions and appointment fees.",
        "fragment": "antenatal-gynecological-scans",
        "slugs": ("nuchal-translucency-scan-a-complete-guide", "twin-nuchal-translucency-scan-a-complete-guide-of"),
    },
    {
        "title": "Abdominal Ultrasound Scans",
        "description": "Whole abdomen, pelvis and KUB scans are listed under our routine ultrasound services. Contact the clinic to confirm the scan requested by your referring doctor and any preparation needed.",
        "fragment": "routine-scans",
        "slugs": (),
    },
    {
        "title": "Doppler Scans",
        "description": "Our services include arterial and venous Doppler studies, with obstetric Doppler listed separately under antenatal scans. Contact the clinic about the specific study on your referral.",
        "fragment": "doppler-scans",
        "slugs": (),
    },
)
