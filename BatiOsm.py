# -*- coding:Utf-8 -*-
#!/usr/bin/env python
import sys
import time
from math import pi
from math import sqrt

import lxml.etree

BORNE_INF_MODIF = 1.
BORNE_SUP_MODIF = 10.
NB_ZONE_USER = 500

class Point:
    """Définition d'un point.
    
    Attributs :
    - identifiant (chaine de caractère) 
    - latitude et longitude (flottant)
    """
    def __init__(self, node_id, node_lat, node_lon):
        self.node_id = node_id
        self.node_lat = float(node_lat)
        self.node_lon = float(node_lon)
        self.historique = []
        
    def affiche(self):
        print(self.node_id, self.node_lat, self.node_lon)
        
    def distance(self, other):
        """Calcul de la distance entre deux points"""
        d_lat = self.node_lat - other.node_lat
        d_lon = self.node_lon - other.node_lon
        return sqrt(d_lat**2 + d_lon**2)*pi/180*6378137
        
    def export_node(self):
        """Création du code xml équivalent au point"""
        i_hist = 0
        nodeHist = "  <node "
        while i_hist < len(self.historique):
            nodeHist = nodeHist + self.historique[i_hist] + "=" + "\"" + \
                self.historique[i_hist + 1] + "\" "
            i_hist = i_hist + 2
        nodeHist = nodeHist + "/>"
        self.print_node = nodeHist
    
    def setHistorique(self, historique):
        """
        Cette méthode défini dans une variable tous les éléments relatifs à
        l'historique dans osm : numéros de version, date de maj, dernier
        utilisateur ayant modifié le batiment, le changeset,etc...
        """
        self.historique=historique

