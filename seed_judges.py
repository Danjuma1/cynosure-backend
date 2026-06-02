#!/usr/bin/env python3
"""
Regenerates all judges.judge records in final_fixture.json from the official
Lagos and Abuja judges lists. Also adds any missing court records.

Run from the backend directory:
    python seed_judges.py
"""
import json
import re
import uuid
import os

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FIXTURE_PATH = os.environ.get(
    'FIXTURE_PATH',
    os.path.join(os.path.dirname(__file__), 'final_fixture.json'),
)
UUID_NS = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # URL namespace

# ---------------------------------------------------------------------------
# Existing court PKs
# ---------------------------------------------------------------------------

SC        = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'  # Supreme Court
CA_LAGOS  = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'  # Court of Appeal Lagos
FHC_LAGOS = 'cccccccc-cccc-cccc-cccc-cccccccccccc'  # Federal High Court Lagos
FHC_ABUJA = 'dddddddd-dddd-dddd-dddd-dddddddddddd'  # Federal High Court Abuja
SHC_LAGOS = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'  # Lagos State High Court
NIC_LAGOS = 'ffffffff-ffff-ffff-ffff-ffffffffffff'  # National Industrial Court Lagos

# New court PKs (valid UUID hex, sequential)
MC_LAGOS  = '00000001-0000-4000-a000-000000000001'  # Magistrate Court Lagos
FCT_HC    = '00000002-0000-4000-a000-000000000002'  # FCT High Court Abuja
CA_ABUJA  = '00000003-0000-4000-a000-000000000003'  # Court of Appeal Abuja
NIC_ABUJA = '00000004-0000-4000-a000-000000000004'  # National Industrial Court Abuja

NEW_COURTS = [
    {
        "model": "courts.court",
        "pk": MC_LAGOS,
        "fields": {
            "name": "Magistrate Court of Lagos State",
            "code": "MC-LA",
            "court_type": "MC",
            "state": "LA",
            "city": "Lagos",
            "address": "Lagos, Nigeria",
            "phone": "",
            "email": "",
            "website": "",
            "is_active": True,
            "is_deleted": False,
            "follower_count": 0,
        }
    },
    {
        "model": "courts.court",
        "pk": FCT_HC,
        "fields": {
            "name": "High Court of the Federal Capital Territory",
            "code": "FCT-HC",
            "court_type": "FCT",
            "state": "FC",
            "city": "Abuja",
            "address": "Maitama, Abuja, FCT",
            "phone": "",
            "email": "",
            "website": "",
            "is_active": True,
            "is_deleted": False,
            "follower_count": 0,
        }
    },
    {
        "model": "courts.court",
        "pk": CA_ABUJA,
        "fields": {
            "name": "Court of Appeal Abuja Division",
            "code": "CA-ABJ",
            "court_type": "CA",
            "state": "FC",
            "city": "Abuja",
            "address": "Abuja, FCT",
            "phone": "",
            "email": "",
            "website": "",
            "is_active": True,
            "is_deleted": False,
            "follower_count": 0,
        }
    },
    {
        "model": "courts.court",
        "pk": NIC_ABUJA,
        "fields": {
            "name": "National Industrial Court Abuja Division",
            "code": "NIC-ABJ",
            "court_type": "NIC",
            "state": "FC",
            "city": "Abuja",
            "address": "Abuja, FCT",
            "phone": "",
            "email": "",
            "website": "",
            "is_active": True,
            "is_deleted": False,
            "follower_count": 0,
        }
    },
]

# ---------------------------------------------------------------------------
# Raw judges data
# Format: (name_as_given, location, is_retired, is_chief_judge)
# ---------------------------------------------------------------------------

