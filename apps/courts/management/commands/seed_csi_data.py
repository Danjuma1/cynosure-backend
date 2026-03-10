"""
Management command to seed all CSI (Court Sitting Information) data.

Seeds Courts, Panels, Divisions, and Judges from the static frontend data
into the database. Idempotent — safe to run multiple times.

Usage:
    python manage.py seed_csi_data
    python manage.py seed_csi_data --reset   # Delete all CSI data first
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.courts.models import Court, Division, Panel
from apps.judges.models import Judge


# ── State code mapping ───────────────────────────────────────────────────────

STATE_CODE_MAP = {
    'FCT Abuja': 'FC', 'Lagos': 'LA', 'Rivers': 'RI', 'Ebonyi': 'EB',
    'Delta': 'DE', 'Ondo': 'ON', 'Akwa Ibom': 'AK', 'Anambra': 'AN',
    'Bauchi': 'BA', 'Bayelsa': 'BY', 'Benue': 'BE', 'Borno': 'BO',
    'Cross River': 'CR', 'Edo': 'ED', 'Ekiti': 'EK', 'Enugu': 'EN',
    'Gombe': 'GO', 'Imo': 'IM', 'Jigawa': 'JI', 'Kaduna': 'KD',
    'Kano': 'KN', 'Katsina': 'KT', 'Kebbi': 'KE', 'Kogi': 'KO',
    'Kwara': 'KW', 'Nasarawa': 'NA', 'Niger': 'NI', 'Ogun': 'OG',
    'Osun': 'OS', 'Oyo': 'OY', 'Plateau': 'PL', 'Sokoto': 'SO',
    'Taraba': 'TA', 'Yobe': 'YO', 'Zamfara': 'ZA', 'Abia': 'AB',
    'Adamawa': 'AD',
}

ALL_STATES = [
    ('AB', 'Abia', 'Umuahia'),
    ('AD', 'Adamawa', 'Yola'),
    ('AK', 'Akwa Ibom', 'Uyo'),
    ('AN', 'Anambra', 'Awka'),
    ('BA', 'Bauchi', 'Bauchi'),
    ('BY', 'Bayelsa', 'Yenagoa'),
    ('BE', 'Benue', 'Makurdi'),
    ('BO', 'Borno', 'Maiduguri'),
    ('CR', 'Cross River', 'Calabar'),
    ('DE', 'Delta', 'Asaba'),
    ('EB', 'Ebonyi', 'Abakaliki'),
    ('ED', 'Edo', 'Benin City'),
    ('EK', 'Ekiti', 'Ado-Ekiti'),
    ('EN', 'Enugu', 'Enugu'),
    ('FC', 'FCT Abuja', 'Abuja'),
    ('GO', 'Gombe', 'Gombe'),
    ('IM', 'Imo', 'Owerri'),
    ('JI', 'Jigawa', 'Dutse'),
    ('KD', 'Kaduna', 'Kaduna'),
    ('KN', 'Kano', 'Kano'),
    ('KT', 'Katsina', 'Katsina'),
    ('KE', 'Kebbi', 'Birnin-Kebbi'),
    ('KO', 'Kogi', 'Lokoja'),
    ('KW', 'Kwara', 'Ilorin'),
    ('LA', 'Lagos', 'Ikeja'),
    ('NA', 'Nasarawa', 'Lafia'),
    ('NI', 'Niger', 'Minna'),
    ('OG', 'Ogun', 'Abeokuta'),
    ('ON', 'Ondo', 'Akure'),
    ('OS', 'Osun', 'Osogbo'),
    ('OY', 'Oyo', 'Ibadan'),
    ('PL', 'Plateau', 'Jos'),
    ('RI', 'Rivers', 'Port Harcourt'),
    ('SO', 'Sokoto', 'Sokoto'),
    ('TA', 'Taraba', 'Jalingo'),
    ('YO', 'Yobe', 'Damaturu'),
    ('ZA', 'Zamfara', 'Gusau'),
]


# ── Source data (mirrors frontend static files) ──────────────────────────────

CA_DATA = [
    {'code': 'CA-ABJ', 'name': 'Court of Appeal — Abuja Division', 'state': 'FC',
     'city': 'Abuja', 'address': 'Court of Appeal Complex, Three Arms Zone, Central Business District, Abuja',
     'active': True, 'panels': ['Panel 1', 'Panel 2', 'Panel 3', 'Panel 4', 'Panel 5']},
    {'code': 'CA-LAG', 'name': 'Court of Appeal — Lagos Division', 'state': 'LA',
     'city': 'Lagos', 'address': 'Court of Appeal, Ozumba Mbadiwe Avenue, Victoria Island, Lagos',
     'active': True, 'panels': ['Panel 1', 'Panel 2', 'Panel 3', 'Panel 4', 'Panel 5']},
    {'code': 'CA-PH', 'name': 'Court of Appeal — Port Harcourt Division', 'state': 'RI',
     'city': 'Port Harcourt', 'address': 'Court of Appeal, Aba Road, Port Harcourt, Rivers State',
     'active': True, 'panels': ['Panel 1', 'Panel 2', 'Panel 3']},
    {'code': 'CA-BEN', 'name': 'Court of Appeal — Benin Division',     'state': 'ED', 'city': 'Benin City',    'active': False, 'panels': []},
    {'code': 'CA-CAL', 'name': 'Court of Appeal — Calabar Division',   'state': 'CR', 'city': 'Calabar',       'active': False, 'panels': []},
    {'code': 'CA-ENU', 'name': 'Court of Appeal — Enugu Division',     'state': 'EN', 'city': 'Enugu',         'active': False, 'panels': []},
    {'code': 'CA-IBA', 'name': 'Court of Appeal — Ibadan Division',    'state': 'OY', 'city': 'Ibadan',        'active': False, 'panels': []},
    {'code': 'CA-ILO', 'name': 'Court of Appeal — Ilorin Division',    'state': 'KW', 'city': 'Ilorin',        'active': False, 'panels': []},
    {'code': 'CA-JOS', 'name': 'Court of Appeal — Jos Division',       'state': 'PL', 'city': 'Jos',           'active': False, 'panels': []},
    {'code': 'CA-KAD', 'name': 'Court of Appeal — Kaduna Division',    'state': 'KD', 'city': 'Kaduna',        'active': False, 'panels': []},
    {'code': 'CA-KAN', 'name': 'Court of Appeal — Kano Division',      'state': 'KN', 'city': 'Kano',          'active': False, 'panels': []},
    {'code': 'CA-MAK', 'name': 'Court of Appeal — Makurdi Division',   'state': 'BE', 'city': 'Makurdi',       'active': False, 'panels': []},
    {'code': 'CA-OWE', 'name': 'Court of Appeal — Owerri Division',    'state': 'IM', 'city': 'Owerri',        'active': False, 'panels': []},
    {'code': 'CA-SOK', 'name': 'Court of Appeal — Sokoto Division',    'state': 'SO', 'city': 'Sokoto',        'active': False, 'panels': []},
    {'code': 'CA-YOL', 'name': 'Court of Appeal — Yola Division',      'state': 'AD', 'city': 'Yola',          'active': False, 'panels': []},
    {'code': 'CA-AKU', 'name': 'Court of Appeal — Akure Division',     'state': 'ON', 'city': 'Akure',         'active': False, 'panels': []},
    {'code': 'CA-ASA', 'name': 'Court of Appeal — Asaba Division',     'state': 'DE', 'city': 'Asaba',         'active': False, 'panels': []},
    {'code': 'CA-AWK', 'name': 'Court of Appeal — Awka Division',      'state': 'AN', 'city': 'Awka',          'active': False, 'panels': []},
    {'code': 'CA-ADO', 'name': 'Court of Appeal — Ado-Ekiti Division', 'state': 'EK', 'city': 'Ado-Ekiti',     'active': False, 'panels': []},
    {'code': 'CA-GOM', 'name': 'Court of Appeal — Gombe Division',     'state': 'GO', 'city': 'Gombe',         'active': False, 'panels': []},
]

FHC_DATA = [
    {'code': 'FHC-ABJ', 'name': 'Federal High Court — Abuja Division', 'state': 'FC',
     'city': 'Abuja', 'address': 'Federal High Court Complex, Off Shehu Shagari Way, Central Business District, Abuja',
     'active': True,
     'judges': [
         ('J.T. Tsoho', 'Chief Judge'),
         ('G.K. Olotu', None), ('B.F.M. Nyako', None), ('R.N. Ofili-Ajumogobia', None),
         ('A.R. Mohammed', None), ('I.E. Ekwo', None), ('D.U. Okorowo', None),
         ('Joyce Obehi Abdulmalik', None), ('James Kolawale Omotosho', None),
         ('Emeka Nwite', None), ('Obiora Atuegwu Egwuatu', None),
         ('Mobolaji Olubukola Olajuwon', None), ('Nkeonye Evelyn Maha', None),
     ]},
    {'code': 'FHC-LAG', 'name': 'Federal High Court — Lagos Division', 'state': 'LA',
     'city': 'Lagos', 'address': 'No. 1 Sapara Williams Close, off Adeola Hopewell Street, Victoria Island, Lagos',
     'active': True,
     'judges': [
         ('J.T. Tsoho', 'Chief Judge'),
         ('A.O. Faji', None), ('A. Lewis-Allagoa', None), ('C.J. Aneke', None),
         ('Yellim S. Bogoro', None), ('Daniel Emeka Osiagor', None), ('Akintayo Aluko', None),
         ('Peter Odo Lifu', None), ('Abimbola O. Awogboro', None),
         ('Dipeolu Deinde Isaac', None), ('Ogundare Kehinde Olayiwola', None),
         ('Ibrahim Ahmad Kala', None), ('Ogazi Friday Nkemakonam', None),
     ]},
    {'code': 'FHC-PH', 'name': 'Federal High Court — Port Harcourt Division', 'state': 'RI',
     'city': 'Port Harcourt', 'address': 'Federal High Court, Aba Road, Port Harcourt, Rivers State',
     'active': True,
     'judges': [
         ('P.I. Ajoku', None), ('E.A. Obile', None), ('Pheobe Msuen Ayua', None),
         ('Stephen Daylop Pam', None), ('Adamu Turaki Mohammed', None),
         ("Sa'adatu Ibrahim Mark", None),
     ]},
    {'code': 'FHC-ABA', 'name': 'Federal High Court — Abakaliki Division',  'state': 'EB', 'city': 'Abakaliki',   'active': False, 'judges': []},
    {'code': 'FHC-ABE', 'name': 'Federal High Court — Abeokuta Division',   'state': 'OG', 'city': 'Abeokuta',    'active': False, 'judges': []},
    {'code': 'FHC-ADO', 'name': 'Federal High Court — Ado-Ekiti Division',  'state': 'EK', 'city': 'Ado-Ekiti',   'active': False, 'judges': []},
    {'code': 'FHC-ASA', 'name': 'Federal High Court — Asaba Division',      'state': 'DE', 'city': 'Asaba',        'active': False, 'judges': []},
    {'code': 'FHC-AWK', 'name': 'Federal High Court — Awka Division',       'state': 'AN', 'city': 'Awka',         'active': False, 'judges': []},
    {'code': 'FHC-BAU', 'name': 'Federal High Court — Bauchi Division',     'state': 'BA', 'city': 'Bauchi',       'active': False, 'judges': []},
    {'code': 'FHC-BEN', 'name': 'Federal High Court — Benin Division',      'state': 'ED', 'city': 'Benin City',   'active': False, 'judges': []},
    {'code': 'FHC-CAL', 'name': 'Federal High Court — Calabar Division',    'state': 'CR', 'city': 'Calabar',      'active': False, 'judges': []},
    {'code': 'FHC-ENU', 'name': 'Federal High Court — Enugu Division',      'state': 'EN', 'city': 'Enugu',        'active': False, 'judges': []},
    {'code': 'FHC-GOM', 'name': 'Federal High Court — Gombe Division',      'state': 'GO', 'city': 'Gombe',        'active': False, 'judges': []},
    {'code': 'FHC-IBA', 'name': 'Federal High Court — Ibadan Division',     'state': 'OY', 'city': 'Ibadan',       'active': False, 'judges': []},
    {'code': 'FHC-ILO', 'name': 'Federal High Court — Ilorin Division',     'state': 'KW', 'city': 'Ilorin',       'active': False, 'judges': []},
    {'code': 'FHC-JOS', 'name': 'Federal High Court — Jos Division',        'state': 'PL', 'city': 'Jos',          'active': False, 'judges': []},
    {'code': 'FHC-KAD', 'name': 'Federal High Court — Kaduna Division',     'state': 'KD', 'city': 'Kaduna',       'active': False, 'judges': []},
    {'code': 'FHC-KAN', 'name': 'Federal High Court — Kano Division',       'state': 'KN', 'city': 'Kano',         'active': False, 'judges': []},
    {'code': 'FHC-KAT', 'name': 'Federal High Court — Katsina Division',    'state': 'KT', 'city': 'Katsina',      'active': False, 'judges': []},
    {'code': 'FHC-LAF', 'name': 'Federal High Court — Lafia Division',      'state': 'NA', 'city': 'Lafia',        'active': False, 'judges': []},
    {'code': 'FHC-LOK', 'name': 'Federal High Court — Lokoja Division',     'state': 'KO', 'city': 'Lokoja',       'active': False, 'judges': []},
    {'code': 'FHC-MAI', 'name': 'Federal High Court — Maiduguri Division',  'state': 'BO', 'city': 'Maiduguri',    'active': False, 'judges': []},
    {'code': 'FHC-MAK', 'name': 'Federal High Court — Makurdi Division',    'state': 'BE', 'city': 'Makurdi',      'active': False, 'judges': []},
    {'code': 'FHC-MIN', 'name': 'Federal High Court — Minna Division',      'state': 'NI', 'city': 'Minna',        'active': False, 'judges': []},
    {'code': 'FHC-OSO', 'name': 'Federal High Court — Osogbo Division',     'state': 'OS', 'city': 'Osogbo',       'active': False, 'judges': []},
    {'code': 'FHC-OWE', 'name': 'Federal High Court — Owerri Division',     'state': 'IM', 'city': 'Owerri',       'active': False, 'judges': []},
    {'code': 'FHC-SOK', 'name': 'Federal High Court — Sokoto Division',     'state': 'SO', 'city': 'Sokoto',       'active': False, 'judges': []},
    {'code': 'FHC-UMU', 'name': 'Federal High Court — Umuahia Division',    'state': 'AB', 'city': 'Umuahia',      'active': False, 'judges': []},
    {'code': 'FHC-UYO', 'name': 'Federal High Court — Uyo Division',        'state': 'AK', 'city': 'Uyo',          'active': False, 'judges': []},
    {'code': 'FHC-YEN', 'name': 'Federal High Court — Yenagoa Division',    'state': 'BY', 'city': 'Yenagoa',      'active': False, 'judges': []},
    {'code': 'FHC-YOL', 'name': 'Federal High Court — Yola Division',       'state': 'AD', 'city': 'Yola',         'active': False, 'judges': []},
    {'code': 'FHC-ZAR', 'name': 'Federal High Court — Zaria Division',      'state': 'KD', 'city': 'Zaria',        'active': False, 'judges': []},
    {'code': 'FHC-AKU', 'name': 'Federal High Court — Akure Division',      'state': 'ON', 'city': 'Akure',        'active': False, 'judges': []},
    {'code': 'FHC-BIR', 'name': 'Federal High Court — Birnin-Kebbi Division','state': 'KE','city': 'Birnin-Kebbi', 'active': False, 'judges': []},
    {'code': 'FHC-DAM', 'name': 'Federal High Court — Damaturu Division',   'state': 'YO', 'city': 'Damaturu',     'active': False, 'judges': []},
    {'code': 'FHC-DUT', 'name': 'Federal High Court — Dutse Division',      'state': 'JI', 'city': 'Dutse',        'active': False, 'judges': []},
    {'code': 'FHC-GSU', 'name': 'Federal High Court — Gusau Division',      'state': 'ZA', 'city': 'Gusau',        'active': False, 'judges': []},
    {'code': 'FHC-JAL', 'name': 'Federal High Court — Jalingo Division',    'state': 'TA', 'city': 'Jalingo',      'active': False, 'judges': []},
]

NIC_DATA = [
    {'code': 'NIC-ABJ', 'name': 'National Industrial Court — Abuja Division', 'state': 'FC',
     'city': 'Abuja', 'address': 'Plot 10, Port Harcourt Crescent, Off Gimbiya Street, Area 11, FCT',
     'phone': '07040101202', 'active': True},
    {'code': 'NIC-LAG', 'name': 'National Industrial Court — Lagos Division', 'state': 'LA',
     'city': 'Lagos', 'address': '31, Lugard Avenue, Ikoyi, Lagos',
     'phone': '08038690335', 'active': True},
    {'code': 'NIC-PH', 'name': 'National Industrial Court — Port Harcourt Division', 'state': 'RI',
     'city': 'Port Harcourt', 'address': 'No. 9 Banks Road, Opposite State High Court Complex, Old G.R.A, Port Harcourt',
     'phone': '08056632570', 'active': True},
    {'code': 'NIC-ABA', 'name': 'National Industrial Court — Abakaliki Division', 'state': 'EB', 'city': 'Abakaliki', 'active': False},
    {'code': 'NIC-ASA', 'name': 'National Industrial Court — Asaba Division',     'state': 'DE', 'city': 'Asaba',     'active': False},
    {'code': 'NIC-AKU', 'name': 'National Industrial Court — Akure Division',     'state': 'ON', 'city': 'Akure',     'active': False},
    {'code': 'NIC-BEN', 'name': 'National Industrial Court — Benin Division',     'state': 'ED', 'city': 'Benin City','active': False},
    {'code': 'NIC-CAL', 'name': 'National Industrial Court — Calabar Division',   'state': 'CR', 'city': 'Calabar',   'active': False},
    {'code': 'NIC-ENU', 'name': 'National Industrial Court — Enugu Division',     'state': 'EN', 'city': 'Enugu',     'active': False},
    {'code': 'NIC-GOM', 'name': 'National Industrial Court — Gombe Division',     'state': 'GO', 'city': 'Gombe',     'active': False},
    {'code': 'NIC-IBA', 'name': 'National Industrial Court — Ibadan Division',    'state': 'OY', 'city': 'Ibadan',    'active': False},
    {'code': 'NIC-ILO', 'name': 'National Industrial Court — Ilorin Division',    'state': 'KW', 'city': 'Ilorin',    'active': False},
    {'code': 'NIC-JOS', 'name': 'National Industrial Court — Jos Division',       'state': 'PL', 'city': 'Jos',       'active': False},
    {'code': 'NIC-KAD', 'name': 'National Industrial Court — Kaduna Division',    'state': 'KD', 'city': 'Kaduna',    'active': False},
    {'code': 'NIC-KAN', 'name': 'National Industrial Court — Kano Division',      'state': 'KN', 'city': 'Kano',      'active': False},
    {'code': 'NIC-MAI', 'name': 'National Industrial Court — Maiduguri Division', 'state': 'BO', 'city': 'Maiduguri', 'active': False},
    {'code': 'NIC-MAK', 'name': 'National Industrial Court — Makurdi Division',   'state': 'BE', 'city': 'Makurdi',   'active': False},
    {'code': 'NIC-MIN', 'name': 'National Industrial Court — Minna Division',     'state': 'NI', 'city': 'Minna',     'active': False},
    {'code': 'NIC-OWE', 'name': 'National Industrial Court — Owerri Division',    'state': 'IM', 'city': 'Owerri',    'active': False},
    {'code': 'NIC-SOK', 'name': 'National Industrial Court — Sokoto Division',    'state': 'SO', 'city': 'Sokoto',    'active': False},
    {'code': 'NIC-UMU', 'name': 'National Industrial Court — Umuahia Division',   'state': 'AB', 'city': 'Umuahia',  'active': False},
    {'code': 'NIC-UYO', 'name': 'National Industrial Court — Uyo Division',       'state': 'AK', 'city': 'Uyo',       'active': False},
    {'code': 'NIC-ABE', 'name': 'National Industrial Court — Abeokuta Division',  'state': 'OG', 'city': 'Abeokuta',  'active': False},
    {'code': 'NIC-LAF', 'name': 'National Industrial Court — Lafia Division',     'state': 'NA', 'city': 'Lafia',     'active': False},
    {'code': 'NIC-LOK', 'name': 'National Industrial Court — Lokoja Division',    'state': 'KO', 'city': 'Lokoja',    'active': False},
    {'code': 'NIC-YOL', 'name': 'National Industrial Court — Yola Division',      'state': 'AD', 'city': 'Yola',      'active': False},
    {'code': 'NIC-ZAR', 'name': 'National Industrial Court — Zaria Division',     'state': 'KD', 'city': 'Zaria',     'active': False},
]

# Lagos SHC divisions with judges
LAGOS_SHC_DIVISIONS = [
    {'code': 'SHC-LA-IKJ-GEN',  'name': 'General Civil Division',          'parent': 'Ikeja Judicial Division',   'judges': [
        'K.O. Alogba', 'O.A. Ipaye', 'L.B. Lawal-Akapo', 'L.A.F. Oluyemi',
        'L.A.M. Folami', 'Y.R. Pinheiro', 'D.T. Olatokun',
    ]},
    {'code': 'SHC-LA-IKJ-LND',  'name': 'Lands Division',                  'parent': 'Ikeja Judicial Division',   'judges': [
        'R.I.B. Adebiyi', 'M.O. Obadina', 'M.A. Savage', 'S.S. Ogunsanya',
        'A.M. Lawal', 'Y.G. Oshoala', 'O.A. Odunsanya',
    ]},
    {'code': 'SHC-LA-IKJ-FAM',  'name': 'Family and Probate Division',     'parent': 'Ikeja Judicial Division',   'judges': [
        'C.O. Balogun', 'O.I. Oguntade', 'A.O. Adeyemi', 'O.J. Awope',
    ]},
    {'code': 'SHC-LA-IKJ-CRM',  'name': 'Criminal Division',               'parent': 'Ikeja Judicial Division',   'judges': [
        'A.J. Coker', 'H.O. Oshodi', 'O.O.A. Fadipe', 'O.A. Ogala', 'I.O. Ijelu',
    ]},
    {'code': 'SHC-LA-IKJ-SPO',  'name': 'Special Offences Court',          'parent': 'Ikeja Judicial Division',   'judges': [
        'M.A. Dada', 'R.A. Oshodi',
    ]},
    {'code': 'SHC-LA-IKJ-SXO',  'name': 'Sexual Offences Court',           'parent': 'Ikeja Judicial Division',   'judges': [
        'A.O. Soladoye', 'O.A. Okunuga',
    ]},
    {'code': 'SHC-LA-LAG-GEN',  'name': 'General Civil Division',          'parent': 'Lagos Judicial Division',   'judges': [
        'T.A.O. Oyekan-Abdullai', 'J.E. Oyefeso', 'A.O. Opesanwo', 'G.A. Safari',
        'O.O. Ogungbesan', 'I.E. Alakija', 'O. Sule-Amzat', 'F.O. Aigbokaevbo', 'O.A. Oresanya',
    ]},
    {'code': 'SHC-LA-LAG-LND',  'name': 'Lands Division',                  'parent': 'Lagos Judicial Division',   'judges': [
        'O.A. Akinlade', 'O.O. Ogunjobi', 'E.O. Ashade',
    ]},
    {'code': 'SHC-LA-LAG-FAM',  'name': 'Family and Probate Division',     'parent': 'Lagos Judicial Division',   'judges': [
        'A.A. Oyebanji', 'C.A. Balogun',
    ]},
    {'code': 'SHC-LA-LAG-FTK',  'name': 'Fast Track Division',             'parent': 'Lagos Judicial Division',   'judges': [
        'O.O. Pedro', 'L.A. Okunnu', 'K.A. Jose', 'A.A. Akintoye', 'R.O. Olukolu', 'A.M. Ipaye-Nwachukwu',
    ]},
    {'code': 'SHC-LA-LAG-CRM',  'name': 'Criminal Division',               'parent': 'Lagos Judicial Division',   'judges': [
        'A.M. Nicol-Clay', 'Y.A. Adesanya', 'I.O. Harrison', 'S.I. Sonaike',
    ]},
    {'code': 'SHC-LA-ETI',      'name': 'Eti-Osa Division',                'parent': 'Lagos Judicial Division',   'judges': [
        'M.O. Obadina', 'W. Animahun',
    ]},
    {'code': 'SHC-LA-BAD',      'name': 'Badagry Judicial Division',       'parent': 'Badagry Judicial Division',  'judges': [
        'O.A. Adamson', 'E.O. Ogundare', 'M.O. Dawodu',
    ]},
    {'code': 'SHC-LA-IKO',      'name': 'Ikorodu Judicial Division',       'parent': 'Ikorodu Judicial Division',  'judges': [
        'I.O. Akinkugbe', 'A.F. Pokanu', 'M.I. Oshodi',
    ]},
    {'code': 'SHC-LA-EPE',      'name': 'Epe Judicial Division',           'parent': 'Epe Judicial Division',      'judges': [
        'W.A. Animahun', 'S.A. Olaitan',
    ]},
]

FCT_SHC_DIVISIONS = [
    {'code': 'SHC-FC-ABJ', 'name': 'FCT High Court', 'parent': 'Abuja High Court', 'judges': []},
]

RIVERS_SHC_DIVISIONS = [
    {'code': 'SHC-RI-PH', 'name': 'Port Harcourt Division', 'parent': 'Port Harcourt Judicial Division', 'judges': []},
]

# Magistrate divisions
MAGISTRATE_DIVISIONS = {
    'LA': [
        {'code': 'MC-LA-ISL', 'name': 'Lagos Island Magistrate Court',  'city': 'Lagos Island'},
        {'code': 'MC-LA-IKJ', 'name': 'Ikeja Magistrate Court',         'city': 'Ikeja'},
        {'code': 'MC-LA-BAD', 'name': 'Badagry Magistrate Court',       'city': 'Badagry'},
        {'code': 'MC-LA-EPE', 'name': 'Epe Magistrate Court',           'city': 'Epe'},
        {'code': 'MC-LA-IKO', 'name': 'Ikorodu Magistrate Court',       'city': 'Ikorodu'},
        {'code': 'MC-LA-YAB', 'name': 'Yaba Magistrate Court',          'city': 'Yaba'},
    ],
    'FC': [
        {'code': 'MC-FC-ABJ', 'name': 'Abuja Magistrate Court',         'city': 'Abuja'},
        {'code': 'MC-FC-BWA', 'name': 'Bwari Magistrate Court',         'city': 'Bwari'},
        {'code': 'MC-FC-GWA', 'name': 'Gwagwalada Magistrate Court',    'city': 'Gwagwalada'},
        {'code': 'MC-FC-KUJ', 'name': 'Kuje Magistrate Court',          'city': 'Kuje'},
    ],
    'RI': [
        {'code': 'MC-RI-PH',  'name': 'Port Harcourt Magistrate Court', 'city': 'Port Harcourt'},
    ],
}


def parse_judge_name(full_name):
    """
    Parse a judge name string like 'J.T. Tsoho' or 'Joyce Obehi Abdulmalik'
    into (first_name, last_name).
    Splits on last space — everything before is first_name, last word is last_name.
    """
    full_name = full_name.strip()
    parts = full_name.rsplit(' ', 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return full_name, full_name


class Command(BaseCommand):
    help = 'Seed CSI court data (courts, panels, divisions, judges) from static source data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete all CSI courts data before seeding (CAUTION: deletes all cause lists too)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('Deleting all CSI courts data...'))
            Court.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Deleted.'))

        self.stdout.write('Seeding CA courts...')
        self._seed_ca()

        self.stdout.write('Seeding FHC courts...')
        self._seed_fhc()

        self.stdout.write('Seeding NIC courts...')
        self._seed_nic()

        self.stdout.write('Seeding State High Courts...')
        self._seed_shc()

        self.stdout.write('Seeding Magistrate Courts...')
        self._seed_mc()

        self.stdout.write(self.style.SUCCESS('\nCSI data seeding complete!'))
        self._print_summary()

    def _seed_ca(self):
        for d in CA_DATA:
            court, created = Court.objects.get_or_create(
                code=d['code'],
                defaults={
                    'name': d['name'],
                    'court_type': 'CA',
                    'state': d['state'],
                    'city': d.get('city', ''),
                    'address': d.get('address', ''),
                    'is_active': d['active'],
                }
            )
            if not created:
                court.name = d['name']
                court.is_active = d['active']
                court.save(update_fields=['name', 'is_active'])

            status = 'created' if created else 'updated'
            self.stdout.write(f'  CA {status}: {court.name}')

            # Seed panels for active CA courts
            for panel_name in d.get('panels', []):
                panel_code = f"{d['code']}-{panel_name.replace(' ', '-').upper()}"
                panel, p_created = Panel.objects.get_or_create(
                    court=court,
                    code=panel_code,
                    defaults={'name': panel_name, 'is_active': True}
                )
                if not p_created:
                    panel.name = panel_name
                    panel.save(update_fields=['name'])
                p_status = 'created' if p_created else 'ok'
                self.stdout.write(f'    Panel {p_status}: {panel_name}')

    def _seed_fhc(self):
        for d in FHC_DATA:
            court, created = Court.objects.get_or_create(
                code=d['code'],
                defaults={
                    'name': d['name'],
                    'court_type': 'FHC',
                    'state': d['state'],
                    'city': d.get('city', ''),
                    'address': d.get('address', ''),
                    'is_active': d['active'],
                }
            )
            if not created:
                court.name = d['name']
                court.is_active = d['active']
                court.save(update_fields=['name', 'is_active'])

            status = 'created' if created else 'updated'
            self.stdout.write(f'  FHC {status}: {court.name}')

            for judge_name, role in d.get('judges', []):
                first_name, last_name = parse_judge_name(judge_name)
                title = 'CHIEF_JUDGE' if role == 'Chief Judge' else 'HON_JUSTICE'
                judge, j_created = Judge.objects.get_or_create(
                    court=court,
                    first_name=first_name,
                    last_name=last_name,
                    defaults={'title': title, 'status': 'active', 'is_active': True}
                )
                if not j_created and judge.title != title:
                    judge.title = title
                    judge.save(update_fields=['title'])
                j_status = 'created' if j_created else 'ok'
                self.stdout.write(f'    Judge {j_status}: {first_name} {last_name}')

    def _seed_nic(self):
        for d in NIC_DATA:
            court, created = Court.objects.get_or_create(
                code=d['code'],
                defaults={
                    'name': d['name'],
                    'court_type': 'NIC',
                    'state': d['state'],
                    'city': d.get('city', ''),
                    'address': d.get('address', ''),
                    'phone_number': d.get('phone', ''),
                    'is_active': d['active'],
                }
            )
            if not created:
                court.name = d['name']
                court.is_active = d['active']
                court.save(update_fields=['name', 'is_active'])

            status = 'created' if created else 'updated'
            self.stdout.write(f'  NIC {status}: {court.name}')

    def _seed_shc(self):
        active_states = {'LA', 'RI'}
        for state_code, state_name, capital in ALL_STATES:
            code = f'SHC-{state_code}'
            name = f'{state_name} State High Court'
            if state_code == 'FC':
                name = 'FCT High Court'

            court, created = Court.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'court_type': 'SHC',
                    'state': state_code,
                    'city': capital,
                    'is_active': state_code in active_states,
                }
            )
            if not created:
                court.name = name
                court.is_active = state_code in active_states
                court.save(update_fields=['name', 'is_active'])

            status = 'created' if created else 'updated'
            self.stdout.write(f'  SHC {status}: {court.name}')

            # Seed divisions + judges for Lagos
            if state_code == 'LA':
                self._seed_divisions_with_judges(court, LAGOS_SHC_DIVISIONS)
            elif state_code == 'FC':
                self._seed_divisions_with_judges(court, FCT_SHC_DIVISIONS)
            elif state_code == 'RI':
                self._seed_divisions_with_judges(court, RIVERS_SHC_DIVISIONS)

    def _seed_mc(self):
        active_states = {'LA', 'FC', 'RI'}
        for state_code, state_name, capital in ALL_STATES:
            code = f'MC-{state_code}'
            name = f'{state_name} Magistrate Court'

            court, created = Court.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'court_type': 'MC',
                    'state': state_code,
                    'city': capital,
                    'is_active': state_code in active_states,
                }
            )
            if not created:
                court.name = name
                court.is_active = state_code in active_states
                court.save(update_fields=['name', 'is_active'])

            status = 'created' if created else 'updated'
            self.stdout.write(f'  MC {status}: {court.name}')

            # Seed divisions for active magistrate courts
            if state_code in MAGISTRATE_DIVISIONS:
                for div_data in MAGISTRATE_DIVISIONS[state_code]:
                    div, d_created = Division.objects.get_or_create(
                        court=court,
                        code=div_data['code'],
                        defaults={
                            'name': div_data['name'],
                            'is_active': True,
                        }
                    )
                    if not d_created:
                        div.name = div_data['name']
                        div.save(update_fields=['name'])
                    d_status = 'created' if d_created else 'ok'
                    self.stdout.write(f'    Division {d_status}: {div.name}')

    def _seed_divisions_with_judges(self, court, divisions_data):
        for div_data in divisions_data:
            div, created = Division.objects.get_or_create(
                court=court,
                code=div_data['code'],
                defaults={'name': div_data['name'], 'is_active': True}
            )
            if not created:
                div.name = div_data['name']
                div.save(update_fields=['name'])
            d_status = 'created' if created else 'ok'
            self.stdout.write(f'    Division {d_status}: {div.name}')

            for judge_name in div_data.get('judges', []):
                first_name, last_name = parse_judge_name(judge_name)
                judge, j_created = Judge.objects.get_or_create(
                    court=court,
                    division=div,
                    first_name=first_name,
                    last_name=last_name,
                    defaults={'title': 'HON_JUSTICE', 'status': 'active', 'is_active': True}
                )
                j_status = 'created' if j_created else 'ok'
                self.stdout.write(f'      Judge {j_status}: {first_name} {last_name}')

    def _print_summary(self):
        self.stdout.write('\n' + '='*50)
        self.stdout.write('Summary:')
        for ct, label in [('CA', 'Court of Appeal'), ('FHC', 'Federal High Court'),
                           ('NIC', 'National Industrial Court'), ('SHC', 'State High Court'),
                           ('MC', 'Magistrate Court')]:
            total = Court.objects.filter(court_type=ct).count()
            active = Court.objects.filter(court_type=ct, is_active=True).count()
            self.stdout.write(f'  {label}: {total} courts ({active} active)')
        self.stdout.write(f'  Panels: {Panel.objects.count()}')
        self.stdout.write(f'  Divisions: {Division.objects.count()}')
        self.stdout.write(f'  Judges: {Judge.objects.count()}')
        self.stdout.write('='*50)