class Batiment:
    """L'entité Batiment rassemble plusieurs données : 
    
        - bat_id : un identifiant (chaine de caractère)
        - nbre_node : le nombre de points du batiment (nombre entier)
        - node_id : le tableau des Points du batiments
        - pt_moy : le point de référence du batiments (centre de gravité)
        - dist_mini : une valeurs de distance pour détecter la modification du batiment
        - largeur : la largeur du batiment
        - status : le status du batiment (nouveau, identique, modifié, supprimé)
        - nombre_tag : le nombre de tag défini dans le fichier
        - tableau_tag_key : le tableau d'identifiants des tags
        - tableau_tag_value : le tableau des valeurs des tags
        - pbAire : l'information si le batiment a une aire nulle
        - Aire : l'aire du batiment
        - multipolygone : yes si le batiment en est un, no sinon
        - role : le role si le batiment appartient à une relation
        - nom_relation : le nom de la relation auquel il appartient (ie l'ID 
            de la relation tel que lu dans le fichier source)
    """
    def __init__(self, bat_id, nbre_node, node_id, 
            numTag, tableauTagKey, tableauTagValue, 
            distance=1000, largeur = 0., status = "UNKNOWN", pbAire = "NO",
            multipolygone = "no", role = "outer", nom_relation = ""):
        self.bat_id = bat_id
        self.nbre_node = nbre_node
        self.node_id = node_id
        self.dist_mini = float(distance)
        self.largeur = largeur
        self.status = status
        self.nombre_tag = numTag
        self.tableau_tag_key = tableauTagKey
        self.tableau_tag_value = tableauTagValue
        self.pbAire = "NO"
        self.aire = 0.
        self.multipolygone = "no"
        self.role = "outer"
        self.nom_relation = ""
        self.innerWay = []
    
    def BatimentToPoint(self):
        """Calcul du centre de gravité du batiment.
        
        Etant donné qu'il n'y a pas suffisamment de différence entre chaque point,
        pour faire les calculs à partir de la latitude et de la longitude,
        les coordonnées sont d'abord exprimés en "pseudo-mètres" (c.a.d en 
        approximant chaque composante par rapport à l'origine à R*(lat2-lat1).
        R étant le rayon de la terre, pris égal à 6500000. 
        L'origine est arbitrairement définit comme le premier point du batiment. 
        Cela permet de faire les calculs sur des nombres plus grands.
        Ensuite le calcul se fait d'après 
            https://fr.wikipedia.org/wiki/Aire_et_centre_de_masse_d%27un_polygone
        Le calcul nécessite de diviser par la surface du batiment. Cela
        pose problème si le batiment a une surface nulle. Les exceptions
        sont traités avec pbAire. Dans ce cas le point de référence de 
        ces batiments est la moyenne des coordonnées de chaque point.
        """
        i_node = 0
        calculLatitude = 0
        calculLongitude = 0
        latMoyenne = 0
        lonMoyenne = 0
        aire = 0
        latLocale = []
        lonLocale = []
        while i_node < self.nbre_node:
            latLocale.append((self.node_id[i_node].node_lat - \
                self.node_id[0].node_lat) * 6378137.*pi/180)
            lonLocale.append((self.node_id[i_node].node_lon - \
                self.node_id[0].node_lon) * 6378137.*pi/180)
            i_node = i_node + 1
        i_node = 0
        while i_node < self.nbre_node - 1:
            produitEnCroix = (latLocale[i_node] * lonLocale[i_node + 1] - \
                latLocale[i_node + 1] * lonLocale[i_node])
            aire = aire + 0.5 * produitEnCroix
            calculLatitude = calculLatitude + (latLocale[i_node] + \
                latLocale[i_node + 1]) * produitEnCroix
            calculLongitude = calculLongitude + (lonLocale[i_node] + \
                lonLocale[i_node + 1]) * produitEnCroix
            i_node = i_node + 1
        i_node = 0
        if aire == 0.:
            self.pbAire = "YES"
            while i_node < self.nbre_node:
                latMoyenne = latMoyenne + self.node_id[i_node].node_lat
                lonMoyenne = lonMoyenne + self.node_id[i_node].node_lon
                i_node = i_node + 1
            latitude = latMoyenne / self.nbre_node
            longitude = lonMoyenne / self.nbre_node
        else:
            latitude = self.node_id[0].node_lat + \
                calculLatitude / (6 * aire) * 180/(pi*6378137)
            longitude = self.node_id[0].node_lon + \
                calculLongitude / (6 * aire) * 180/(pi*6378137)
            self.aire = aire
        self.pt_moy = Point(self.bat_id, latitude, longitude)
        self.pt_moy.setHistorique("")
        
    def calculLargeur(self):
        """Calcul de la largeur approximative du batiment. 
        
        Cette distance intervient ensuite dans la détermination
        du status du batiment. Si la distance mini est supérieure à cette
        largeur alors cela veut dire que le batiment est nouveau ou 
        supprimé."""
        tableauLatitude = []
        tableauLongitude = []
        for node in range(self.nbre_node):
            tableauLatitude.append(self.node_id[node].node_lat)
            tableauLongitude.append(self.node_id[node].node_lon)
        minLat = min(tableauLatitude)
        maxLat = max(tableauLatitude)
        minLon = min(tableauLongitude)
        maxLon = max(tableauLongitude)
        self.largeur = sqrt((maxLat - minLat)**2 + (maxLon - minLon)**2)*pi/180*6378137
        
    def setDistMini(self, distance):
        """Cette méthode permet de définir la distance mini comme étant celle
            passé en paramètre"""
        self.dist_mini = float(distance)
    
    def setBatProche(self, nomBatProche):
        """Cette méthode permet de définir que le batiment auquel elle est
        appliquée correspond au batiment passé en paramètre"""
        self.id_bat_proche = nomBatProche
        
    def setStatus(self, status):
        """Cette méthode défini le status du batiment."""
        self.status = status
    
    def setRole(self, role):
        """
        Cette méthode défini le role du batiment lorsqu'il appartient à
        une relation. Le role est soit "inner" soit "outer".
        """
        self.role = role
        
    def setHistorique(self, historique):
        """
        Cette méthode défini dans une variable tous les éléments relatifs à
        l'historique dans osm : numéros de version, date de maj, dernier
        utilisateur ayant modifié le batiment, le changeset,etc...
        """
        self.historique = historique
        
    def export_bat(self):
        """Cette méthode défini une version xml du batiment, de ses noeuds
        et de ses éventuels tag dans le but d'être transcrit dans un fichier."""
        export = []
        res_export = ""
        if self.historique != "":
            i_hist = 0
            wayHist= "  <way "
            while i_hist < len(self.historique):
                wayHist= wayHist + self.historique[i_hist] + "=" + "\"" + \
                    self.historique[i_hist + 1] + "\" "
                i_hist = i_hist + 2
            wayHist = wayHist + ">"
            export.append(wayHist)
        else:
            export.append("  <way id=\"" + self.bat_id + "\" visible=\"true\">")
        i_node = 0
        while i_node < self.nbre_node:
            export.append("    <nd ref=\"" + self.node_id[i_node].node_id + \
                "\" />")
            i_node = i_node + 1
        for i_tag in range(self.nombre_tag):
            export.append("    <tag k=\"" + self.tableau_tag_key[i_tag] + \
                "\" v=\"" + self.tableau_tag_value[i_tag] + "\" />")
        export.append("  </way>")
        i_node = 0
        while i_node < self.nbre_node:
            self.node_id[i_node].export_node()
            export.append(self.node_id[i_node].print_node)
            i_node = i_node + 1
        if self.multipolygone == "yes":
            # export des chemins intérieurs
            CheminInterieur=""
            for i_inner in range(len(self.innerWay)):
                self.innerWay[i_inner].export_bat()
                CheminInterieur = CheminInterieur + self.innerWay[i_inner].print_bat
            export.append(CheminInterieur)
            # export de la relation
            export.append("  <relation id=\"" + self.nom_relation + "\">")
            export.append("    <tag k=\"type\" v=\"multipolygon\"/>")
            export.append("    <member type=\"way\" ref=\"" + self.bat_id + \
                 "\" role=\"outer\"/>")
            for ways in range(len(self.innerWay)):
                export.append("    <member type=\"way\" ref=\"" + \
                    self.innerWay[ways].bat_id + "\" role=\"inner\"/>")
            export.append("  </relation>")
        nb_ligne = len(export)
        i_ligne = 0
        while i_ligne < nb_ligne:
            if i_ligne == nb_ligne - 1:
                res_export = res_export + export[i_ligne]
            else:
                res_export = res_export + export[i_ligne] + "\n"
            i_ligne = i_ligne + 1
        self.print_bat = res_export
        
    def copy_tag(self, other, status):
        """Cette méthode permet de copier les tag d'un batiment passé en 
        paramètre au batiment auquelle elle est appliquée.
        Lorsque le batiment 'self' est détecté comme identique, la source est
        hérité du batiment 'other'. Par contre lorsque le batiment 'self' est
        détecté comme modifié, la source est mis à jour pour prendre la valeur
        du batiment 'other'.
        """
        if status == "IDENTIQUE":
            self.nombre_tag = other.nombre_tag
            self.tableau_tag_key = other.tableau_tag_key
            self.tableau_tag_value = other.tableau_tag_value
        elif status == "MODIFIE":
            try:
                rang_tag_source = self.tableau_tag_key.index("source")
                tag_source_save = self.tableau_tag_value[rang_tag_source]
            except:
                pass
            self.nombre_tag = other.nombre_tag
            self.tableau_tag_key = other.tableau_tag_key
            self.tableau_tag_value = other.tableau_tag_value
            try:
                rang_tag_source = self.tableau_tag_key.index("source")
                self.tableau_tag_value[rang_tag_source] = tag_source_save
            except:
                pass

    def addInner(self, other):
        """
        Cette méthode permet d'ajouter un batiment en tant que chemin intérieur
        pour la définition d'un multipolygone. L'objectif étant de se passer 
        de la classe relation et de considérer les chemins intérieurs d'un 
        multipolygone comme une dépendance du chemin extérieur.
        """
        self.innerWay.append(other)
    
    def addRelation(self, nom_relation):
        """
        Cette méthode défini le numéro de la relation a créer lorsque le batiment
        est un multipolygone.
        """
        self.nom_relation = nom_relation