LAGOS_SHC_JUDGES = [
    ("O.A. Adamson",            "Ikeja",                                False, False),
    ("M.O. Dawodu",             "Ikeja",                                False, False),
    ("K.O. Dawodu",             "Commercial Court, Tapa",               False, False),
    ("E.O. Ogundare",           "Badagry",                              False, False),
    ("Y.A. Adesanya",           "Taylor Courthouse, Igbosere",          False, False),
    ("I.O. Harrison",           "Taylor Courthouse, Igbosere",          False, False),
    ("A.M. Nicol-Clay",         "Ikeja",                                False, False),
    ("S.I. Sonaike",            "Taylor Courthouse, Igbosere",          False, False),
    ("A.J. Coker",              "Ikeja",                                False, False),
    ("O.O.A. Fadipe",           "Ikeja",                                False, False),
    ("I.O. Ijelu",              "Ikeja",                                False, False),
    ("O.A. Ogala",              "Ikeja",                                False, False),
    ("H.O. Oshodi",             "Ikeja",                                False, False),
    ("F.A. Azeez",              "Ikeja",                                False, False),
    ("W.A. Animahun",           "Epe",                                  False, False),
    ("S.A. Olaitan",            "Epe",                                  False, False),
    ("W. Animahun",             "Epe",                                  False, False),
    ("M.O. Obadina",            "Ikeja",                                False, False),
    ("C.A. Balogun",            "Ikeja",                                True,  False),
    ("A.A. Oyebanji",           "Taylor Courthouse, Igbosere",          False, False),
    ("M.M. Balogun",            "Sabo/Yaba, Surulere",                  False, False),
    ("O.I. Oguntade",           "Old Secretariat Courthouse, Ikeja",    False, False),
    ("O.J. Awope",              "Ikeja",                                False, False),
    ("A.O. Adeyemi",            "Ikeja",                                False, False),
    ("A.A. Akintoye",           "Ikeja",                                True,  False),
    ("A.M. Ipaye-Nwachukwu",    "Ikeja",                                False, False),
    ("K.A. Jose",               "Commercial Court, Tapa",               False, False),
    ("L.A. Okunnu",             "Commercial Court, Tapa",               False, False),
    ("R.O. Olukolu",            "Commercial Court, Tapa",               False, False),
    ("O.O. Pedro",              "Commercial Court, Tapa",               False, False),
    ("K.O. Alogba",             "Ikeja",                                False, False),
    ("O.O. Adewunmi-Oshin",     "Osborn Foreshore",                     False, False),
    ("L.A.M. Folami",           "T.B.S, Lagos",                         False, False),
    ("O.A. Ipaye",              "Osborn Foreshore",                     False, False),
    ("L.B. Lawal-Akapo",        "Ikeja",                                True,  False),
    ("B.O. Kalaro",             "Alausa CBD Courthouse, Ikeja",         False, False),
    ("D.T. Olatokun",           "Ikeja",                                False, False),
    ("L.A.F. Oluyemi",          "Ikeja",                                False, False),
    ("Y.R. Pinheiro",           "Ikeja",                                False, False),
    ("F.O. Aigbokaevbo",        "Ajah",                                 False, False),
    ("I.E. Alakija",            "Taylor Courthouse, Igbosere",          False, False),
    ("O.O. Ogungbesan",         "Taylor Courthouse, Igbosere",          False, False),
    ("A.O. Opesanwo",           "Osborn Foreshore",                     False, False),
    ("O.A. Oresanya",           "Ikeja",                                False, False),
    ("J.E. Oyefeso",            "Ajah",                                 False, False),
    ("T.A.O. Oyekan-Abdullai",  "Ikeja",                                True,  False),
    ("G.A. Safari",             "Eti-Osa",                              False, False),
    ("O. Sule-Amzat",           "Sabo/Yaba, Surulere",                  False, False),
    ("A.J. Bashua",             "Sabo/Yaba, Surulere",                  False, False),
    ("I.O. Akinkugbe",          "Ikorodu",                              False, False),
    ("M.I. Oshodi",             "Ikorodu",                              False, False),
    ("A.F. Pokanu",             "Ikorodu",                              False, False),
    ("O.O. Martins",            "Osborn Foreshore",                     False, False),
    ("O.A. Akinlade",           "Osborn Foreshore",                     False, False),
    ("E.O. Ashade",             "Sabo/Yaba, Surulere",                  False, False),
    ("O.O. Ogunjobi",           "Taylor Courthouse, Igbosere",          False, False),
    ("R.I.B. Adebiyi",          "Ikeja",                                False, False),
    ("A.M. Lawal",              "Ikeja",                                False, False),
    # M.O. Obadina already added above (entry 18 = entry 59)
    ("O.A. Odunsanya",          "Ikeja",                                False, False),
    ("S.S. Ogunsanya",          "Ikeja",                                False, False),
    ("Y.G. Oshoala",            "Old Secretariat Courthouse, Ikeja",    False, False),
    ("A.O. Idowu",              "Old Secretariat Courthouse, Ikeja",    False, False),
    ("M.A. Savage",             "Ikeja",                                False, False),
    ("A.A. George",             "Osborn Foreshore",                     False, False),
    ("Y.J. Badejo-Okusanya",    "Osborn Foreshore",                     False, False),
    ("N.O.O. Ojuromi",          "Osborn Foreshore",                     False, False),
    ("O.A. Okunuga",            "Ikeja",                                False, False),
    ("A.K. Shonubi",            "Ikeja",                                False, False),
    ("O.A. Layinka",            "Ikeja",                                False, False),
    ("T.B. Sunmonu",            "Commercial Court, Tapa",               False, False),
    ("R.M. Adewale",            "Roseline O. Courthouse, Ikeja",        False, False),
    ("A.G. Balogun",            "Roseline O. Courthouse, Ikeja",        False, False),
    ("T.A. Anjorin-Ajose",      "Commercial Court, Tapa",               False, False),
    ("O.L. Alebiosu",           "Ikeja",                                False, False),
    ("A.T. Muyideen",           "Taylor Courthouse, Igbosere",          False, False),
    ("O.A. Popoola",            "Ikeja",                                False, False),
    ("A.O. Soladoye",           "Ikeja",                                False, False),
    ("M.A. Dada",               "Ikeja",                                False, False),
    ("R.A. Oshodi",             "Roseline O. Courthouse, Ikeja",        False, False),
]

