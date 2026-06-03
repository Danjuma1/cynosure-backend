"""
Management command to seed all CSI (Court Sitting Information) data.

Seeds Courts, Panels, Divisions, and Judges from the official judges list
into the database. Idempotent — safe to run multiple times.

Usage:
    python manage.py seed_csi_data
    python manage.py seed_csi_data --reset   # Delete all CSI data first
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.courts.models import Court, Division, Panel
from apps.judges.models import Judge


# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_judge_name(full_name):
    """
    Split 'A.O. Surname' or 'FirstName Surname' into (first_name, last_name).
    Strips credentials (anything after comma) and parentheticals first.
    """
    import re
    name = full_name.split(',')[0].strip()
    name = re.sub(r'\(.*?\)', '', name).strip()
    name = re.sub(r'\s+', ' ', name)
    parts = name.split()
    if len(parts) >= 2:
        return ' '.join(parts[:-1]), parts[-1]
    return name, name


# ── State data ───────────────────────────────────────────────────────────────

ALL_STATES = [
    ('AB', 'Abia',        'Umuahia'),      ('AD', 'Adamawa',      'Yola'),
    ('AK', 'Akwa Ibom',   'Uyo'),          ('AN', 'Anambra',      'Awka'),
    ('BA', 'Bauchi',      'Bauchi'),        ('BY', 'Bayelsa',      'Yenagoa'),
    ('BE', 'Benue',       'Makurdi'),       ('BO', 'Borno',        'Maiduguri'),
    ('CR', 'Cross River', 'Calabar'),       ('DE', 'Delta',        'Asaba'),
    ('EB', 'Ebonyi',      'Abakaliki'),     ('ED', 'Edo',          'Benin City'),
    ('EK', 'Ekiti',       'Ado-Ekiti'),     ('EN', 'Enugu',        'Enugu'),
    ('FC', 'FCT Abuja',   'Abuja'),         ('GO', 'Gombe',        'Gombe'),
    ('IM', 'Imo',         'Owerri'),        ('JI', 'Jigawa',       'Dutse'),
    ('KD', 'Kaduna',      'Kaduna'),        ('KN', 'Kano',         'Kano'),
    ('KT', 'Katsina',     'Katsina'),       ('KE', 'Kebbi',        'Birnin-Kebbi'),
    ('KO', 'Kogi',        'Lokoja'),        ('KW', 'Kwara',        'Ilorin'),
    ('LA', 'Lagos',       'Ikeja'),         ('NA', 'Nasarawa',     'Lafia'),
    ('NI', 'Niger',       'Minna'),         ('OG', 'Ogun',         'Abeokuta'),
    ('ON', 'Ondo',        'Akure'),         ('OS', 'Osun',         'Osogbo'),
    ('OY', 'Oyo',         'Ibadan'),        ('PL', 'Plateau',      'Jos'),
    ('RI', 'Rivers',      'Port Harcourt'), ('SO', 'Sokoto',       'Sokoto'),
    ('TA', 'Taraba',      'Jalingo'),       ('YO', 'Yobe',         'Damaturu'),
    ('ZA', 'Zamfara',     'Gusau'),
]


# ── Court of Appeal data ─────────────────────────────────────────────────────

CA_DATA = [
    {'code': 'CA-ABJ', 'name': 'Court of Appeal — Abuja Division',          'state': 'FC', 'city': 'Abuja',          'address': 'Court of Appeal Complex, Three Arms Zone, Central Business District, Abuja', 'active': True,  'panels': ['Panel 1', 'Panel 2', 'Panel 3', 'Panel 4', 'Panel 5', 'Panel 6', 'Panel 7']},
    {'code': 'CA-LAG', 'name': 'Court of Appeal — Lagos Division',          'state': 'LA', 'city': 'Lagos',          'address': 'Court of Appeal, Ozumba Mbadiwe Avenue, Victoria Island, Lagos',              'active': True,  'panels': ['Panel 1', 'Panel 2', 'Panel 3', 'Panel 4', 'Panel 5']},
    {'code': 'CA-PH',  'name': 'Court of Appeal — Port Harcourt Division',  'state': 'RI', 'city': 'Port Harcourt', 'address': 'Court of Appeal, Aba Road, Port Harcourt, Rivers State',                        'active': False, 'panels': []},
    {'code': 'CA-BEN', 'name': 'Court of Appeal — Benin Division',          'state': 'ED', 'city': 'Benin City',    'active': False, 'panels': []},
    {'code': 'CA-CAL', 'name': 'Court of Appeal — Calabar Division',        'state': 'CR', 'city': 'Calabar',       'active': False, 'panels': []},
    {'code': 'CA-ENU', 'name': 'Court of Appeal — Enugu Division',          'state': 'EN', 'city': 'Enugu',         'active': False, 'panels': []},
    {'code': 'CA-IBA', 'name': 'Court of Appeal — Ibadan Division',         'state': 'OY', 'city': 'Ibadan',        'active': False, 'panels': []},
    {'code': 'CA-ILO', 'name': 'Court of Appeal — Ilorin Division',         'state': 'KW', 'city': 'Ilorin',        'active': False, 'panels': []},
    {'code': 'CA-JOS', 'name': 'Court of Appeal — Jos Division',            'state': 'PL', 'city': 'Jos',           'active': False, 'panels': []},
    {'code': 'CA-KAD', 'name': 'Court of Appeal — Kaduna Division',         'state': 'KD', 'city': 'Kaduna',        'active': False, 'panels': []},
    {'code': 'CA-KAN', 'name': 'Court of Appeal — Kano Division',           'state': 'KN', 'city': 'Kano',          'active': False, 'panels': []},
    {'code': 'CA-MAK', 'name': 'Court of Appeal — Makurdi Division',        'state': 'BE', 'city': 'Makurdi',       'active': False, 'panels': []},
    {'code': 'CA-OWE', 'name': 'Court of Appeal — Owerri Division',         'state': 'IM', 'city': 'Owerri',        'active': False, 'panels': []},
    {'code': 'CA-SOK', 'name': 'Court of Appeal — Sokoto Division',         'state': 'SO', 'city': 'Sokoto',        'active': False, 'panels': []},
    {'code': 'CA-YOL', 'name': 'Court of Appeal — Yola Division',           'state': 'AD', 'city': 'Yola',          'active': False, 'panels': []},
    {'code': 'CA-AKU', 'name': 'Court of Appeal — Akure Division',          'state': 'ON', 'city': 'Akure',         'active': False, 'panels': []},
    {'code': 'CA-ASA', 'name': 'Court of Appeal — Asaba Division',          'state': 'DE', 'city': 'Asaba',         'active': False, 'panels': []},
    {'code': 'CA-AWK', 'name': 'Court of Appeal — Awka Division',           'state': 'AN', 'city': 'Awka',          'active': False, 'panels': []},
    {'code': 'CA-ADO', 'name': 'Court of Appeal — Ado-Ekiti Division',      'state': 'EK', 'city': 'Ado-Ekiti',    'active': False, 'panels': []},
    {'code': 'CA-GOM', 'name': 'Court of Appeal — Gombe Division',          'state': 'GO', 'city': 'Gombe',         'active': False, 'panels': []},
]


# ── Federal High Court data ──────────────────────────────────────────────────
# Format: (name_as_given, is_chief_judge)

FHC_DATA = [
    {'code': 'FHC-ABJ', 'name': 'Federal High Court — Abuja Division',
     'state': 'FC', 'city': 'Abuja',
     'address': 'Federal High Court Complex, Off Shehu Shagari Way, Central Business District, Abuja',
     'active': True,
     'judges': [
         ('John T. Tsoho',                True),
         ('G.K. Olotu',                   False),
         ('B.F.M. Nyako',                 False),
         ('R.N. Ofili-Ajumogobia',        False),
         ('A.R. Mohammed',                False),
         ('I.E. Ekwo',                    False),
         ('D.U. Okorowo',                 False),
         ('Joyce Obehi Abdulmalik',       False),
         ('James Kolawale Omotosho',      False),
         ('Emeka Nwite',                  False),
         ('Obiora Atuegwu Egwuatu',       False),
         ('Mobolaji Olubukola Olajuwon',  False),
         ('Nkeonye Evelyn Maha',          False),
         ('Salim Olasupo Ibrahim',        False),
         ('Onah Chigozie Sergius',        False),
     ]},
    {'code': 'FHC-LAG', 'name': 'Federal High Court — Lagos Division',
     'state': 'LA', 'city': 'Lagos',
     'address': 'No. 1 Sapara Williams Close, off Adeola Hopewell Street, Victoria Island, Lagos',
     'active': True,
     'judges': [
         ('A.O. Faji',                    False),
         ('Musa Kakaki',                  False),
         ('Ogazi Friday Nkemakonam',      False),
         ('Daniel E. Osiagor',            False),
         ('Akintayo Aluko',               False),
         ('A.O. Owoeye',                  False),
         ('C.J. Aneke',                   False),
         ('D.I. Dipeolu',                 False),
         ('Y.S. Bogoro',                  False),
         ('A. Lewis-Allagoa',             False),
         ('I.A. Kala',                    False),
     ]},
    {'code': 'FHC-PH',  'name': 'Federal High Court — Port Harcourt Division', 'state': 'RI', 'city': 'Port Harcourt', 'active': False, 'judges': []},
    {'code': 'FHC-ABA', 'name': 'Federal High Court — Abakaliki Division',     'state': 'EB', 'city': 'Abakaliki',    'active': False, 'judges': []},
    {'code': 'FHC-ABE', 'name': 'Federal High Court — Abeokuta Division',      'state': 'OG', 'city': 'Abeokuta',     'active': False, 'judges': []},
    {'code': 'FHC-ADO', 'name': 'Federal High Court — Ado-Ekiti Division',     'state': 'EK', 'city': 'Ado-Ekiti',   'active': False, 'judges': []},
    {'code': 'FHC-ASA', 'name': 'Federal High Court — Asaba Division',         'state': 'DE', 'city': 'Asaba',        'active': False, 'judges': []},
    {'code': 'FHC-AWK', 'name': 'Federal High Court — Awka Division',          'state': 'AN', 'city': 'Awka',         'active': False, 'judges': []},
    {'code': 'FHC-BAU', 'name': 'Federal High Court — Bauchi Division',        'state': 'BA', 'city': 'Bauchi',       'active': False, 'judges': []},
    {'code': 'FHC-BEN', 'name': 'Federal High Court — Benin Division',         'state': 'ED', 'city': 'Benin City',   'active': False, 'judges': []},
    {'code': 'FHC-CAL', 'name': 'Federal High Court — Calabar Division',       'state': 'CR', 'city': 'Calabar',      'active': False, 'judges': []},
    {'code': 'FHC-ENU', 'name': 'Federal High Court — Enugu Division',         'state': 'EN', 'city': 'Enugu',        'active': False, 'judges': []},
    {'code': 'FHC-GOM', 'name': 'Federal High Court — Gombe Division',         'state': 'GO', 'city': 'Gombe',        'active': False, 'judges': []},
    {'code': 'FHC-IBA', 'name': 'Federal High Court — Ibadan Division',        'state': 'OY', 'city': 'Ibadan',       'active': False, 'judges': []},
    {'code': 'FHC-ILO', 'name': 'Federal High Court — Ilorin Division',        'state': 'KW', 'city': 'Ilorin',       'active': False, 'judges': []},
    {'code': 'FHC-JOS', 'name': 'Federal High Court — Jos Division',           'state': 'PL', 'city': 'Jos',          'active': False, 'judges': []},
    {'code': 'FHC-KAD', 'name': 'Federal High Court — Kaduna Division',        'state': 'KD', 'city': 'Kaduna',       'active': False, 'judges': []},
    {'code': 'FHC-KAN', 'name': 'Federal High Court — Kano Division',          'state': 'KN', 'city': 'Kano',         'active': False, 'judges': []},
    {'code': 'FHC-KAT', 'name': 'Federal High Court — Katsina Division',       'state': 'KT', 'city': 'Katsina',      'active': False, 'judges': []},
    {'code': 'FHC-LAF', 'name': 'Federal High Court — Lafia Division',         'state': 'NA', 'city': 'Lafia',        'active': False, 'judges': []},
    {'code': 'FHC-LOK', 'name': 'Federal High Court — Lokoja Division',        'state': 'KO', 'city': 'Lokoja',       'active': False, 'judges': []},
    {'code': 'FHC-MAI', 'name': 'Federal High Court — Maiduguri Division',     'state': 'BO', 'city': 'Maiduguri',   'active': False, 'judges': []},
    {'code': 'FHC-MAK', 'name': 'Federal High Court — Makurdi Division',       'state': 'BE', 'city': 'Makurdi',      'active': False, 'judges': []},
    {'code': 'FHC-MIN', 'name': 'Federal High Court — Minna Division',         'state': 'NI', 'city': 'Minna',        'active': False, 'judges': []},
    {'code': 'FHC-OSO', 'name': 'Federal High Court — Osogbo Division',        'state': 'OS', 'city': 'Osogbo',       'active': False, 'judges': []},
    {'code': 'FHC-OWE', 'name': 'Federal High Court — Owerri Division',        'state': 'IM', 'city': 'Owerri',       'active': False, 'judges': []},
    {'code': 'FHC-SOK', 'name': 'Federal High Court — Sokoto Division',        'state': 'SO', 'city': 'Sokoto',       'active': False, 'judges': []},
    {'code': 'FHC-UMU', 'name': 'Federal High Court — Umuahia Division',       'state': 'AB', 'city': 'Umuahia',      'active': False, 'judges': []},
    {'code': 'FHC-UYO', 'name': 'Federal High Court — Uyo Division',           'state': 'AK', 'city': 'Uyo',          'active': False, 'judges': []},
    {'code': 'FHC-YEN', 'name': 'Federal High Court — Yenagoa Division',       'state': 'BY', 'city': 'Yenagoa',      'active': False, 'judges': []},
    {'code': 'FHC-YOL', 'name': 'Federal High Court — Yola Division',          'state': 'AD', 'city': 'Yola',         'active': False, 'judges': []},
    {'code': 'FHC-ZAR', 'name': 'Federal High Court — Zaria Division',         'state': 'KD', 'city': 'Zaria',        'active': False, 'judges': []},
    {'code': 'FHC-AKU', 'name': 'Federal High Court — Akure Division',         'state': 'ON', 'city': 'Akure',        'active': False, 'judges': []},
    {'code': 'FHC-BIR', 'name': 'Federal High Court — Birnin-Kebbi Division',  'state': 'KE', 'city': 'Birnin-Kebbi','active': False, 'judges': []},
    {'code': 'FHC-DAM', 'name': 'Federal High Court — Damaturu Division',      'state': 'YO', 'city': 'Damaturu',     'active': False, 'judges': []},
    {'code': 'FHC-DUT', 'name': 'Federal High Court — Dutse Division',         'state': 'JI', 'city': 'Dutse',        'active': False, 'judges': []},
    {'code': 'FHC-GSU', 'name': 'Federal High Court — Gusau Division',         'state': 'ZA', 'city': 'Gusau',        'active': False, 'judges': []},
    {'code': 'FHC-JAL', 'name': 'Federal High Court — Jalingo Division',       'state': 'TA', 'city': 'Jalingo',      'active': False, 'judges': []},
]


# ── National Industrial Court data ───────────────────────────────────────────
# Format: (name_as_given, is_president)

NIC_DATA = [
    {'code': 'NIC-ABJ', 'name': 'National Industrial Court — Abuja Division',
     'state': 'FC', 'city': 'Abuja',
     'address': 'Plot 10, Port Harcourt Crescent, Off Gimbiya Street, Area 11, FCT',
     'phone': '07040101202', 'active': True,
     'judges': [
         ('B.B. Kanyip',          True),   # President NICN
         ('O.A. Obaseki-Osaghae', False),
         ('Z.M. Bashir',          False),
         ('O.O. Arowosegbe',      False),
         ('S.O. Adeniyi',         False),
         ('Kado Sanusi',          False),
         ('John I. Targema',      False),
     ]},
    {'code': 'NIC-LAG', 'name': 'National Industrial Court — Lagos Division',
     'state': 'LA', 'city': 'Lagos',
     'address': '31, Lugard Avenue, Ikoyi, Lagos',
     'phone': '08038690335', 'active': True,
     'judges': [
         ('A.N. Ubaka',         False),
         ('R.B. Gwandu',        False),
         ('S.A. Yelwa',         False),
         ('Joyce A.O. Damachi', False),
         ('I.G. Nweneka',       False),
         ('M.N. Esowe',         False),
         ('E.A. Oji',           False),
         ('I.J. Essien',        False),
     ]},
    {'code': 'NIC-PH',  'name': 'National Industrial Court — Port Harcourt Division', 'state': 'RI', 'city': 'Port Harcourt', 'active': False, 'judges': []},
    {'code': 'NIC-ABA', 'name': 'National Industrial Court — Abakaliki Division',     'state': 'EB', 'city': 'Abakaliki',    'active': False, 'judges': []},
    {'code': 'NIC-ASA', 'name': 'National Industrial Court — Asaba Division',         'state': 'DE', 'city': 'Asaba',        'active': False, 'judges': []},
    {'code': 'NIC-AKU', 'name': 'National Industrial Court — Akure Division',         'state': 'ON', 'city': 'Akure',        'active': False, 'judges': []},
    {'code': 'NIC-BEN', 'name': 'National Industrial Court — Benin Division',         'state': 'ED', 'city': 'Benin City',   'active': False, 'judges': []},
    {'code': 'NIC-CAL', 'name': 'National Industrial Court — Calabar Division',       'state': 'CR', 'city': 'Calabar',      'active': False, 'judges': []},
    {'code': 'NIC-ENU', 'name': 'National Industrial Court — Enugu Division',         'state': 'EN', 'city': 'Enugu',        'active': False, 'judges': []},
    {'code': 'NIC-GOM', 'name': 'National Industrial Court — Gombe Division',         'state': 'GO', 'city': 'Gombe',        'active': False, 'judges': []},
    {'code': 'NIC-IBA', 'name': 'National Industrial Court — Ibadan Division',        'state': 'OY', 'city': 'Ibadan',       'active': False, 'judges': []},
    {'code': 'NIC-ILO', 'name': 'National Industrial Court — Ilorin Division',        'state': 'KW', 'city': 'Ilorin',       'active': False, 'judges': []},
    {'code': 'NIC-JOS', 'name': 'National Industrial Court — Jos Division',           'state': 'PL', 'city': 'Jos',          'active': False, 'judges': []},
    {'code': 'NIC-KAD', 'name': 'National Industrial Court — Kaduna Division',        'state': 'KD', 'city': 'Kaduna',       'active': False, 'judges': []},
    {'code': 'NIC-KAN', 'name': 'National Industrial Court — Kano Division',          'state': 'KN', 'city': 'Kano',         'active': False, 'judges': []},
    {'code': 'NIC-MAI', 'name': 'National Industrial Court — Maiduguri Division',     'state': 'BO', 'city': 'Maiduguri',   'active': False, 'judges': []},
    {'code': 'NIC-MAK', 'name': 'National Industrial Court — Makurdi Division',       'state': 'BE', 'city': 'Makurdi',      'active': False, 'judges': []},
    {'code': 'NIC-MIN', 'name': 'National Industrial Court — Minna Division',         'state': 'NI', 'city': 'Minna',        'active': False, 'judges': []},
    {'code': 'NIC-OWE', 'name': 'National Industrial Court — Owerri Division',        'state': 'IM', 'city': 'Owerri',       'active': False, 'judges': []},
    {'code': 'NIC-SOK', 'name': 'National Industrial Court — Sokoto Division',        'state': 'SO', 'city': 'Sokoto',       'active': False, 'judges': []},
    {'code': 'NIC-UMU', 'name': 'National Industrial Court — Umuahia Division',       'state': 'AB', 'city': 'Umuahia',      'active': False, 'judges': []},
    {'code': 'NIC-UYO', 'name': 'National Industrial Court — Uyo Division',           'state': 'AK', 'city': 'Uyo',          'active': False, 'judges': []},
    {'code': 'NIC-ABE', 'name': 'National Industrial Court — Abeokuta Division',      'state': 'OG', 'city': 'Abeokuta',    'active': False, 'judges': []},
    {'code': 'NIC-LAF', 'name': 'National Industrial Court — Lafia Division',         'state': 'NA', 'city': 'Lafia',        'active': False, 'judges': []},
    {'code': 'NIC-LOK', 'name': 'National Industrial Court — Lokoja Division',        'state': 'KO', 'city': 'Lokoja',       'active': False, 'judges': []},
    {'code': 'NIC-YOL', 'name': 'National Industrial Court — Yola Division',          'state': 'AD', 'city': 'Yola',         'active': False, 'judges': []},
    {'code': 'NIC-ZAR', 'name': 'National Industrial Court — Zaria Division',         'state': 'KD', 'city': 'Zaria',        'active': False, 'judges': []},
]


# ── FCT High Court data (court_type = 'FCT') ─────────────────────────────────
# Format: (name_as_given, location, is_chief_judge, is_retired)

FCT_HC_DATA = {
    'code': 'FCT-HC-ABJ',
    'name': 'High Court of the Federal Capital Territory',
    'state': 'FC',
    'city': 'Abuja',
    'address': 'High Court Complex, Maitama, Abuja, FCT',
    'active': True,
    'judges': [
        ('H.B. Yusuf',           'Court 1, Maitama',    True,  False),
        ('S.C. Oriji',           'Court 2, Maitama',    False, False),
        ('M.E. Anenih',          'Court 3, Maitama',    False, False),
        ('U.P. Kekemeke',        'Court 4, Maitama',    False, False),
        ('M.A. Nasir',           'Court 5, Maitama',    False, False),
        ('O. Agbaza',            'Court 6, Maitama',    False, False),
        ('O.A. Musa',            'Court 7, Maitama',    False, False),
        ('C.N. Oji',             'Court 8, Maitama',    False, False),
        ('S.B. Belgore',         'Court 9, Garki',      False, False),
        ('A.L. Kutigi',          'Court 10, Jabi',      False, False),
        ('A.O. Otaluka',         'Court 11, Apo',       False, False),
        ('A.S. Adepoju',         'Court 12, Gwagwalada',False, False),
        ('Y. Halila',            'Court 13, Maitama',   False, False),
        ('B. Kawu',              'Court 14, Apo',       False, False),
        ('K.N. Ogbonnaya',       'Court 15, Zuba',      False, False),
        ('A.O. Ebong',           'Court 16, Bwari',     False, False),
        ('B. Mohammed',          'Court 17, Apo',       False, False),
        ('M. Osho-Adebiyi',      'Court 18, Gwarinpa',  False, False),
        ('V.S. Gaba',            'Court 19, Kuje',      False, False),
        ('B. Hassan',            'Court 20, Nyaya',     False, False),
        ('A.L. Akobi',           'Court 21, Kubwa',     False, False),
        ('S.U. Bature',          'Court 22, Maitama',   False, False),
        ('E. Okpe',              'Court 23, Gudu',      False, False),
        ("H. Mu'azu",            'Court 24, Maitama',   False, False),
        ('M.S. Idris',           'Court 25, Jabi',      False, False),
        ('O.J. Enobie',          'Court 26, Jabi',      False, False),
        ('B. Abubakar',          'Court 27, Apo',       False, False),
        ('A.H. Musa',            'Court 28, Apo',       False, False),
        ('C.O. Oba',             'Court 29, Apo',       False, False),
        ('J.O. Onwuegbuzie',     'Court 30, Apo',       False, False),
        ('A.A. Fashola',         'Court 31, Jabi',      False, False),
        ('F.E. Messiri',         'Court 32, Jabi',      False, False),
        ('M.A. Hassan',          'Court 33, Gwarinpa',  False, False),
        ('M.M. Adamu',           'Court 34, Gudu',      False, False),
        ('N.C. Nwabulu',         'Court 35, Jikwoyi',   False, False),
        ('C.O. Agashieze',       'Court 36, Lugbe',     False, False),
        ('M.A. Madugu',          'Court 37, Bwari',     False, False),
        ('J.O.E. Adeyemi-Ajayi', 'Court 38, Life Camp', False, False),
        ('O.I. Adelaja',         'Court 39, Kubwa',     False, False),
        ('K. Apunioye',          'Court 40, Gwagwalada',False, False),
        ('A.M. Abdullahi',       'Court 41, Jikwoyi',   False, False),
        ('R.I. Kanyip',          'Court 42, Life Camp', False, False),
        ('S.M. Mayana',          'Court 43, Apo',       False, False),
        ('C.E. Nwecheonwu',      'Court 44, Kuje',      False, False),
        ('A.Y. Shafa',           'Court 45, Nyaya',     False, False),
        ('B. Dogonyaro',         'Court 46, Apo',       False, False),
        ('M. Zubairu',           'Court 47, Jikwoyi',   False, False),
        ('M.A. Katsina-Alu',     'Court 48, Jikwoyi',   False, False),
        ('A.A. Halilu',          'Court 49, Apo',       False, False),
        ('I. Mohammed',          'Court 50, Gwagwalada',False, False),
        ('H.L. Abba-Aliyu',      'Court 51, Jabi',      False, False),
        ('N.K. Nwosu-Iheme',     'Court 52, Wuse Zone 2',False, False),
        ('F.A. Aliyu',           'Court 53, Apo',       False, False),
        ('J.A. Aina',            'Court 54, Gwagwalada',False, False),
        ('B.M. Bassi',           'Court 55, Asokoro',   False, False),
        ('A.O. Oyeyipo',         'Court 56, Jabi',      False, False),
        ('O.O. Bamodu',          'Court 57, Kuje',      False, False),
        ('A. Godwin Iheabunike', 'Court 58, Bwari',     False, False),
        ('Celestine O. Odo',     'Court 59, Kwali',     False, False),
        ('H.L. Gummi',           'Court 60, Asokoro',   False, False),
        ('S.B.L. Avoh',          'Court 61, Jabi',      False, False),
        ('M.I. Yusuf Daibu',     'Court 62, Garki',     False, False),
        ('O.V. Ariwoola',        'Court 63, Wuse Zone 2',False, False),
        ('L.N.B. Wike',          'Court 64, Gwarinpa',  False, False),
        ('M.L. Tanko',           'Court 65, Asokoro',   False, False),
        ('A. Tijani',            'Court 66, Kwali',     False, False),
    ],
}


# ── Lagos State High Court judges (flat list, no divisions required) ──────────
# Format: (name_as_given, location, is_retired)

LAGOS_SHC_JUDGES = [
    ('O.A. Adamson',         'Ikeja',                             False),
    ('M.O. Dawodu',          'Ikeja',                             False),
    ('K.O. Dawodu',          'Commercial Court, Tapa',            False),
    ('E.O. Ogundare',        'Badagry',                           False),
    ('Y.A. Adesanya',        'Taylor Courthouse, Igbosere',       False),
    ('I.O. Harrison',        'Taylor Courthouse, Igbosere',       False),
    ('A.M. Nicol-Clay',      'Ikeja',                             False),
    ('S.I. Sonaike',         'Taylor Courthouse, Igbosere',       False),
    ('A.J. Coker',           'Ikeja',                             False),
    ('O.O.A. Fadipe',        'Ikeja',                             False),
    ('I.O. Ijelu',           'Ikeja',                             False),
    ('O.A. Ogala',           'Ikeja',                             False),
    ('H.O. Oshodi',          'Ikeja',                             False),
    ('F.A. Azeez',           'Ikeja',                             False),
    ('W.A. Animahun',        'Epe',                               False),
    ('S.A. Olaitan',         'Epe',                               False),
    ('W. Animahun',          'Epe',                               False),
    ('M.O. Obadina',         'Ikeja',                             False),
    ('C.A. Balogun',         'Ikeja',                             True),
    ('A.A. Oyebanji',        'Taylor Courthouse, Igbosere',       False),
    ('M.M. Balogun',         'Sabo/Yaba, Surulere',               False),
    ('O.I. Oguntade',        'Old Secretariat Courthouse, Ikeja', False),
    ('O.J. Awope',           'Ikeja',                             False),
    ('A.O. Adeyemi',         'Ikeja',                             False),
    ('A.A. Akintoye',        'Ikeja',                             True),
    ('A.M. Ipaye-Nwachukwu', 'Ikeja',                             False),
    ('K.A. Jose',            'Commercial Court, Tapa',            False),
    ('L.A. Okunnu',          'Commercial Court, Tapa',            False),
    ('R.O. Olukolu',         'Commercial Court, Tapa',            False),
    ('O.O. Pedro',           'Commercial Court, Tapa',            False),
    ('K.O. Alogba',          'Ikeja',                             False),
    ('O.O. Adewunmi-Oshin',  'Osborn Foreshore',                  False),
    ('L.A.M. Folami',        'T.B.S, Lagos',                      False),
    ('O.A. Ipaye',           'Osborn Foreshore',                  False),
    ('L.B. Lawal-Akapo',     'Ikeja',                             True),
    ('B.O. Kalaro',          'Alausa CBD Courthouse, Ikeja',      False),
    ('D.T. Olatokun',        'Ikeja',                             False),
    ('L.A.F. Oluyemi',       'Ikeja',                             False),
    ('Y.R. Pinheiro',        'Ikeja',                             False),
    ('F.O. Aigbokaevbo',     'Ajah',                              False),
    ('I.E. Alakija',         'Taylor Courthouse, Igbosere',       False),
    ('O.O. Ogungbesan',      'Taylor Courthouse, Igbosere',       False),
    ('A.O. Opesanwo',        'Osborn Foreshore',                  False),
    ('O.A. Oresanya',        'Ikeja',                             False),
    ('J.E. Oyefeso',         'Ajah',                              False),
    ('T.A.O. Oyekan-Abdullai','Ikeja',                            True),
    ('G.A. Safari',          'Eti-Osa',                           False),
    ('O. Sule-Amzat',        'Sabo/Yaba, Surulere',               False),
    ('A.J. Bashua',          'Sabo/Yaba, Surulere',               False),
    ('I.O. Akinkugbe',       'Ikorodu',                           False),
    ('M.I. Oshodi',          'Ikorodu',                           False),
    ('A.F. Pokanu',          'Ikorodu',                           False),
    ('O.O. Martins',         'Osborn Foreshore',                  False),
    ('O.A. Akinlade',        'Osborn Foreshore',                  False),
    ('E.O. Ashade',          'Sabo/Yaba, Surulere',               False),
    ('O.O. Ogunjobi',        'Taylor Courthouse, Igbosere',       False),
    ('R.I.B. Adebiyi',       'Ikeja',                             False),
    ('A.M. Lawal',           'Ikeja',                             False),
    ('O.A. Odunsanya',       'Ikeja',                             False),
    ('S.S. Ogunsanya',       'Ikeja',                             False),
    ('Y.G. Oshoala',         'Old Secretariat Courthouse, Ikeja', False),
    ('A.O. Idowu',           'Old Secretariat Courthouse, Ikeja', False),
    ('M.A. Savage',          'Ikeja',                             False),
    ('A.A. George',          'Osborn Foreshore',                  False),
    ('Y.J. Badejo-Okusanya', 'Osborn Foreshore',                  False),
    ('N.O.O. Ojuromi',       'Osborn Foreshore',                  False),
    ('O.A. Okunuga',         'Ikeja',                             False),
    ('A.K. Shonubi',         'Ikeja',                             False),
    ('O.A. Layinka',         'Ikeja',                             False),
    ('T.B. Sunmonu',         'Commercial Court, Tapa',            False),
    ('R.M. Adewale',         'Roseline O. Courthouse, Ikeja',     False),
    ('A.G. Balogun',         'Roseline O. Courthouse, Ikeja',     False),
    ('T.A. Anjorin-Ajose',   'Commercial Court, Tapa',            False),
    ('O.L. Alebiosu',        'Ikeja',                             False),
    ('A.T. Muyideen',        'Taylor Courthouse, Igbosere',       False),
    ('O.A. Popoola',         'Ikeja',                             False),
    ('A.O. Soladoye',        'Ikeja',                             False),
    ('M.A. Dada',            'Ikeja',                             False),
    ('R.A. Oshodi',          'Roseline O. Courthouse, Ikeja',     False),
]


# ── Lagos Magistrates (rows 3-152 of the official list; rows 1-2 are registrar staff) ──
# Format: (name_as_given, is_chief_magistrate)

LAGOS_MAGISTRATES = [
    ('P.A. Ojo',              True),   ('Y.O. Aje-Afunwa',       True),
    ('A.O. Adedayo',          True),   ('O.I. Adelaja',          False),
    ('A.A. Oshoniyi',         False),  ('O.O. Oshin',            False),
    ('F.O. Aigbokhaevbo',     False),  ('F.A. Azeez',            False),
    ('A. Ipaye-Nwachukwu',    False),  ('T.A. Elias',            False),
    ('O.J. Awope',            False),  ('A.K. Shonubi',          False),
    ('T.O. Shomade',          False),  ('A.F.O. Botoku',         False),
    ('K.B. Ayeye',            False),  ('A.M. Alli-Balogun',     False),
    ('B.O. Osunsanmi',        False),  ('A.O. Komolafe',         False),
    ('O.I. Oguntade',         False),  ('O.O. Martins',          False),
    ('Y.J. Badejo-Okusanya',  False),  ('R.O. Davies',           False),
    ('A.O. Layinka',          False),  ('O. Sule-Amzat',         False),
    ('O.O. Olatunji',         False),  ('E.O. Ogunkanmi',        False),
    ('F.M. Kayode-Alamu',     False),  ('B.A. Sonuga',           False),
    ('T. Akanni',             False),  ('O.A. Adegbite',         False),
    ('P.A. Adekomaiya',       False),  ('M.K.O. Fadeyi',         False),
    ('W.B. Balogun',          False),  ('J.O.E. Adeyemi',        False),
    ('M. Owumi',              False),  ('A.A. Paul',             False),
    ('O.A. Komolafe',         False),  ('K.O. Doja-Ojo',         False),
    ('C.J. Momodu',           False),  ('A.O. Ajibade',          False),
    ('A.O. Gbajumo',          False),  ('O.G. Oghre',            False),
    ('O.A. Akinde',           False),  ('H.O.A. Amos',           False),
    ('O. Kusanu',             False),  ('P.E. Nwaka',            False),
    ('A.B. Olagbegi-Adelabu', False),  ('H.O. Omisore',          False),
    ('A.M. Olumide-Fusika',   False),  ('F.J. Adefioye',         False),
    ('E. Kubeinje',           False),  ('O.O.A. Fowowe-Erusiafe',False),
    ('O.A. Aka-Bashorun',     False),  ('G.L. Hotepo',           False),
    ('J.A. Adegun',           False),  ('A.T. Omoyele',          False),
    ('M.I. Dan-Oni',          False),  ('A.S. Odusanya',         False),
    ('S.K. Matepo',           False),  ('M.O. Olubi',            False),
    ('M.O. Tanimola',         False),  ('O.M. Ajayi',            False),
    ('K.O. Ogundare',         False),  ('J. Ugbomoiko',          False),
    ('A.O. Oshodi-Makanju',   False),  ('A.A. Fashola',          False),
    ('L.Y. Balogun',          False),  ('B.O. Ope-Agbe',         False),
    ('B. Folarin-Williams',   False),  ('A.A. Adesanya',         False),
    ('A.O. Onilogbo',         False),  ('A.A. Famobiwo',         False),
    ('L.A. Owolabi',          False),  ('F.F. George',           False),
    ('K.A. Ariyo',            False),  ('O.A. Olagbende',        False),
    ('A.M. Davies',           False),  ('M.O. Osinbajo',         False),
    ('O.A. Erinle',           False),  ('O.O. Ojuromi',          False),
    ('F. Dalley',             False),  ('N.A. Layeni',           False),
    ('G.O. Anifowoshe',       False),  ('I.O. Alaka',            False),
    ('T.O. Babalola',         False),  ('O.O. Otitoju',          False),
    ('O.A. Akokhia',          False),  ('Y.O. Ekogbulu',         False),
    ('A.A. Gbajumo-Ayoku',    False),  ('A.A. Adetunji',         False),
    ('B.I. Bakare',           False),  ('F. Ikobayo',            False),
    ('T.A. Idowu',            False),  ('O.A. Salawu',           False),
    ('L.O. Kazeem',           False),  ('T.O. Abayomi',          False),
    ('O.I. Raji',             False),  ('K.S. Abdul-Salam',      False),
    ('A.O. Ogbe',             False),  ('Y.O. Aro-Lambo',        False),
    ('M.B. Amore',            False),  ('O.A. Odunayo',          False),
    ('A.S. Okubule',          False),  ('O.S. Abioye',           False),
    ('A.K. Tella',            False),  ('T.A. Ojo',              False),
    ('A.K. Dosunmu',          False),  ('I.A. Abina',            False),
    ('K.J. Layeni',           False),  ('R.A. Oladele',          False),
    ('W.A. Salami',           False),  ('M.F. Onamusi',          False),
    ('O.A. Ogunjobi',         False),  ('T. Anjorin-Ajose',      False),
    ('O.O. Akingbesote',      False),  ('O.O. Adeshina',         False),
    ('T.F. Oyaniyi',          False),  ('O.C. Emeka-Opara',      False),
    ('C.K. Tunji-Carrena',    False),  ('K.K. Awoyinka',         False),
    ('O.A. Aderibigbe',       False),  ('S.A. Grillo',           False),
    ('S.O. Obasa',            False),  ('F.A. Shittabey',        False),
    ('O.O. Fajana',           False),  ('T.B. Are',              False),
    ('O.O. Ekundayo',         False),  ('F.O. Sasanya',          False),
    ('A.B. Ajiferuke',        False),  ('O. Isreal-Adelakun',    False),
    ('M.A. Agbaje',           False),  ('T.J. Agbona',           False),
    ('A.O. Olorunfemi',       False),  ('O.R. Williams-Isichei', False),
    ('R.I. Ayilara',          False),  ('O.A. Daodu',            False),
    ('F.D. Hughes',           False),  ('M.O. Kadiri',           False),
    ('H.B. Mogaji',           False),  ('A.A. Runsewe',          False),
    ('T.R. Shekoni-Adeyekun', False),  ('O.O. Fagbohun',         False),
    ('A.R. Morafa',           False),  ('M.C. Ayinde',           False),
    ('M.O. Dawodu',           False),  ('R.E. Ojudun',           False),
    ('A.O. Alogba',           False),  ('O.D. Njoku',            False),
    ('T.A. Popoola',          False),  ('G.O. Tiamiyu',          False),
]


# ── Command ───────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Seed CSI court data (courts, panels, divisions, judges) from the official judges list'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete all existing judges and courts before seeding (CAUTION: also removes cause lists)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('Deleting all CSI data...'))
            Judge.objects.all().delete()
            Court.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Deleted.'))

        self.stdout.write('Seeding Court of Appeal courts...')
        self._seed_ca()

        self.stdout.write('Seeding Federal High Court courts...')
        self._seed_fhc()

        self.stdout.write('Seeding National Industrial Court courts...')
        self._seed_nic()

        self.stdout.write('Seeding FCT High Court...')
        self._seed_fct_hc()

        self.stdout.write('Seeding State High Courts...')
        self._seed_shc()

        self.stdout.write('Seeding Magistrate Courts...')
        self._seed_mc()

        self.stdout.write(self.style.SUCCESS('\nCSI data seeding complete!'))
        self._print_summary()

    # ── CA ────────────────────────────────────────────────────────────────────

    def _seed_ca(self):
        for d in CA_DATA:
            court, created = Court.objects.update_or_create(
                code=d['code'],
                defaults={
                    'name': d['name'], 'court_type': 'CA',
                    'state': d['state'], 'city': d.get('city', ''),
                    'address': d.get('address', ''), 'is_active': d['active'],
                }
            )
            self.stdout.write(f"  CA {'created' if created else 'updated'}: {court.name}")

            for panel_name in d.get('panels', []):
                panel_code = f"{d['code']}-{panel_name.replace(' ', '-').upper()}"
                panel, p_created = Panel.objects.update_or_create(
                    court=court, code=panel_code,
                    defaults={'name': panel_name, 'is_active': True}
                )
                self.stdout.write(f"    Panel {'created' if p_created else 'ok'}: {panel_name}")

    # ── FHC ───────────────────────────────────────────────────────────────────

    def _seed_fhc(self):
        for d in FHC_DATA:
            court, created = Court.objects.update_or_create(
                code=d['code'],
                defaults={
                    'name': d['name'], 'court_type': 'FHC',
                    'state': d['state'], 'city': d.get('city', ''),
                    'address': d.get('address', ''), 'is_active': d['active'],
                }
            )
            self.stdout.write(f"  FHC {'created' if created else 'updated'}: {court.name}")

            # Delete stale judges for this court before re-seeding
            if d.get('judges'):
                Judge.objects.filter(court=court).delete()

            for name, is_chief in d.get('judges', []):
                first, last = parse_judge_name(name)
                title = 'CHIEF_JUDGE' if is_chief else 'HON_JUSTICE'
                Judge.objects.create(
                    court=court, first_name=first, last_name=last,
                    title=title, is_chief_judge=is_chief,
                    status='active', is_active=True,
                )
                self.stdout.write(f'    Judge: {first} {last}')

    # ── NIC ───────────────────────────────────────────────────────────────────

    def _seed_nic(self):
        for d in NIC_DATA:
            court, created = Court.objects.update_or_create(
                code=d['code'],
                defaults={
                    'name': d['name'], 'court_type': 'NIC',
                    'state': d['state'], 'city': d.get('city', ''),
                    'address': d.get('address', ''), 'is_active': d['active'],
                }
            )
            self.stdout.write(f"  NIC {'created' if created else 'updated'}: {court.name}")

            if d.get('judges'):
                Judge.objects.filter(court=court).delete()

            for name, is_president in d.get('judges', []):
                first, last = parse_judge_name(name)
                title = 'PRESIDENT' if is_president else 'HON_JUSTICE'
                Judge.objects.create(
                    court=court, first_name=first, last_name=last,
                    title=title, is_chief_judge=is_president,
                    status='active', is_active=True,
                )
                self.stdout.write(f'    Judge: {first} {last}')

    # ── FCT High Court ────────────────────────────────────────────────────────

    def _seed_fct_hc(self):
        d = FCT_HC_DATA
        court, created = Court.objects.update_or_create(
            code=d['code'],
            defaults={
                'name': d['name'], 'court_type': 'FCT',
                'state': d['state'], 'city': d['city'],
                'address': d['address'], 'is_active': d['active'],
            }
        )
        self.stdout.write(f"  FCT HC {'created' if created else 'updated'}: {court.name}")

        Judge.objects.filter(court=court).delete()

        for name, location, is_chief, is_retired in d['judges']:
            first, last = parse_judge_name(name)
            Judge.objects.create(
                court=court, first_name=first, last_name=last,
                title='CHIEF_JUDGE' if is_chief else 'HON_JUSTICE',
                is_chief_judge=is_chief,
                office_location=location,
                status='retired' if is_retired else 'active',
                is_active=not is_retired,
            )
            self.stdout.write(f'    Judge: {first} {last} — {location}')

    # ── State High Courts ─────────────────────────────────────────────────────

    def _seed_shc(self):
        # Lagos and FCT are active; Rivers is locked
        active_states = {'LA', 'FC'}
        for state_code, state_name, capital in ALL_STATES:
            code = f'SHC-{state_code}'
            name = 'FCT High Court' if state_code == 'FC' else f'{state_name} State High Court'

            court, created = Court.objects.update_or_create(
                code=code,
                defaults={
                    'name': name, 'court_type': 'SHC',
                    'state': state_code, 'city': capital,
                    'is_active': state_code in active_states,
                }
            )
            self.stdout.write(f"  SHC {'created' if created else 'updated'}: {court.name}")

            if state_code == 'LA':
                self._seed_shc_judges_flat(court, LAGOS_SHC_JUDGES)

    def _seed_shc_judges_flat(self, court, judges_data):
        """Seed SHC judges directly under the court (no division — matches frontend flow)."""
        Judge.objects.filter(court=court).delete()
        seen = set()
        for name, location, is_retired in judges_data:
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            first, last = parse_judge_name(name)
            Judge.objects.create(
                court=court, first_name=first, last_name=last,
                title='HON_JUSTICE',
                office_location=location,
                status='retired' if is_retired else 'active',
                is_active=not is_retired,
            )
            self.stdout.write(f'    Judge: {first} {last} — {location}')

    # ── Magistrate Courts ─────────────────────────────────────────────────────

    def _seed_mc(self):
        # Lagos and FCT are active; Rivers is locked
        active_states = {'LA', 'FC'}
        for state_code, state_name, capital in ALL_STATES:
            code = f'MC-{state_code}'
            name = f'{state_name} Magistrate Court'

            court, created = Court.objects.update_or_create(
                code=code,
                defaults={
                    'name': name, 'court_type': 'MC',
                    'state': state_code, 'city': capital,
                    'is_active': state_code in active_states,
                }
            )
            self.stdout.write(f"  MC {'created' if created else 'updated'}: {court.name}")

            if state_code == 'LA':
                self._seed_magistrates_flat(court, LAGOS_MAGISTRATES)

    def _seed_magistrates_flat(self, court, magistrates_data):
        """Seed magistrates directly under the court (no division — matches frontend flow)."""
        Judge.objects.filter(court=court).delete()
        for name, is_chief in magistrates_data:
            first, last = parse_judge_name(name)
            Judge.objects.create(
                court=court, first_name=first, last_name=last,
                title='HON_JUSTICE',
                is_chief_judge=is_chief,
                status='active', is_active=True,
            )
        self.stdout.write(f'    Seeded {len(magistrates_data)} magistrates')

    # ── Summary ───────────────────────────────────────────────────────────────

    def _print_summary(self):
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('Summary:')
        for ct, label in [
            ('CA',  'Court of Appeal'),
            ('FHC', 'Federal High Court'),
            ('NIC', 'National Industrial Court'),
            ('FCT', 'FCT High Court'),
            ('SHC', 'State High Court'),
            ('MC',  'Magistrate Court'),
        ]:
            total  = Court.objects.filter(court_type=ct).count()
            active = Court.objects.filter(court_type=ct, is_active=True).count()
            judges = Judge.objects.filter(court__court_type=ct).count()
            self.stdout.write(f'  {label}: {total} courts ({active} active), {judges} judges')
        self.stdout.write(f'  Panels total:    {Panel.objects.count()}')
        self.stdout.write(f'  Divisions total: {Division.objects.count()}')
        self.stdout.write(f'  Judges total:    {Judge.objects.count()}')
        self.stdout.write('=' * 50)