def formatLog(donnees, nbCarLim, separateur):
    """Cette fonction permet de générer une chaine de caractère formaté et 
    de longueur constante à partir du tableau passé en paramètre"""
    result = ""
    nbData = len(donnees)
    for i_data in range(nbData):
        donnees[i_data] = " " + donnees[i_data]
        nbCar = len(donnees[i_data])
        while nbCar < nbCarLim:
            donnees[i_data] = donnees[i_data] + " "
            nbCar = len(donnees[i_data])
        result = result + separateur + donnees[i_data]
    return result

#------------------------------------------------------------------------------
#      D E B U T   D U   P R O G R A M M E
#------------------------------------------------------------------------------


adresse = sys.path[0]
fichier_osm_old = sys.argv[1]
fichier_osm_new = sys.argv[2]
prefixe = sys.argv[3]
try:
    mode = sys.argv[4]
except:
    mode = ""
    pass
separation = "--------------------------------------------------------------------------------------------------------------------------------"


tps1 = time.perf_counter()

print("------------------------------------------------------------------")
print("-                    Lecture des données                         -")
print("------------------------------------------------------------------")

#------------------------------------------------------------------------
#lecture des nouveaux batiments :
#------------------------------------------------------------------------
print("lecture du fichier " + fichier_osm_new + "...")

lat_min=90.
lat_max=0.
lon_min=45.
lon_max=-45.

new_nodes = []
new_id_nodes = []

new_nbre_nodes = 0
new_nbre_ways = 0
i_way = 0
i_nd_ref = 0
col_id = 0
col_lat = 0
col_lon = 0

utf8_xml_parser = lxml.etree.XMLParser(encoding='utf-8')
new_bati_etree = lxml.etree.parse(fichier_osm_new, parser=utf8_xml_parser)
new_nbre_nodes = 0
new_bati_root = new_bati_etree.getroot()

# lecture des noeuds
for node in new_bati_root.iter('node'):
    historique = []
    node_id = node.get('id')
    node_lat = node.get('lat')
    node_lon = node.get('lon')
    if float(node_lat) < lat_min:
        lat_min = float(node_lat)
    if float(node_lat) > lat_max:
        lat_max = float(node_lat)
    if float(node_lon) < lon_min:
        lon_min = float(node_lon)
    if float(node_lon) > lon_max:
        lon_max = float(node_lon)
    new_id_nodes.append(node_id)
    new_nodes.append(Point(node_id, node_lat, node_lon))
    info_nodes = node.attrib
    for i_key in range(len(info_nodes)):
        historique.append(info_nodes.keys()[i_key])
        historique.append(info_nodes.get(info_nodes.keys()[i_key]))
    new_nodes[new_nbre_nodes].setHistorique(historique)
    new_nbre_nodes = new_nbre_nodes + 1

NB_ZONE_LAT = int((lat_max - lat_min) * (pi/180*6378137) / (2 * BORNE_SUP_MODIF))-1
NB_ZONE_LON = int((lon_max - lon_min) * (pi/180*6378137) / (2 * BORNE_SUP_MODIF))-1
NB_ZONE = min(NB_ZONE_LAT,NB_ZONE_LON,500,NB_ZONE_USER)
delta_lat = (lat_max-lat_min)/NB_ZONE
delta_lon = (lon_max-lon_min)/NB_ZONE

new_bati = []
for i in range(NB_ZONE):
    new_bati += [[]]
    for j in range(NB_ZONE):
        new_bati[i] += [[]]

# lectures des batiments
for way in new_bati_root.iter('way'):
    tab_nodes = []
    tab_key = []
    tab_value = []
    way_id = way.get('id')
    nbre_node = len(way.findall('./nd'))
    nbre_tag = len(way.findall('./tag'))
    for node in way.findall('./nd'):
        id_node = node.get('ref')
        tab_nodes.append(new_nodes[new_id_nodes.index(id_node)])
    for tag in way.findall('./tag'):
        tab_key.append(tag.get('k'))
        tab_value.append(tag.get('v'))
    batiment_lu = Batiment(way_id, nbre_node, tab_nodes, nbre_tag, tab_key,\
        tab_value, 1000, 0., "UNKNOWN")
    batiment_lu.BatimentToPoint()
    if batiment_lu.pbAire == "YES":
        print("  Attention, surface nulle obtenue pour le batiment :" + \
            batiment_lu.bat_id)
    batiment_lu.calculLargeur()
    batiment_lu.setHistorique("")
    batiment_lu.setBatProche("")
    repereLatitude = int((batiment_lu.pt_moy.node_lat-lat_min)/delta_lat)
    repereLongitude = int((batiment_lu.pt_moy.node_lon-lon_min)/delta_lon)
    if repereLatitude > NB_ZONE-1:
        repereLatitude = NB_ZONE-1
    if repereLongitude > NB_ZONE-1:
        repereLongitude = NB_ZONE-1
    if repereLatitude < 0:
        repereLatitude = 0
    if repereLongitude < 0:
        repereLongitude = 0
    new_bati[repereLatitude][repereLongitude].append(batiment_lu)
    new_nbre_ways = new_nbre_ways + 1

# lectures des relations
for relation in new_bati_root.iter('relation'):
    id_relation = relation.get('id')
    for member in relation.findall('./member'):
        id_membre = member.get('ref')
        role = member.get('role')
        for i_lat in range(NB_ZONE):
            for i_lon in range(NB_ZONE):
                for i_bat in range(len(new_bati[i_lat][i_lon])):
                    if new_bati[i_lat][i_lon][i_bat].bat_id == id_membre:
                        if role == "outer":
                            OuterWay = new_bati[i_lat][i_lon][i_bat]
                            OuterWay.addRelation(id_relation)
                            OuterWay.multipolygone = "yes"
                        else:
                            new_bati[i_lat][i_lon][i_bat].setRole("inner")
                            OuterWay.addInner(new_bati[i_lat][i_lon][i_bat])