LAGOS_NIC_JUDGES = [
    ("A.N. Ubaka",          "Court 3, NICN Lagos",   False, False),
    ("R.B. Gwandu",         "Court 4, NICN Lagos",   False, False),
    ("S.A. Yelwa",          "Court 9, NICN Lagos",   False, False),
    ("Joyce A.O. Damachi",  "Court 8, NICN Lagos",   False, False),
    ("I.G. Nweneka",        "Court 5, NICN Lagos",   False, False),
    ("M.N. Esowe",          "Court 2, NICN Lagos",   False, False),
    ("(Prof.) E.A. Oji",    "Court 7, NICN Lagos",   False, False),
    ("I.J. Essien",         "Court 6, NICN Lagos",   False, False),
]

LAGOS_FHC_JUDGES = [
    ("A.O. Faji",                  "Court 2, FHC Ikoyi",  False, False),
    ("Musa Kakaki",                "Court 10, FHC Ikoyi", False, False),
    ("Ogazi Friday Nkemakonam",    "Court 12, FHC Ikoyi", False, False),
    ("Daniel E. Osiagor",          "Court 6, FHC Ikoyi",  False, False),
    ("Akintayo Aluko",             "Court 7, FHC Ikoyi",  False, False),
    ("A.O. Owoeye",                "Court 9, FHC Ikoyi",  False, False),
    ("C.J. Aneke",                 "Court 4, FHC Ikoyi",  False, False),
    ("D.I. Dipeolu",               "Court 8, FHC Ikoyi",  False, False),
    ("Y.S. Bogoro",                "Court 5, FHC Ikoyi",  False, False),
    ("A. Lewis-Allagoa",           "Court 3, FHC Ikoyi",  False, False),
    ("I.A. Kala",                  "Court 11, FHC Ikoyi", False, False),
]

