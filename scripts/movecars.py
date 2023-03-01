from __future__ import absolute_import, print_function

from import_export.formats.base_formats import XLSX


fmt = XLSX()
f = open("/Users/grfavre/Desktop/car 3 et train 5.xlsx", fmt.get_read_mode())
dataset = fmt.create_dataset(f.read())

t = []
for (registration_id, car_id, bib_number, last, first) in dataset:
    t.append((registration_id, car_id, bib_number, last, first))

t = [
    (114, 3, 301, "Alili Bustabad", "Adrian"),
    (339, 3, 302, "Olivier", "Alice"),
    (321, 3, 303, "Rossier", "Anastasia"),
    (383, 3, 304, "Sansar", "Bat Orgil"),
    (107, 3, 305, "Corday", "Benjamin"),
    (65, 3, 306, "Jaloul", "Boris"),
    (325, 3, 307, "Gonnet", "Carl"),
    (120, 3, 308, "Zaharcenco", "Constantin"),
    (146, 3, 309, "Cuany", "Dany"),
    (235, 3, 310, "Bosnjak", "Daris"),
    (294, 3, 311, "Alves Vala", "Diogo"),
    (63, 3, 312, "Jaloul", "Elena"),
    (241, 3, 313, "Schneider", "Haris"),
    (246, 3, 314, "Cappelle", "Jarod"),
    (250, 3, 315, "Cappelle", "Jason"),
    (316, 3, 316, "Baillod", "Kiana"),
    (291, 3, 317, "Baladan", "Leandro"),
    (208, 3, 318, "Felice", "Lony"),
    (136, 3, 319, "Mazreku", "Lorik"),
    (156, 3, 320, "Tschanz", "Loris"),
    (113, 3, 321, "Simon Serralta", "Lua"),
    (249, 3, 322, "Blagojevic", "Marko"),
    (280, 3, 323, "Riganti", "Martina"),
    (295, 3, 324, "Domingues Teixeira", "Melissa"),
    (281, 3, 325, "Riganti", "Mirko"),
    (219, 3, 326, "Gligorijevic", "Nikola"),
    (338, 3, 327, "Teijeiro", "Nora"),
    (287, 3, 328, "Markotic", "Petra"),
    (119, 3, 329, "Zaharcenco", "Sofia"),
    (72, 3, 330, "Duran-Bourc'h", "Th\xe9ana"),
    (329, 3, 331, "Ahmeti", "Ylli"),
    (330, 3, 332, "D'Antino", "Achille"),
    (137, 3, 333, "Sannier", "Aline"),
    (64, 3, 334, "Babakki Barry", "Amina"),
    (282, 3, 335, "Chappuis", "Ana\xeblle"),
    (48, 3, 336, "Levy", "Axel Ethan"),
    (275, 3, 337, "da Silva Santos", "Carlota"),
    (230, 3, 338, "Castillo Polo", "Dario"),
    (164, 3, 339, "Mesple", "Elisa"),
    (267, 3, 340, "Jo\u0161tov\xe1", "Eli\u0161ka"),
    (163, 3, 341, "Ounissi Ferreira", "In\xe8s"),
    (185, 3, 342, "Koster", "Ivar"),
    (229, 3, 343, "Clerc", "Jessica"),
    (49, 3, 344, "Levy", "Johan David"),
    (159, 3, 345, "Lambert", "Jules"),
    (269, 3, 346, "Lottini", "Julie"),
    (68, 3, 347, "Zanotti", "Kevin"),
    (268, 3, 348, "Mathey", "Kim-Lou"),
    (258, 3, 349, "Acimovic", "Lazar"),
    (337, 3, 350, "Ara\xfajo Da Silva", "Leonardo"),
    (160, 3, 351, "Lambert", "Lucie"),
    (307, 3, 352, "Schweitzer", "Mat\xe9o"),
    (102, 3, 353, "Delley", "Mathias"),
    (293, 3, 354, "Scianna", "Maxime"),
    (357, 3, 355, "Carre\xf1o Hormaz\xe1bal", "Mayna"),
    (217, 3, 356, "Buccarello", "Morena"),
    (103, 3, 357, "Delley", "Nicolas"),
    (180, 3, 358, "Wingfield", "Oriana"),
    (131, 3, 359, "Levy", "Sam Ely"),
    (273, 3, 360, "Crettaz", "Santiago"),
    (270, 3, 361, "Lottini", "Shanice"),
    (187, 3, 362, "Verreschi", "Vanessa"),
    (212, 3, 363, "D'Antino", "Zelda"),
    (233, 5, 501, "Ahmed", "Kamar Etta"),
    (232, 5, 501, "Ahmed", "Kenan"),
    (117, 5, 501, "Akeza", "Teta"),
    (178, 5, 501, "Akpo", "Marcus"),
    (385, 5, 501, "Alame", "Karim"),
    (345, 5, 501, "Amoros Rezzoug", "Lydia"),
    (344, 5, 501, "amoros Rezzoug", "Yasmine"),
    (77, 5, 501, "Atrash", "Julien"),
    (33, 5, 501, "Brotto", "Alessio"),
    (35, 5, 501, "Brotto", "Irene"),
    (81, 5, 501, "Caputo", "No\xe9mie"),
    (272, 5, 501, "Carranza Durand", "Leticia"),
    (285, 5, 501, "Chamas", "Myriam"),
    (358, 5, 501, "Ciampi", "Sarah Laura"),
    (196, 5, 501, "Dawit Weldeslasie", "Arsema"),
    (257, 5, 501, "D\xe9corvet", "Karim"),
    (133, 5, 501, "Detrey", "Clarice"),
    (134, 5, 501, "Detrey", "Jada"),
    (197, 5, 501, "Dichovska", "Milena"),
    (303, 5, 501, "Do Nascimento Santana", "Nicole"),
    (349, 5, 501, "Domingues", "Hugo"),
    (261, 5, 501, "Dominique", "Ana\xefs"),
    (278, 5, 501, "Faizi", "Hashmatullah"),
    (386, 5, 501, "Filmon", "Ariam"),
    (200, 5, 501, "Fisseha", "Seim Daniel"),
    (254, 5, 501, "Fisseha", "Yared Daniel"),
    (248, 5, 501, "Freitas Praia", "Grazielle"),
    (331, 5, 501, "Gashi", "Edon"),
    (259, 5, 501, "Gozzing", "Luane"),
    (44, 5, 501, "Guarnieri Baglini", "Vera"),
    (73, 5, 501, "Guex", "Louise"),
    (201, 5, 501, "Habtemariam", "Ruta"),
    (198, 5, 501, "Habtom", "Samrawit"),
    (132, 5, 501, "Inthornprom", "Patcharapon"),
    (88, 5, 501, "Kuleshov", "Philipp"),
    (95, 5, 501, "Lefauconnier", "Aden Ray"),
    (194, 5, 501, "Lheriau", "Eva"),
    (89, 5, 501, "Mandr\xe0", "Evan"),
    (305, 5, 501, "Muharremi", "Armend"),
    (195, 5, 501, "Mustafazada", "Said Masi"),
    (252, 5, 501, "Nieuwenhuizen", "Capucine"),
    (277, 5, 501, "Omarkhel", "Ahmad Zamir"),
    (335, 5, 501, "Perrino", "Lenny"),
    (354, 5, 501, "Ric", "Elisabeth"),
    (306, 5, 501, "Salem", "Arij"),
    (109, 5, 501, "Sarasin", "Julia"),
    (374, 5, 501, "Savu", "Darian"),
    (373, 5, 501, "Savu", "Rom\xe9o"),
    (376, 5, 501, "Schetty Crucello", "Nat\xe1lia"),
    (216, 5, 501, "Schiffke", "Emilie"),
    (276, 5, 501, "Shakeri", "Qayoum"),
    (199, 5, 501, "Shalhoub", "Maya"),
    (127, 5, 501, "Stauder", "Albane Marine"),
    (126, 5, 501, "Veseli", "Leonit"),
    (309, 5, 501, "Yonas Russom", "Sinodos"),
    (182, 5, 501, "Zahnd", "Joanna Lauren"),
    (181, 5, 501, "Zahnd", "Julia Alexia"),
    (83, 5, 501, "Zharikov", "Vsevolod"),
]