print("  " + str(new_nbre_nodes) + " noeuds répertoriés dans le fichier " + \
    fichier_osm_new)
print("  " + str(new_nbre_ways) + " batiments répertoriés dans le fichier " + \
    fichier_osm_new)

#------------------------------------------------------------------------
#lecture des vieux batiments :
#------------------------------------------------------------------------
#file_old = open(fichier_osm_old, "r")
print("lecture du fichier " + fichier_osm_old + "...")

old_nodes = []
old_id_nodes = []

old_nbre_nodes = 0
old_nbre_ways = 0
i_way = 0
i_nd_ref = 0
col_id = 0
col_lat = 0
col_lon = 0

utf8_xml_parser = lxml.etree.XMLParser(encoding='utf-8')
old_bati_etree = lxml.etree.parse(fichier_osm_old, parser=utf8_xml_parser)
old_nbre_nodes = 0
old_bati_root = old_bati_etree.getroot()

# lecture des noeuds
for node in old_bati_root.iter('node'):
    historique = []
    node_id = node.get('id')
    node_lat = node.get('lat')
    node_lon = node.get('lon')
    old_id_nodes.append(node_id)
    old_nodes.append(Point(node_id, node_lat, node_lon))
    info_nodes = node.attrib
    for i_key in range(len(info_nodes)):
        historique.append(info_nodes.keys()[i_key])
        historique.append(info_nodes.get(info_nodes.keys()[i_key]))
    old_nodes[old_nbre_nodes].setHistorique(historique)
    old_nbre_nodes = old_nbre_nodes + 1

old_bati = []
for i in range(NB_ZONE):
    old_bati += [[]]
    for j in range(NB_ZONE):
        old_bati[i] += [[]]

# lectures des batiments
for way in old_bati_root.iter('way'):
    historique = []
    tab_nodes = []
    tab_key = []
    tab_value = []
    way_id = way.get('id')
    info_way = way.attrib
    nbre_node = len(way.findall('./nd'))
    nbre_tag = len(way.findall('./tag'))
    for node in way.findall('./nd'):
        id_node = node.get('ref')
        tab_nodes.append(old_nodes[old_id_nodes.index(id_node)])
    for tag in way.findall('./tag'):
        tab_key.append(tag.get('k'))
        tab_value.append(tag.get('v'))
    for i_key in range(len(info_way)):
        historique.append(info_way.keys()[i_key])
        historique.append(info_way.get(info_way.keys()[i_key]))
    batiment_lu = Batiment(way_id, nbre_node, tab_nodes, nbre_tag, tab_key,\
        tab_value, 1000, 0., "UNKNOWN")
    batiment_lu.BatimentToPoint()
    if batiment_lu.pbAire == "YES":
        print("  Attention, surface nulle obtenue pour le batiment :" + \
            batiment_lu.bat_id)
    batiment_lu.calculLargeur()
    batiment_lu.setHistorique(historique)
    batiment_lu.setBatProche("")
    repereLatitude = int((batiment_lu.pt_moy.node_lat-lat_min)/delta_lat)
    repereLongitude = int((batiment_lu.pt_moy.node_lon-lon_min)/delta_lon)
    if repereLatitude > NB_ZONE-1:
        repereLatitude = NB_ZONE-1
    if repereLongitude > NB_ZONE-1:
        repereLongitude = NB_ZONE-1
    if repereLatitude < 0:
        repereLatitude = 0
    if repereLongitude < 0:
        repereLongitude = 0
    old_bati[repereLatitude][repereLongitude].append(batiment_lu)
    old_nbre_ways = old_nbre_ways + 1

# lectures des relations
for relation in old_bati_root.iter('relation'):
    id_relation = relation.get('id')
    for member in relation.findall('./member'):
        id_membre = member.get('ref')
        role = member.get('role')
        for i_lat in range(NB_ZONE):
            for i_lon in range(NB_ZONE):
                for i_bat in range(len(old_bati[i_lat][i_lon])):
                    if old_bati[i_lat][i_lon][i_bat].bat_id == id_membre:
                        if role == "outer":
                            OuterWay = old_bati[i_lat][i_lon][i_bat]
                            OuterWay.addRelation(id_relation)
                            OuterWay.multipolygone = "yes"
                        else:
                            old_bati[i_lat][i_lon][i_bat].setRole("inner")
                            OuterWay.addInner(old_bati[i_lat][i_lon][i_bat])

tps2 = time.perf_counter()
print("  " + str(old_nbre_nodes) + " noeuds répertoriés dans le fichier " + \
    fichier_osm_old)
print("  " + str(old_nbre_ways) + " batiments répertoriés dans le fichier " + \
    fichier_osm_old)
print("------------------------------------------------------------------")
print("Temps de lecture des fichiers : " + str(tps2 - tps1))
print("------------------------------------------------------------------")
print("-  Recherche des similitudes et des différences entre batiments  -")
print("-  NB_ZONE a été calculé à : " + str(NB_ZONE))
print("------------------------------------------------------------------")
#------------------------------------------------------------------------------
# calcul des distances mini entre chaque anciens batiments
# pour chaque batiment anciens (resp. nouveau) on détermine la distance 
# la plus petite avec tous les nouveaux batiments (resp. anciens)
#------------------------------------------------------------------------------
#