# Rows 1-2 of the magistrate list are registrar staff (not magistrates) — excluded.
# Rows 3-5 are Chief Magistrates (Admin), rows 6+ are Magistrates.
LAGOS_MAGISTRATES = [
    ("P.A. Ojo",                "Lagos",    False, True),   # Chief Magistrate (Admin)
    ("Y.O. Aje-Afunwa",         "Lagos",    False, True),   # Chief Magistrate (Admin)
    ("A.O. Adedayo",            "Lagos",    False, True),   # Chief Magistrate (Admin)
    ("O.I. Adelaja",            "Lagos",    False, False),
    ("A.A. Oshoniyi",           "Lagos",    False, False),
    ("O.O. Oshin",              "Lagos",    False, False),
    ("F.O. Aigbokhaevbo",       "Lagos",    False, False),
    ("F.A. Azeez",              "Lagos",    False, False),
    ("A. Ipaye-Nwachukwu",      "Lagos",    False, False),
    ("T.A. Elias",              "Lagos",    False, False),
    ("O.J. Awope",              "Lagos",    False, False),
    ("A.K. Shonubi",            "Lagos",    False, False),
    ("T.O. Shomade",            "Lagos",    False, False),
    ("A.F.O. Botoku",           "Lagos",    False, False),
    ("K.B. Ayeye",              "Lagos",    False, False),
    ("A.M. Alli-Balogun",       "Lagos",    False, False),
    ("B.O. Osunsanmi",          "Lagos",    False, False),
    ("A.O. Komolafe",           "Lagos",    False, False),
    ("O.I. Oguntade",           "Lagos",    False, False),
    ("O.O. Martins",            "Lagos",    False, False),
    ("Y.J. Badejo-Okusanya",    "Lagos",    False, False),
    ("R.O. Davies",             "Lagos",    False, False),
    ("A.O. Layinka",            "Lagos",    False, False),
    ("O. Sule-Amzat",           "Lagos",    False, False),
    ("O.O. Olatunji",           "Lagos",    False, False),
    ("E.O. Ogunkanmi",          "Lagos",    False, False),
    ("F.M. Kayode-Alamu",       "Lagos",    False, False),
    ("B.A. Sonuga",             "Lagos",    False, False),
    ("T. Akanni",               "Lagos",    False, False),
    ("O.A. Adegbite",           "Lagos",    False, False),
    ("P.A. Adekomaiya",         "Lagos",    False, False),
    ("M.K.O. Fadeyi",           "Lagos",    False, False),
    ("W.B. Balogun",            "Lagos",    False, False),
    ("J.O.E. Adeyemi",          "Lagos",    False, False),
    ("M. Owumi",                "Lagos",    False, False),
    ("A.A. Paul",               "Lagos",    False, False),
    ("O.A. Komolafe",           "Lagos",    False, False),
    ("K.O. Doja-Ojo",           "Lagos",    False, False),
    ("C.J. Momodu",             "Lagos",    False, False),
    ("A.O. Ajibade",            "Lagos",    False, False),
    ("A.O. Gbajumo",            "Lagos",    False, False),
    ("O.G. Oghre",              "Lagos",    False, False),
    ("O.A. Akinde",             "Lagos",    False, False),
    ("H.O.A. Amos",             "Lagos",    False, False),
    ("O. Kusanu",               "Lagos",    False, False),
    ("P.E. Nwaka",              "Lagos",    False, False),
    ("A.B. Olagbegi-Adelabu",   "Lagos",    False, False),
    ("H.O. Omisore",            "Lagos",    False, False),
    ("A.M. Olumide-Fusika",     "Lagos",    False, False),
    ("F.J. Adefioye",           "Lagos",    False, False),
    ("E. Kubeinje",             "Lagos",    False, False),
    ("O.O.A. Fowowe-Erusiafe",  "Lagos",    False, False),
    ("O.A. Aka-Bashorun",       "Lagos",    False, False),
    ("G.L. Hotepo",             "Lagos",    False, False),
    ("J.A. Adegun",             "Lagos",    False, False),
    ("A.T. Omoyele",            "Lagos",    False, False),
    ("M.I. Dan-Oni",            "Lagos",    False, False),
    ("A.S. Odusanya",           "Lagos",    False, False),
    ("S.K. Matepo",             "Lagos",    False, False),
    ("M.O. Olubi",              "Lagos",    False, False),
    ("M.O. Tanimola",           "Lagos",    False, False),
    ("O.M. Ajayi",              "Lagos",    False, False),
    ("K.O. Ogundare",           "Lagos",    False, False),
    ("J. Ugbomoiko",            "Lagos",    False, False),
    ("A.O. Oshodi-Makanju",     "Lagos",    False, False),
    ("A.A. Fashola",            "Lagos",    False, False),
    ("L.Y. Balogun",            "Lagos",    False, False),
    ("B.O. Ope-Agbe",           "Lagos",    False, False),
    ("B. Folarin-Williams",     "Lagos",    False, False),
    ("A.A. Adesanya",           "Lagos",    False, False),
    ("A.O. Onilogbo",           "Lagos",    False, False),
    ("A.A. Famobiwo",           "Lagos",    False, False),
    ("L.A. Owolabi",            "Lagos",    False, False),
    ("F.F. George",             "Lagos",    False, False),
    ("K.A. Ariyo",              "Lagos",    False, False),
    ("O.A. Olagbende",          "Lagos",    False, False),
    ("A.M. Davies",             "Lagos",    False, False),
    ("M.O. Osinbajo",           "Lagos",    False, False),
    ("O.A. Erinle",             "Lagos",    False, False),
    ("O.O. Ojuromi",            "Lagos",    False, False),
    ("F. Dalley",               "Lagos",    False, False),
    ("N.A. Layeni",             "Lagos",    False, False),
    ("G.O. Anifowoshe",         "Lagos",    False, False),
    ("I.O. Alaka",              "Lagos",    False, False),
    ("T.O. Babalola",           "Lagos",    False, False),
    ("O.O. Otitoju",            "Lagos",    False, False),
    ("O.A. Akokhia",            "Lagos",    False, False),
    ("Y.O. Ekogbulu",           "Lagos",    False, False),
    ("A.A. Gbajumo-Ayoku",      "Lagos",    False, False),
    ("A.A. Adetunji",           "Lagos",    False, False),
    ("B.I. Bakare",             "Lagos",    False, False),
    ("F. Ikobayo",              "Lagos",    False, False),
    ("T.A. Idowu",              "Lagos",    False, False),
    ("O.A. Salawu",             "Lagos",    False, False),
    ("L.O. Kazeem",             "Lagos",    False, False),
    ("T.O. Abayomi",            "Lagos",    False, False),
    ("O.I. Raji",               "Lagos",    False, False),
    ("K.S. Abdul-Salam",        "Lagos",    False, False),
    ("A.O. Ogbe",               "Lagos",    False, False),
    ("Y.O. Aro-Lambo",          "Lagos",    False, False),
    ("M.B. Amore",              "Lagos",    False, False),
    ("O.A. Odunayo",            "Lagos",    False, False),
    ("A.S. Okubule",            "Lagos",    False, False),
    ("O.S. Abioye",             "Lagos",    False, False),
    ("A.K. Tella",              "Lagos",    False, False),
    ("T.A. Ojo",                "Lagos",    False, False),
    ("A.K. Dosunmu",            "Lagos",    False, False),
    ("I.A. Abina",              "Lagos",    False, False),
    ("K.J. Layeni",             "Lagos",    False, False),
    ("R.A. Oladele",            "Lagos",    False, False),
    ("W.A. Salami",             "Lagos",    False, False),
    ("M.F. Onamusi",            "Lagos",    False, False),
    ("O.A. Ogunjobi",           "Lagos",    False, False),
    ("T. Anjorin-Ajose",        "Lagos",    False, False),
    ("O.O. Akingbesote",        "Lagos",    False, False),
    ("O.O. Adeshina",           "Lagos",    False, False),
    ("T.F. Oyaniyi",            "Lagos",    False, False),
    ("O.C. Emeka-Opara",        "Lagos",    False, False),
    ("C.K. Tunji-Carrena",      "Lagos",    False, False),
    ("K.K. Awoyinka",           "Lagos",    False, False),
    ("O.A. Aderibigbe",         "Lagos",    False, False),
    ("S.A. Grillo",             "Lagos",    False, False),
    ("S.O. Obasa",              "Lagos",    False, False),
    ("F.A. Shittabey",          "Lagos",    False, False),
    ("O.O. Fajana",             "Lagos",    False, False),
    ("T.B. Are",                "Lagos",    False, False),
    ("O.O. Ekundayo",           "Lagos",    False, False),
    ("F.O. Sasanya",            "Lagos",    False, False),
    ("A.B. Ajiferuke",          "Lagos",    False, False),
    ("O. Isreal-Adelakun",      "Lagos",    False, False),
    ("M.A. Agbaje",             "Lagos",    False, False),
    ("T.J. Agbona",             "Lagos",    False, False),
    ("A.O. Olorunfemi",         "Lagos",    False, False),
    ("O.R. Williams-Isichei",   "Lagos",    False, False),
    ("R.I. Ayilara",            "Lagos",    False, False),
    ("O.A. Daodu",              "Lagos",    False, False),
    ("F.D. Hughes",             "Lagos",    False, False),
    ("M.O. Kadiri",             "Lagos",    False, False),
    ("H.B. Mogaji",             "Lagos",    False, False),
    ("A.A. Runsewe",            "Lagos",    False, False),
    ("T.R. Shekoni-Adeyekun",   "Lagos",    False, False),
    ("O.O. Fagbohun",           "Lagos",    False, False),
    ("A.R. Morafa",             "Lagos",    False, False),
    ("M.C. Ayinde",             "Lagos",    False, False),
    ("M.O. Dawodu",             "Lagos",    False, False),
    ("R.E. Ojudun",             "Lagos",    False, False),
    ("A.O. Alogba",             "Lagos",    False, False),
    ("O.D. Njoku",              "Lagos",    False, False),
    ("T.A. Popoola",            "Lagos",    False, False),
    ("G.O. Tiamiyu",            "Lagos",    False, False),
]