fmt = XLSX()
f = open("/Users/grfavre/Desktop/train 5.xlsx", fmt.get_read_mode())
dataset = fmt.create_dataset(f.read())

t = []
for (registration_id, car_id, bib_number, last, first) in dataset:
    t.append((registration_id, car_id, bib_number, last, first))

t = [
    (95, 5, 501, "Lefauconnier", "Aden Ray"),
    (277, 5, 502, "Omarkhel", "Ahmad Zamir"),
    (127, 5, 503, "Stauder", "Albane Marine"),
    (33, 5, 504, "Brotto", "Alessio"),
    (261, 5, 505, "Dominique", "Ana\xefs"),
    (386, 5, 506, "Filmon", "Ariam"),
    (306, 5, 507, "Salem", "Arij"),
    (305, 5, 508, "Muharremi", "Armend"),
    (196, 5, 509, "Dawit Weldeslasie", "Arsema"),
    (252, 5, 510, "Nieuwenhuizen", "Capucine"),
    (133, 5, 511, "Detrey", "Clarice"),
    (374, 5, 512, "Savu", "Darian"),
    (331, 5, 513, "Gashi", "Edon"),
    (354, 5, 514, "Ric", "Elisabeth"),
    (216, 5, 515, "Schiffke", "Emilie"),
    (194, 5, 516, "Lheriau", "Eva"),
    (89, 5, 517, "Mandr\xe0", "Evan"),
    (248, 5, 518, "Freitas Praia", "Grazielle"),
    (278, 5, 519, "Faizi", "Hashmatullah"),
    (349, 5, 520, "Domingues", "Hugo"),
    (35, 5, 521, "Brotto", "Irene"),
    (134, 5, 522, "Detrey", "Jada"),
    (182, 5, 523, "Zahnd", "Joanna Lauren"),
    (109, 5, 524, "Sarasin", "Julia"),
    (181, 5, 525, "Zahnd", "Julia Alexia"),
    (77, 5, 526, "Atrash", "Julien"),
    (233, 5, 527, "Ahmed", "Kamar Etta"),
    (385, 5, 528, "Alame", "Karim"),
    (257, 5, 529, "D\xe9corvet", "Karim"),
    (232, 5, 530, "Ahmed", "Kenan"),
    (335, 5, 531, "Perrino", "Lenny"),
    (126, 5, 532, "Veseli", "Leonit"),
    (272, 5, 533, "Carranza Durand", "Leticia"),
    (73, 5, 534, "Guex", "Louise"),
    (259, 5, 535, "Gozzing", "Luane"),
    (345, 5, 536, "Amoros Rezzoug", "Lydia"),
    (178, 5, 537, "Akpo", "Marcus"),
    (199, 5, 538, "Shalhoub", "Maya"),
    (197, 5, 539, "Dichovska", "Milena"),
    (285, 5, 540, "Chamas", "Myriam"),
    (376, 5, 541, "Schetty Crucello", "Nat\xe1lia"),
    (303, 5, 542, "Do Nascimento Santana", "Nicole"),
    (81, 5, 543, "Caputo", "No\xe9mie"),
    (132, 5, 544, "Inthornprom", "Patcharapon"),
    (88, 5, 545, "Kuleshov", "Philipp"),
    (276, 5, 546, "Shakeri", "Qayoum"),
    (373, 5, 547, "Savu", "Rom\xe9o"),
    (201, 5, 548, "Habtemariam", "Ruta"),
    (195, 5, 549, "Mustafazada", "Said Masi"),
    (198, 5, 550, "Habtom", "Samrawit"),
    (358, 5, 551, "Ciampi", "Sarah Laura"),
    (200, 5, 552, "Fisseha", "Seim Daniel"),
    (309, 5, 553, "Yonas Russom", "Sinodos"),
    (117, 5, 554, "Akeza", "Teta"),
    (44, 5, 555, "Guarnieri Baglini", "Vera"),
    (83, 5, 556, "Zharikov", "Vsevolod"),
    (254, 5, 557, "Fisseha", "Yared Daniel"),
    (344, 5, 558, "amoros Rezzoug", "Yasmine"),
]

from registrations.models import Registration, Transport


for (registration_id, car_id, bib_number, last, first) in t:
    try:
        reg = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        print(("reg %s does not exist" % registration_id))
    if not last == reg.child.last_name:
        print(("Name is wrong (%s)! Skipping reg %s" % (last, registration_id)))
        continue
    if not str(bib_number) == reg.child.bib_number:
        print("bib number is wrong, fixing it")
        reg.child.bib_number = bib_number
        reg.child.save()
    reg.transport = Transport.objects.get(name=str(car_id))
    reg.save()
    print("ok")