nb_bat_traite = 0
avancement = 0.
nb_comparaison = 0
for i_lat in range(NB_ZONE):
    for i_lon in range(NB_ZONE):
        lat_inf = max(i_lat-1,0)
        lon_inf = max(i_lon-1,0)
        lat_sup = min(i_lat+1,NB_ZONE-1) + 1
        lon_sup = min(i_lon+1,NB_ZONE-1) + 1
        for i_bat in range(len(old_bati[i_lat][i_lon])):
            if old_bati[i_lat][i_lon][i_bat].role == "outer":
                nb_bat_traite = nb_bat_traite + 1
                avancement = float(nb_bat_traite)/(old_nbre_ways+new_nbre_ways)*100.
                sys.stdout.write("Calcul en cours : " + str(int(avancement)) + " %" + chr(13))
                for n_lat in range(lat_inf,lat_sup):
                    for n_lon in range(lon_inf,lon_sup):
                        for n_bat in range(len(new_bati[n_lat][n_lon])):
                            if new_bati[n_lat][n_lon][n_bat].role == "outer":
                                distance=old_bati[i_lat][i_lon][i_bat].pt_moy.distance(new_bati[n_lat][n_lon][n_bat].pt_moy)
                                nb_comparaison = nb_comparaison + 1
                                if old_bati[i_lat][i_lon][i_bat].dist_mini > distance:
                                    old_bati[i_lat][i_lon][i_bat].setDistMini(distance)
                                    old_bati[i_lat][i_lon][i_bat].setBatProche(new_bati[n_lat][n_lon][n_bat].bat_id)

for i_lat in range(NB_ZONE):
    for i_lon in range(NB_ZONE):
        lat_inf = max(i_lat-1,0)
        lon_inf = max(i_lon-1,0)
        lat_sup = min(i_lat+1,NB_ZONE-1) + 1
        lon_sup = min(i_lon+1,NB_ZONE-1) + 1
        for i_bat in range(len(new_bati[i_lat][i_lon])):
            if new_bati[i_lat][i_lon][i_bat].role == "outer":
                nb_bat_traite = nb_bat_traite + 1
                avancement = float(nb_bat_traite)/(old_nbre_ways+new_nbre_ways)*100.
                sys.stdout.write("Calcul en cours : " + str(int(avancement)) + " %" + chr(13))
                for o_lat in range(lat_inf,lat_sup):
                    for o_lon in range(lon_inf,lon_sup):
                        for o_bat in range(len(old_bati[o_lat][o_lon])):
                            if old_bati[o_lat][o_lon][o_bat].role == "outer":
                                distance=new_bati[i_lat][i_lon][i_bat].pt_moy.distance(old_bati[o_lat][o_lon][o_bat].pt_moy)
                                nb_comparaison = nb_comparaison + 1
                                if new_bati[i_lat][i_lon][i_bat].dist_mini > distance:
                                    new_bati[i_lat][i_lon][i_bat].setDistMini(distance)
                                    new_bati[i_lat][i_lon][i_bat].setBatProche(old_bati[o_lat][o_lon][o_bat].bat_id)
                                    if distance < BORNE_INF_MODIF:
                                        new_bati[i_lat][i_lon][i_bat].copy_tag(old_bati[o_lat][o_lon][o_bat],"IDENTIQUE")
                                    elif distance > BORNE_INF_MODIF and distance < BORNE_SUP_MODIF:
                                        new_bati[i_lat][i_lon][i_bat].copy_tag(old_bati[o_lat][o_lon][o_bat],"MODIFIE")
#------------------------------------------------------------------------
# Classement des batiments :
#  - dist_mini < BORNE_INF_MODIF : identique
#  - BORNE_INF_MODIF < dist_mini < BORNE_SUP_MODIF : modifié
#  - dist_mini > BORNE_SUP_MODIF : nouveau ou supprimé
#  - dist_mini > largeur : nouveau ou supprimé
#------------------------------------------------------------------------
for i_lat in range(NB_ZONE):
    for i_lon in range(NB_ZONE):
        #Classement des anciens batiments
        for i_bat in range(len(old_bati[i_lat][i_lon])):
            if old_bati[i_lat][i_lon][i_bat].role == "outer":
                if old_bati[i_lat][i_lon][i_bat].dist_mini > BORNE_SUP_MODIF:
                    old_bati[i_lat][i_lon][i_bat].setStatus("SUPPRIME")
                if old_bati[i_lat][i_lon][i_bat].dist_mini > old_bati[i_lat][i_lon][i_bat].largeur:
                    old_bati[i_lat][i_lon][i_bat].setStatus("SUPPRIME")
        #Classement des nouveaux batiments
        for i_bat in range(len(new_bati[i_lat][i_lon])):
            if new_bati[i_lat][i_lon][i_bat].role == "outer":
                if new_bati[i_lat][i_lon][i_bat].dist_mini < BORNE_INF_MODIF:
                    new_bati[i_lat][i_lon][i_bat].setStatus("IDENTIQUE")
                elif new_bati[i_lat][i_lon][i_bat].dist_mini > BORNE_INF_MODIF \
                        and new_bati[i_lat][i_lon][i_bat].dist_mini < BORNE_SUP_MODIF:
                    new_bati[i_lat][i_lon][i_bat].setStatus("MODIFIE")
                elif new_bati[i_lat][i_lon][i_bat].dist_mini > BORNE_SUP_MODIF:
                    new_bati[i_lat][i_lon][i_bat].setStatus("NOUVEAU")
                if new_bati[i_lat][i_lon][i_bat].dist_mini > new_bati[i_lat][i_lon][i_bat].largeur:
                    new_bati[i_lat][i_lon][i_bat].setStatus("NOUVEAU")

nb_bat_new = 0
nb_bat_mod = 0
nb_bat_del = 0
nb_bat_noMod = 0

# Comptage des batiment de chaque catégorie.
for i_lat in range(NB_ZONE):
    for i_lon in range(NB_ZONE):
        for i_bat in range(len(old_bati[i_lat][i_lon])):
            if old_bati[i_lat][i_lon][i_bat].role == "outer":
                if old_bati[i_lat][i_lon][i_bat].status == "SUPPRIME":
                    nb_bat_del = nb_bat_del +1
        for i_bat in range(len(new_bati[i_lat][i_lon])):
            if new_bati[i_lat][i_lon][i_bat].role == "outer":
                if new_bati[i_lat][i_lon][i_bat].status == "IDENTIQUE":
                    nb_bat_noMod = nb_bat_noMod + 1
                elif new_bati[i_lat][i_lon][i_bat].status == "MODIFIE":
                    nb_bat_mod = nb_bat_mod + 1
                elif new_bati[i_lat][i_lon][i_bat].status == "NOUVEAU":
                    nb_bat_new = nb_bat_new + 1