FCT_HC_JUDGES = [
    ("H.B. Yusuf",              "Court 1, Maitama",    False, True),   # Chief Judge
    ("S.C. Oriji",              "Court 2, Maitama",    False, False),
    ("M.E. Anenih",             "Court 3, Maitama",    False, False),
    ("U.P. Kekemeke",           "Court 4, Maitama",    False, False),
    ("M.A. Nasir",              "Court 5, Maitama",    False, False),
    ("O. Agbaza",               "Court 6, Maitama",    False, False),
    ("O.A. Musa",               "Court 7, Maitama",    False, False),
    ("C.N. Oji",                "Court 8, Maitama",    False, False),
    ("S.B. Belgore",            "Court 9, Garki",      False, False),
    ("A.L. Kutigi",             "Court 10, Jabi",      False, False),
    ("A.O. Otaluka",            "Court 11, Apo",       False, False),
    ("A.S. Adepoju",            "Court 12, Gwagwalada",False, False),
    ("Y. Halila",               "Court 13, Maitama",   False, False),
    ("B. Kawu",                 "Court 14, Apo",       False, False),
    ("K.N. Ogbonnaya",          "Court 15, Zuba",      False, False),
    ("A.O. Ebong",              "Court 16, Bwari",     False, False),
    ("B. Mohammed",             "Court 17, Apo",       False, False),
    ("M. Osho-Adebiyi",         "Court 18, Gwarinpa",  False, False),
    ("V.S. Gaba",               "Court 19, Kuje",      False, False),
    ("B. Hassan",               "Court 20, Nyaya",     False, False),
    ("A.L. Akobi",              "Court 21, Kubwa",     False, False),
    ("S.U. Bature",             "Court 22, Maitama",   False, False),
    ("E. Okpe",                 "Court 23, Gudu",      False, False),
    ("H. Mu'azu",               "Court 24, Maitama",   False, False),
    ("M.S. Idris",              "Court 25, Jabi",      False, False),
    ("O.J. Enobie",             "Court 26, Jabi",      False, False),
    ("B. Abubakar",             "Court 27, Apo",       False, False),
    ("A.H. Musa",               "Court 28, Apo",       False, False),
    ("C.O. Oba",                "Court 29, Apo",       False, False),
    ("J.O. Onwuegbuzie",        "Court 30, Apo",       False, False),
    ("A.A. Fashola",            "Court 31, Jabi",      False, False),
    ("F.E. Messiri",            "Court 32, Jabi",      False, False),
    ("M.A. Hassan",             "Court 33, Gwarinpa",  False, False),
    ("M.M. Adamu",              "Court 34, Gudu",      False, False),
    ("N.C. Nwabulu",            "Court 35, Jikwoyi",   False, False),
    ("C.O. Agashieze",          "Court 36, Lugbe",     False, False),
    ("M.A. Madugu",             "Court 37, Bwari",     False, False),
    ("J.O.E. Adeyemi-Ajayi",    "Court 38, Life Camp", False, False),
    ("O.I. Adelaja",            "Court 39, Kubwa",     False, False),
    ("K. Apunioye",             "Court 40, Gwagwalada",False, False),
    ("A.M. Abdullahi",          "Court 41, Jikwoyi",   False, False),
    ("R.I. Kanyip",             "Court 42, Life Camp", False, False),
    ("S.M. Mayana",             "Court 43, Apo",       False, False),
    ("C.E. Nwecheonwu",         "Court 44, Kuje",      False, False),
    ("A.Y. Shafa",              "Court 45, Nyaya",     False, False),
    ("B. Dogonyaro",            "Court 46, Apo",       False, False),
    ("M. Zubairu",              "Court 47, Jikwoyi",   False, False),
    ("M.A. Katsina-Alu",        "Court 48, Jikwoyi",   False, False),
    ("A.A. Halilu",             "Court 49, Apo",       False, False),
    ("I. Mohammed",             "Court 50, Gwagwalada",False, False),
    ("H.L. Abba-Aliyu",         "Court 51, Jabi",      False, False),
    ("N.K. Nwosu-Iheme",        "Court 52, Wuse Zone 2",False, False),
    ("F.A. Aliyu",              "Court 53, Apo",       False, False),
    ("J.A. Aina",               "Court 54, Gwagwalada",False, False),
    ("B.M. Bassi",              "Court 55, Asokoro",   False, False),
    ("A.O. Oyeyipo",            "Court 56, Jabi",      False, False),
    ("O.O. Bamodu",             "Court 57, Kuje",      False, False),
    ("A. Godwin Iheabunike",    "Court 58, Bwari",     False, False),
    ("Celestine O. Odo",        "Court 59, Kwali",     False, False),
    ("H.L. Gummi",              "Court 60, Asokoro",   False, False),
    ("S.B.L. Avoh",             "Court 61, Jabi",      False, False),
    ("M.I. Yusuf Daibu",        "Court 62, Garki",     False, False),
    ("O.V. Ariwoola",           "Court 63, Wuse Zone 2",False, False),
    ("L.N.B. Wike",             "Court 64, Gwarinpa",  False, False),
    ("M.L. Tanko",              "Court 65, Asokoro",   False, False),
    ("A. Tijani",               "Court 66, Kwali",     False, False),
]

