"""Disciplines de la médecine vétérinaire et mots-clés (anglais, langue des résumés)
utilisés pour classer chaque étude. L'ordre définit l'ordre des rubriques du podcast."""

DISCIPLINES = {
    "dermatologie": {
        "label": "Dermatologie",
        "keywords": ["atopic", "dermatitis", "pruritus", "pruritic", "skin", "cutaneous", "otitis",
                     "pyoderma", "alopecia", "malassezia", "dermatophyt", "pemphigus", "allergen",
                     "oclacitinib", "lokivetmab", "flea allergy", "keratinization", "ear canal"],
    },
    "cardiologie": {
        "label": "Cardiologie",
        "keywords": ["cardiac", "heart", "myxomatous", "mitral", "cardiomyopathy", "arrhythmia",
                     "echocardiograph", "pimobendan", "congestive heart failure", "nt-probnp",
                     "troponin", "atrial", "ventricular", "pulmonary hypertension", "electrocardiog",
                     "systemic hypertension", "blood pressure"],
    },
    "oncologie": {
        "label": "Oncologie",
        "keywords": ["tumor", "tumour", "neoplas", "cancer", "carcinoma", "sarcoma", "lymphoma",
                     "mast cell", "chemotherapy", "radiotherapy", "radiation therapy", "metasta",
                     "oncolog", "osteosarcoma", "hemangiosarcoma", "melanoma", "malignan"],
    },
    "nephrologie": {
        "label": "Néphrologie et urologie",
        "keywords": ["kidney", "renal", "chronic kidney disease", "ckd", "acute kidney injury",
                     "urinary", "urolith", "cystitis", "proteinuria", "sdma", "creatinine",
                     "bladder", "urethral", "ureter", "dialysis", "iris stag"],
    },
    "gastro": {
        "label": "Gastro-entérologie et hépatologie",
        "keywords": ["gastrointestinal", "enteropathy", "diarrh", "vomiting", "liver", "hepat",
                     "pancreatitis", "pancrea", "intestinal", "colitis", "gastric", "esophag",
                     "oesophag", "biliary", "gallbladder", "microbiome", "fecal", "faecal",
                     "inflammatory bowel", "portosystemic", "cobalamin"],
    },
    "endocrinologie": {
        "label": "Endocrinologie",
        "keywords": ["diabetes", "diabetic", "insulin", "hyperthyroid", "hypothyroid", "thyroid",
                     "cushing", "hyperadrenocorticism", "hypoadrenocorticism", "addison", "cortisol",
                     "acromegaly", "endocrin", "trilostane", "glucose", "fructosamine", "parathyroid"],
    },
    "neurologie": {
        "label": "Neurologie",
        "keywords": ["seizure", "epilep", "neurolog", "intervertebral disc", "spinal cord",
                     "brain", "meningo", "encephal", "myelopathy", "syringomyelia", "chiari",
                     "vestibular", "neuropathy", "cognitive dysfunction", "paresis"],
    },
    "ophtalmologie": {
        "label": "Ophtalmologie",
        "keywords": ["ocular", "ophthalm", "cornea", "corneal", "glaucoma", "cataract", "retina",
                     "uveitis", "keratoconjunctivitis", "conjunctiv", "intraocular", "eyelid", "lens"],
    },
    "chirurgie": {
        "label": "Chirurgie et orthopédie",
        "keywords": ["surgical", "surgery", "postoperative", "laparoscop", "arthroscop", "fracture",
                     "cranial cruciate", "tplo", "osteotomy", "orthop", "osteoarthritis", "hip dysplasia",
                     "elbow dysplasia", "patellar luxation", "wound", "dehiscence", "implant",
                     "brachycephalic obstructive", "boas", "ovariohysterectomy", "gonadectomy"],
    },
    "anesthesie": {
        "label": "Anesthésie et analgésie",
        "keywords": ["anesthe", "anaesthe", "analges", "sedation", "propofol", "alfaxalone",
                     "isoflurane", "sevoflurane", "dexmedetomidine", "opioid", "methadone",
                     "buprenorphine", "nerve block", "epidural", "pain score", "premedication"],
    },
    "urgences": {
        "label": "Urgences et soins intensifs",
        "keywords": ["emergency", "critical care", "intensive care", "sepsis", "septic", "shock",
                     "trauma", "resuscitation", "cardiopulmonary", "transfusion", "toxicos",
                     "intoxication", "poisoning", "hemoabdomen", "fluid therapy", "lactate",
                     "gastric dilatation"],
    },
    "imagerie": {
        "label": "Imagerie médicale",
        "keywords": ["computed tomography", "magnetic resonance", "mri", "ultrasonograph",
                     "radiograph", "imaging", "contrast-enhanced", "scintigraph", "fluoroscop",
                     "ct scan", "point-of-care ultrasound", "pocus"],
    },
    "infectiologie": {
        "label": "Maladies infectieuses et parasitologie",
        "keywords": ["infection", "infectious", "bacterial", "viral", "virus", "antimicrobial",
                     "antibiotic", "resistance", "leishmani", "parvovirus", "fip", "feline infectious peritonitis",
                     "felv", "fiv", "leptospir", "babesi", "ehrlichi", "anaplasm", "dirofilari", "heartworm",
                     "angiostrongyl", "tick", "flea", "giardia", "toxoplasm", "parasit", "vaccin",
                     "zoono", "mrsp", "staphylococcus", "escherichia"],
    },
    "hemato_immuno": {
        "label": "Hématologie et immunologie",
        "keywords": ["immune-mediated", "imha", "itp", "thrombocytopenia", "anemia", "anaemia",
                     "coagulation", "thromboelastograph", "hemostasis", "haemostasis", "thrombo",
                     "immunosuppress", "lupus", "polyarthritis", "blood type"],
    },
    "medecine_interne": {
        "label": "Médecine interne générale",
        "keywords": ["internal medicine", "respiratory", "bronch", "pneumonia", "asthma", "airway",
                     "nasal", "laryng", "obesity", "geriatric", "senior", "comorbid", "biomarker",
                     "polyuria", "fever"],
    },
    "biologie": {
        "label": "Biologie clinique et pathologie",
        "keywords": ["clinical pathology", "hematolog", "haematolog", "cytolog", "histopatholog",
                     "reference interval", "analyzer", "analyser", "biochemistry", "assay",
                     "immunohistochem", "necropsy"],
    },
    "pharmacologie": {
        "label": "Pharmacologie et thérapeutique",
        "keywords": ["pharmacokinetic", "pharmacodynamic", "bioavailability", "dose", "dosing",
                     "drug", "adverse event", "adverse drug", "plasma concentration", "formulation"],
    },
    "reproduction": {
        "label": "Reproduction et néonatologie",
        "keywords": ["pregnan", "neonat", "puppies", "kittens", "dystocia", "cesarean", "caesarean",
                     "estrous", "oestrous", "semen", "sperm", "pyometra", "mammary", "castration",
                     "contracept", "fertility", "deslorelin"],
    },
    "comportement": {
        "label": "Comportement et bien-être",
        "keywords": ["behavio", "anxiety", "aggression", "fear", "stress", "welfare", "separation",
                     "owner-reported", "quality of life", "human-animal", "training", "cognition"],
    },
    "nutrition": {
        "label": "Nutrition",
        "keywords": ["diet", "dietary", "nutrition", "food", "feeding", "body condition",
                     "weight loss", "grain-free", "raw meat", "taurine", "omega-3", "supplement"],
    },
    "dentisterie": {
        "label": "Dentisterie et chirurgie maxillo-faciale",
        "keywords": ["dental", "dentist", "periodont", "tooth", "teeth", "oral", "stomatitis",
                     "gingiv", "maxill", "mandib", "resorptive lesion", "endodont"],
    },
    "epidemiologie": {
        "label": "Épidémiologie et santé publique",
        "keywords": ["epidemiolog", "prevalence", "incidence", "risk factor", "cohort", "population",
                     "breed predisposition", "vetcompass", "survey", "one health", "mortality",
                     "longevity", "life expectancy"],
    },
}

DEFAULT = "medecine_interne"


def label(key: str) -> str:
    return DISCIPLINES.get(key, DISCIPLINES[DEFAULT])["label"]


def order(key: str) -> int:
    keys = list(DISCIPLINES)
    return keys.index(key) if key in keys else len(keys)