# Vérification de la cohérence des résultats. On chercher à vérifier que :
# nb_bat_apres = nb_bat_avant + nouveaux - supprimés
# si l'équation n'est pas vérifié et que la zone compte des batiments modifiés
# suffisant pour rétablir l'équilibre, alors on déclare les batiments modifiés 
# comme nouveaux sinon on affiche un warning
warning_equilibre = []
warning_equilibre.append("Erreur d'équilibre : nb_bat_apres <> nb_bat_avant + nouveaux - supprimés")
for i_lat in range(NB_ZONE):
    for i_lon in range(NB_ZONE):
        nb_nouveaux = 0
        nb_supprimes = 0
        nb_modifies = 0
        nb_identiques = 0
        nb_innner = 0
        nb_bat_apres = len(new_bati[i_lat][i_lon])
        nb_bat_avant = len(old_bati[i_lat][i_lon])
        for i_bat in range(len(old_bati[i_lat][i_lon])):
            if old_bati[i_lat][i_lon][i_bat].status == "SUPPRIME":
                nb_supprimes = nb_supprimes + 1
        for i_bat in range(len(new_bati[i_lat][i_lon])):
            if new_bati[i_lat][i_lon][i_bat].status == "NOUVEAU":
                nb_nouveaux = nb_nouveaux + 1
            elif new_bati[i_lat][i_lon][i_bat].status == "MODIFIE":
                nb_modifies = nb_modifies + 1
            elif new_bati[i_lat][i_lon][i_bat].status == "IDENTIQUE":
                nb_identiques = nb_identiques + 1
            elif new_bati[i_lat][i_lon][i_bat].role == "inner":
                nb_innner = nb_innner + 1
        if nb_bat_apres != nb_bat_avant + nb_nouveaux - nb_supprimes:
            if nb_bat_apres == nb_bat_avant + nb_nouveaux + nb_modifies - nb_supprimes:
                for i_bat in range(len(new_bati[i_lat][i_lon])):
                    if new_bati[i_lat][i_lon][i_bat].status == "MODIFIE":
                        new_bati[i_lat][i_lon][i_bat].setStatus("NOUVEAU")
            else:
                warning_equilibre.append("Erreur d'équilibre pour la zone i_lat" \
                    + " / i_lon " + str(i_lat) + "/" + str(i_lon))
                warning_equilibre.append("   Avant : " \
                    + str(nb_bat_avant) + "   Après : " + str(nb_bat_apres) \
                    + "   Nouveaux : " + str(nb_nouveaux) + "   Supprimés : " \
                    + str(nb_supprimes) + "   Modifiés : " + str(nb_modifies))

nb_bat_new = 0
nb_bat_mod = 0
nb_bat_del = 0
nb_bat_noMod = 0

# Comptage des batiment de chaque catégorie.
for i_lat in range(NB_ZONE):
    for i_lon in range(NB_ZONE):
        for i_bat in range(len(old_bati[i_lat][i_lon])):
            if old_bati[i_lat][i_lon][i_bat].role == "outer":
                if old_bati[i_lat][i_lon][i_bat].status == "SUPPRIME":
                    nb_bat_del = nb_bat_del +1
        for i_bat in range(len(new_bati[i_lat][i_lon])):
            if new_bati[i_lat][i_lon][i_bat].role == "outer":
                if new_bati[i_lat][i_lon][i_bat].status == "IDENTIQUE":
                    nb_bat_noMod = nb_bat_noMod + 1
                elif new_bati[i_lat][i_lon][i_bat].status == "MODIFIE":
                    nb_bat_mod = nb_bat_mod + 1
                elif new_bati[i_lat][i_lon][i_bat].status == "NOUVEAU":
                    nb_bat_new = nb_bat_new + 1

print("------------------------------------------------------------------")
print("-                    Création des fichiers                       -")
print("------------------------------------------------------------------")
print(str(nb_comparaison) + " comparaisons entre batiments effectuées")
print(str(nb_bat_noMod) + " batiments identiques")
print(str(nb_bat_mod) +  " batiments modifiés")
print(str(nb_bat_new) + " batiments nouveaux")
print(str(nb_bat_del) + " batiments supprimés")

tps3 = time.perf_counter()

file_log = open(adresse + "/" + prefixe + "_log.txt", "w")
file_log.write("Rappel des input : \n")
file_log.write("    BORNE_INF_MODIF : " + str(BORNE_INF_MODIF) + "\n")
file_log.write("    BORNE_SUP_MODIF : " + str(BORNE_SUP_MODIF) + "\n")
file_log.write("    NB_ZONE : " + str(NB_ZONE) + "\n")
file_log.write("Le fichier " + fichier_osm_old + " contient :" + "\n")
file_log.write("    - " + str(old_nbre_nodes) + " noeuds" + "\n")
file_log.write("    - " + str(old_nbre_ways) + " batiments" + "\n")
file_log.write("Le fichier " + fichier_osm_new + " contient :" + "\n")
file_log.write("    - " + str(new_nbre_nodes) + " noeuds" + "\n")
file_log.write("    - " + str(new_nbre_ways) + " batiments" + "\n")
file_log.write("Résultat de la comparaison :" + "\n")
file_log.write("    Nombre de comparaisons effectuées : " + \
    str(nb_comparaison) + "\n")
file_log.write("    Nombre de batiments identiques trouvés : " + \
    str(nb_bat_noMod) + "\n")
file_log.write("    Nombre de batiments modifiés trouvés : " + \
    str(nb_bat_mod) + "\n")
file_log.write("    Nombre de batiments nouveaux trouvés : " + \
    str(nb_bat_new) + "\n")
file_log.write("    Nombre de batiments supprimés trouvés : " + \
    str(nb_bat_del) + "\n")