FHC_ABUJA_JUDGES = [
    ("John T. Tsoho",                   "FHC Abuja", False, True),   # Chief Judge
    ("G.K. Olotu",                      "FHC Abuja", False, False),
    ("B.F.M. Nyako",                    "FHC Abuja", False, False),
    ("R.N. Ofili-Ajumogobia",           "FHC Abuja", False, False),
    ("A.R. Mohammed",                   "FHC Abuja", False, False),
    ("I.E. Ekwo",                       "FHC Abuja", False, False),
    ("D.U. Okorowo",                    "FHC Abuja", False, False),
    ("Joyce Obehi Abdulmalik",          "FHC Abuja", False, False),
    ("James Kolawale Omotosho",         "FHC Abuja", False, False),
    ("Emeka Nwite",                     "FHC Abuja", False, False),
    ("Obiora Atuegwu Egwuatu",          "FHC Abuja", False, False),
    ("Mobolaji Olubukola Olajuwon",     "FHC Abuja", False, False),
    ("Nkeonye Evelyn Maha",             "FHC Abuja", False, False),
    ("Salim Olasupo Ibrahim",           "FHC Abuja", False, False),
    ("Onah Chigozie Sergius",           "FHC Abuja", False, False),
]

NIC_ABUJA_JUDGES = [
    ("B.B. Kanyip",         "NICN Abuja", False, True),   # President NICN
    ("O.A. Obaseki-Osaghae","NICN Abuja", False, False),
    ("Z.M. Bashir",         "NICN Abuja", False, False),
    ("O.O. Arowosegbe",     "NICN Abuja", False, False),
    ("S.O. Adeniyi",        "NICN Abuja", False, False),
    ("Kado Sanusi",         "NICN Abuja", False, False),
    ("John I. Targema",     "NICN Abuja", False, False),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_name(raw):
    """Return (first_name, last_name) from a raw name string."""
    name = raw.split(',')[0].strip()
    name = re.sub(r'\(.*?\)', '', name).strip()
    name = re.sub(r'\s+', ' ', name)
    parts = name.split()
    if not parts:
        return 'Unknown', 'Unknown'
    if len(parts) == 1:
        return parts[0], parts[0]
    return ' '.join(parts[:-1]), parts[-1]


def make_judge(name, court_id, location, retired=False, chief=False, title='HON_JUSTICE'):
    first, last = parse_name(name)
    pk = str(uuid.uuid5(UUID_NS, f'judge:{name}:{court_id}'))
    return {
        "model": "judges.judge",
        "pk": pk,
        "fields": {
            "title": title,
            "first_name": first,
            "last_name": last,
            "other_names": "",
            "court_id": court_id,
            "division_id": None,
            "status": "retired" if retired else "active",
            "email": "",
            "office_location": location,
            "biography": "",
            "appointment_date": None,
            "year_of_call": None,
            "qualifications": [],
            "areas_of_expertise": [],
            "sitting_days": [0, 1, 2, 3, 4],
            "sitting_time_start": "09:00",
            "sitting_time_end": "16:00",
            "is_chief_judge": chief,
            "is_active": not retired,
        }
    }


def build_judges(data_list, court_id, title='HON_JUSTICE'):
    records = []
    seen_pks = set()
    for (name, location, retired, chief) in data_list:
        record = make_judge(name, court_id, location, retired, chief, title)
        if record['pk'] not in seen_pks:
            seen_pks.add(record['pk'])
            records.append(record)
        else:
            print(f'  [skip duplicate] {name}')
    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    with open(FIXTURE_PATH, encoding='utf-8') as f:
        fixture = json.load(f)

    # Split fixture into non-judge / non-new-court records and courts
    existing_court_pks = {
        SC, CA_LAGOS, FHC_LAGOS, FHC_ABUJA, SHC_LAGOS, NIC_LAGOS,
        MC_LAGOS, FCT_HC, CA_ABUJA, NIC_ABUJA,
    }
    new_court_pks = {MC_LAGOS, FCT_HC, CA_ABUJA, NIC_ABUJA}

    base_records = [
        r for r in fixture
        if r['model'] != 'judges.judge'
        and not (r['model'] == 'courts.court' and r['pk'] in new_court_pks)
    ]

    # Build all judge records
    all_judges = []

    print('Building Lagos State High Court judges…')
    all_judges += build_judges(LAGOS_SHC_JUDGES, SHC_LAGOS)

    print('Building Lagos NIC judges…')
    all_judges += build_judges(LAGOS_NIC_JUDGES, NIC_LAGOS)

    print('Building Lagos FHC judges…')
    all_judges += build_judges(LAGOS_FHC_JUDGES, FHC_LAGOS)

    print('Building Lagos Magistrates…')
    all_judges += build_judges(LAGOS_MAGISTRATES, MC_LAGOS, title='HON')

    print('Building FCT High Court judges…')
    all_judges += build_judges(FCT_HC_JUDGES, FCT_HC)

    print('Building FHC Abuja judges…')
    all_judges += build_judges(FHC_ABUJA_JUDGES, FHC_ABUJA)

    print('Building NIC Abuja judges…')
    all_judges += build_judges(NIC_ABUJA_JUDGES, NIC_ABUJA)

    # Assemble final fixture
    output = base_records + NEW_COURTS + all_judges

    with open(FIXTURE_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Summary
    counts = {}
    for r in all_judges:
        cid = r['fields']['court_id']
        counts[cid] = counts.get(cid, 0) + 1

    court_labels = {
        SHC_LAGOS:  'Lagos SHC',
        NIC_LAGOS:  'Lagos NIC',
        FHC_LAGOS:  'Lagos FHC',
        MC_LAGOS:   'Lagos Magistrates',
        FCT_HC:     'FCT High Court',
        FHC_ABUJA:  'FHC Abuja',
        NIC_ABUJA:  'NIC Abuja',
    }
    print()
    print('=== Done ===')
    for cid, label in court_labels.items():
        print(f'  {label}: {counts.get(cid, 0)} judges')
    print(f'  Total judges: {len(all_judges)}')
    print(f'  Total fixture records: {len(output)}')
    print(f'  Written to: {FIXTURE_PATH}')


if __name__ == '__main__':
    main()
