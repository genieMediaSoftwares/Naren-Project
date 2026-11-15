"""Presentation-independent search metadata. No clinical content or attribution."""

ORIGIN = "https://www.narenultrasound.in"
CLINIC_ID = ORIGIN + "/#clinic"

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
    "home": ("Ultrasound & Fetal Medicine in Visakhapatnam | Naren Ultrasound", "Explore ultrasound and fetal medicine services at Naren Ultrasound in Maharanipeta, Visakhapatnam. Find scan services, clinic details and appointments."),
    "about": ("About Naren Ultrasound | Visakhapatnam", "Learn about Naren Ultrasound & Fetal Medicine Center in Maharanipeta, Visakhapatnam, its ultrasound services and patient-focused approach."),
    "services": ("Ultrasound Scan Services in Visakhapatnam | Naren Ultrasound", "Explore pregnancy, gynecological, routine, paediatric, Doppler and small-parts ultrasound services and USG-guided procedures at Naren Ultrasound."),
    "doctors": ("Dr. Naren Satya | Naren Ultrasound Visakhapatnam", "Read the profile of Dr. Naren Satya at Naren Ultrasound & Fetal Medicine Center in Visakhapatnam and explore the clinic's ultrasound services."),
    "gallery": ("Clinic Gallery | Naren Ultrasound Visakhapatnam", "View the existing clinic gallery at Naren Ultrasound & Fetal Medicine Center in Visakhapatnam and find contact and appointment information."),
    "patient_info": ("Ultrasound Appointments in Visakhapatnam | Naren Ultrasound", "Find clinic hours, patient information and ultrasound appointment options at Naren Ultrasound in Maharanipeta, Visakhapatnam."),
    "contact": ("Contact & Directions | Naren Ultrasound Visakhapatnam", "Find the address, phone numbers, clinic hours and directions for Naren Ultrasound in Maharanipeta, Visakhapatnam. Contact the clinic for scan enquiries."),
    "blog_list": ("Pregnancy Ultrasound Guides | Naren Ultrasound", "Browse articles on TIFFA, NT, dating, viability, growth and fetal echo scans, including twin pregnancy topics, from Naren Ultrasound in Visakhapatnam."),
}

# Exact existing slugs: metadata only; the stored title and article stay intact.
ARTICLE_TOPICS = {
    "what-is-a-fetal-anomaly-scan": ("Fetal Anomaly Scan: Purpose & What to Expect", "fetal anomaly scans, their purpose and what to expect at an appointment"),
    "your-babys-first-detailed-health-check-understandi": ("TIFFA Scan: Meaning & What to Expect", "TIFFA scan terminology and what an ultrasound appointment involves"),
    "twin-tiffa-scan-a-complete-guide-for-parents": ("Twin TIFFA Scan: A Guide for Parents", "TIFFA scans in twin pregnancies and questions to discuss with your doctor"),
    "what-is-amniotic-fluid-how-doctors-check-it": ("Amniotic Fluid: What It Is & How It Is Assessed", "amniotic fluid and its assessment during pregnancy"),
    "nuchal-translucency-scan-a-complete-guide": ("NT Scan in Pregnancy: A Patient Guide", "nuchal translucency (NT) scans and questions to discuss at your pregnancy appointment"),
    "twin-nuchal-translucency-scan-a-complete-guide-of": ("Twin NT Scan: A Guide for Parents", "nuchal translucency (NT) scans in twin pregnancies"),
    "what-is-a-fetal-echo-scan-every-parent-should-know": ("Fetal Echo in Pregnancy: What to Expect", "fetal echocardiography in pregnancy and what to discuss with your doctor"),
    "twins-fetal-echo-a-complete-guide-for-parents": ("Fetal Echo for Twins: A Patient Guide", "fetal echocardiography in twin pregnancies and appointment questions"),
    "the-dating-scan-detailed-explanation-of-the-dating": ("Dating Scan: A Guide for Expectant Parents", "pregnancy dating scans and questions about gestational age and due dates"),
    "twin-dating-scan-detailed-explanation-of-twin-dati": ("Twin Dating Scan: A Guide for Parents", "dating scans for twin pregnancies and questions for your appointment"),
    "early-tiffa-scan-baby-early-development": ("Early TIFFA Scan: A Patient Guide", "early TIFFA scans and questions to discuss with your pregnancy care team"),
    "twin-early-tiffa-scan-what-you-need-to-know-as-a-p": ("Twin Early TIFFA Scan: A Patient Guide", "early TIFFA scans in twin pregnancies and appointment questions"),
    "early-pregnancy-viability-scan-the-complete-guide": ("Early Pregnancy Viability Scan: A Patient Guide", "early pregnancy viability scans and what to discuss with your doctor"),
    "twin-viability-scan-what-it-checks-and-why-it-matt": ("Twin Viability Scan: A Guide for Parents", "viability scans in twin pregnancies and questions for your doctor"),
    "late-tiffa-anomaly-scan-what-it-checks-and-why-it": ("Late TIFFA / Anomaly Scan: A Patient Guide", "later TIFFA or anomaly assessments and questions to discuss with your doctor"),
    "twin-late-tiffa-anomaly-scan-what-you-need-to-know": ("Twin Late TIFFA Scan: A Patient Guide", "later TIFFA or anomaly assessments in twin pregnancies"),
    "routine-growth-scan-what-it-checks-and-why-it-matt": ("Growth Scan in Pregnancy: A Patient Guide", "pregnancy growth scans and questions about ultrasound and Doppler assessment"),
    "twin-routine-growth-scan-what-it-checks-and-why-it": ("Twin Growth Scan: A Guide for Parents", "growth scans in twin pregnancies and questions to discuss with your doctor"),
}