file_log.write("Temps de lecture des fichiers : " + str(tps2 - tps1) + " secondes." + "\n")
file_log.write("Temps de calcul : " + str(tps3 - tps2) + " secondes." + "\n")
file_log.write("Temps d'execution totale : " + str(tps3 - tps1) + " secondes." + "\n")
file_log.write(separation + "\n")
i_warn = 0
for i_warn in range(len(warning_equilibre)):
    file_log.write(warning_equilibre[i_warn] + "\n")
file_log.write(separation + "\n")
file_log.write("Récapitulatif des batiments issus de " + fichier_osm_new + "\n")
file_log.write(separation + "\n")

for i_lat in range(NB_ZONE):
    for i_lon in range(NB_ZONE):
        for i_bat in range(len(new_bati[i_lat][i_lon])):
            Resultat = [new_bati[i_lat][i_lon][i_bat].bat_id, \
                new_bati[i_lat][i_lon][i_bat].status, \
                str(round(new_bati[i_lat][i_lon][i_bat].dist_mini, 9)), \
                str(round(new_bati[i_lat][i_lon][i_bat].pt_moy.node_lat,7)), \
                str(round(new_bati[i_lat][i_lon][i_bat].pt_moy.node_lon,7)), \
                str(round(new_bati[i_lat][i_lon][i_bat].aire,1))]
            file_log.write(formatLog(Resultat,16,"|") + "\n")
file_log.write(separation + "\n")
file_log.write("Récapitulatif des batiments issus de " + fichier_osm_old + "\n")
file_log.write(separation + "\n")

for i_lat in range(NB_ZONE):
    for i_lon in range(NB_ZONE):
        for i_bat in range(len(old_bati[i_lat][i_lon])):
            #print(old_bati[i_lat][i_lon][i_bat].aire)
            Resultat = [old_bati[i_lat][i_lon][i_bat].bat_id, \
                old_bati[i_lat][i_lon][i_bat].status, \
                str(round(old_bati[i_lat][i_lon][i_bat].dist_mini, 9)), \
                str(round(old_bati[i_lat][i_lon][i_bat].pt_moy.node_lat,7)), \
                str(round(old_bati[i_lat][i_lon][i_bat].pt_moy.node_lon,7)), \
                str(round(old_bati[i_lat][i_lon][i_bat].aire,1))]
            file_log.write(formatLog(Resultat,16,"|") + "\n")
file_log.write(separation + "\n")

nom_file_noMod = prefixe + "_unModified.osm"
file_noMod = open(adresse + "/" + nom_file_noMod, "w")
file_noMod.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>" + "\n")
file_noMod.write("<osm version=\"0.6\" upload=\"true\" generator=\"JOSM\">" + "\n")

nom_file_mod = prefixe + "_mod_1_a_" + str(nb_bat_mod) + ".osm"
file_mod = open(adresse + "/" + nom_file_mod, "w")
file_mod.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>" + "\n")
file_mod.write("<osm version=\"0.6\" upload=\"true\" generator=\"JOSM\">" + "\n")

nom_file_new = prefixe + "_new_1_a_" + str(nb_bat_new) + ".osm"
file_new = open(adresse + "/" + nom_file_new , "w")
file_new.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>" + "\n")
file_new.write("<osm version=\"0.6\" upload=\"true\" generator=\"JOSM\">" + "\n")

nom_file_del = prefixe + "_sup_1_a_" + str(nb_bat_del) + ".osm"
file_del = open(adresse + "/" + nom_file_del , "w")
file_del.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>" + "\n")
file_del.write("<osm version=\"0.6\" upload=\"true\" generator=\"JOSM\">" + "\n")

# Ecriture des nouveaux batiments
enTete = ["STAT", "ANCIEN BAT.", "TOL", "NOUVEAU BAT.", "fichier"]
file_log.write("NOUVEAUX BATIMENTS" + "\n" )
file_log.write(separation + "\n")
file_log.write(formatLog(enTete,16,"|") +"\n")
file_log.write(separation + "\n")
for i_lat in range(NB_ZONE):
    for i_lon in range(NB_ZONE):
        for i_bat in range(len(new_bati[i_lat][i_lon])):
            if new_bati[i_lat][i_lon][i_bat].role == "outer":
                new_bati[i_lat][i_lon][i_bat].export_bat()
                if new_bati[i_lat][i_lon][i_bat].status == "IDENTIQUE":
                    file_noMod.write((new_bati[i_lat][i_lon][i_bat].print_bat + "\n"))
                    Ligne = ["IDENTIQUE", new_bati[i_lat][i_lon][i_bat].bat_id, \
                        str(round(new_bati[i_lat][i_lon][i_bat].dist_mini,9)), \
                        new_bati[i_lat][i_lon][i_bat].id_bat_proche, \
                        nom_file_noMod]
                    file_log.write(formatLog(Ligne,16,"|") + "\n")
                elif new_bati[i_lat][i_lon][i_bat].status == "MODIFIE":
                    file_mod.write((new_bati[i_lat][i_lon][i_bat].print_bat + "\n"))
                    Ligne = ["MODIFIE", new_bati[i_lat][i_lon][i_bat].bat_id, \
                        str(round(new_bati[i_lat][i_lon][i_bat].dist_mini,9)), \
                        new_bati[i_lat][i_lon][i_bat].id_bat_proche, \
                        nom_file_mod]
                    file_log.write(formatLog(Ligne,16,"|") + "\n")
                elif new_bati[i_lat][i_lon][i_bat].status == "NOUVEAU":
                    file_new.write((new_bati[i_lat][i_lon][i_bat].print_bat + "\n"))
                    Ligne = ["NOUVEAU", new_bati[i_lat][i_lon][i_bat].bat_id, \
                        str(round(new_bati[i_lat][i_lon][i_bat].dist_mini,9)), \
                        new_bati[i_lat][i_lon][i_bat].id_bat_proche, \
                        nom_file_new]
                    file_log.write(formatLog(Ligne,16,"|") + "\n")

# Ecriture des anciens batiments (seulement ceux qui sont supprimés)
enTete = ["STAT", "ANCIEN BAT.", "TOL", "fichier"]
file_log.write(separation + "\n")
file_log.write("ANCIENS BATIMENTS" + "\n" )
file_log.write(separation + "\n")
file_log.write(formatLog(enTete,16,"|") +"\n")
file_log.write(separation + "\n")
for i_lat in range(NB_ZONE):
    for i_lon in range(NB_ZONE):
        for i_bat in range(len(old_bati[i_lat][i_lon])):
            if old_bati[i_lat][i_lon][i_bat].role == "outer":
                if old_bati[i_lat][i_lon][i_bat].status == "SUPPRIME":
                    old_bati[i_lat][i_lon][i_bat].export_bat()
                    file_del.write((old_bati[i_lat][i_lon][i_bat].print_bat + "\n"))
                    Ligne = ["SUPPRIME", old_bati[i_lat][i_lon][i_bat].bat_id, \
                        str(round(old_bati[i_lat][i_lon][i_bat].dist_mini,9)), \
                        nom_file_del]
                    file_log.write(formatLog(Ligne,16,"|") + "\n")
# cloture des fichiers osm
file_del.write("</osm>")
file_del.close()
file_noMod.write("</osm>")
file_noMod.close()
file_mod.write("</osm>")
file_mod.close()
file_new.write("</osm>")
file_new.close()
file_log.write(separation + "\n")
# Enregistrement de la 'densité' de batiments.
file_log.write("Densité de batiments issus du fichier " + fichier_osm_old + "\n")
file_log.write(separation + "\n")
enTete = ["",""]
i_zone = 0
while i_zone < NB_ZONE:
    enTete.append(str(i_zone))
    i_zone = i_zone + 1
file_log.write(formatLog(enTete,4," ") + "\n")
for i_lat in range(NB_ZONE):
    densite_old = [str(i_lat) , "|"]
    for i_lon in range(NB_ZONE):
        densite_old.append(str(len(old_bati[i_lat][i_lon])))
    file_log.write(formatLog(densite_old,4," ") + "\n")

file_log.write(separation + "\n")
file_log.write("Densité de batiments issus du fichier " + fichier_osm_new + "\n")
file_log.write(separation + "\n")
file_log.write(formatLog(enTete,4," ") + "\n")
for i_lat in range(NB_ZONE):
    densite_new = [str(i_lat) , "|"]
    for i_lon in range(NB_ZONE):
        densite_new.append(str(len(new_bati[i_lat][i_lon])))
    file_log.write(formatLog(densite_new,4," ") + "\n")
file_log.close()

if mode == "debug":
    # sauvegarde dans un fichier des zones définies
    nom_file_debug = prefixe + "_debug.osm"
    node_id = 100000
    way_id = 1
    file_debug = open(adresse + "/" + nom_file_debug, "w")
    file_debug.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>" + "\n")
    file_debug.write("<osm version=\"0.6\" upload=\"true\" generator=\"JOSM\">" + "\n")
    for i_lat in range(NB_ZONE):
        lat = lat_min + i_lat * delta_lat
        node1 = "  <node id=\"-" + str(node_id) + "\" action=\"modify\" visible=\"true\"" + \
            " lat=\"" + str(lat) + "\" lon=\"" + str(lon_min) + "\" />"
        node2 = "  <node id=\"-" + str(node_id + 1) + "\" action=\"modify\" visible=\"true\"" + \
            " lat=\"" + str(lat) + "\" lon=\"" + str(lon_max) + "\" />"
        way1 = "  <way id=\"-" + str(way_id) + "\" action=\"modify\"" + \
            " visible=\"true\">"
        way2 = "    <nd ref=\"-" + str(node_id) + "\" />"
        way3 = "    <nd ref=\"-" + str(node_id + 1) + "\" />"
        way4 = "  </way>"
        file_debug.write(node1 + "\n")
        file_debug.write(node2 + "\n")
        file_debug.write(way1 + "\n")
        file_debug.write(way2 + "\n")
        file_debug.write(way3 + "\n")
        file_debug.write(way4 + "\n")
        node_id = node_id + 2
        way_id = way_id + 1
    for i_lon in range(NB_ZONE):
        lon = lon_min + i_lon * delta_lon
        node1 = "  <node id=\"-" + str(node_id) + "\" action=\"modify\" visible=\"true\"" + \
            " lat=\"" + str(lat_min) + "\" lon=\"" + str(lon) + "\" />"
        node2 = "  <node id=\"-" + str(node_id + 1) + "\" action=\"modify\" visible=\"true\"" + \
            " lat=\"" + str(lat_max) + "\" lon=\"" + str(lon) + "\" />"
        way1 = "  <way id=\"-" + str(way_id) + "\" action=\"modify\"" + \
            " visible=\"true\">"
        way2 = "    <nd ref=\"-" + str(node_id) + "\" />"
        way3 = "    <nd ref=\"-" + str(node_id + 1) + "\" />"
        way4 = "  </way>"
        file_debug.write(node1 + "\n")
        file_debug.write(node2 + "\n")
        file_debug.write(way1 + "\n")
        file_debug.write(way2 + "\n")
        file_debug.write(way3 + "\n")
        file_debug.write(way4 + "\n")
        node_id = node_id + 2
        way_id = way_id + 1
    # Transcription des points au cdg des batiments
    for i_lat in range(NB_ZONE):
        for i_lon in range(NB_ZONE):
            for i_bat in range(len(new_bati[i_lat][i_lon])):
                new_bati[i_lat][i_lon][i_bat].pt_moy.export_node()
                file_debug.write(new_bati[i_lat][i_lon][i_bat].pt_moy.print_node + "\n")
    file_debug.write("</osm>" + "\n")
    file_debug.close()

print("Durée du calcul : " + str(tps3 - tps2))
print("Durée totale : " + str(tps3-tps1))
print("------------------------------------------------------------------")
print("-                       FIN DU PROCESS                           -")
print("------------------------------------------------------------------")

