'''
Created on May 4, 2020

@author: rbossy
'''

import collections
import itertools
import re
import os
import os.path

def load(path):
    if os.path.isdir(path):
        for fn in os.listdir(path):
            yield from load(os.path.join(path, fn))
    elif os.path.isfile(path) and path.endswith('.fdp'):
        p = Perso()
        p.parse_file(path)
        yield p, path

class Ref:
    def __init__(self, value, name=None):
        self.value = value
        self.name = name
        
    def __str__(self):
        return str(self.value)
    
    def __iadd__(self, other):
        self.value += other
        
    def __isub__(self, other):
        self.value -= other
        
    def is_int(self):
        try:
            int(self.value)
            return True
        except ValueError:
            return False

class Niveau:
    def __init__(self, name):
        self.name = name
Niveau.PJ = Niveau('pj')
Niveau.Pietaille = Niveau('piétaille')
Niveau.Coriace = Niveau('coriace')
Niveau.Rival = Niveau('rival')

class Perso:
    LINE_PATTERN = re.compile(r'(?P<k>\w+)\s*[:=]?\s*(?P<v>.+)', re.RegexFlag.IGNORECASE)
    def __init__(self):
        self.niveau = Ref(None)
        self.nom = Ref(None)
        self.origine = Ref(None)
        self.langues = Ref([])
        self.attributs = Attributs()
        self.aptitudes_combat = AptitudesCombat()
        self.carrieres = collections.OrderedDict()
        self.avantages = Ref([])
        self.desavantages = Ref([])
        self.pouvoir = Ref(0)
        self.foi = Ref(0)
        self.creation = Ref(0)
        self.vitalite = Ref(0)
        self.heroisme = Ref(0)
        self.ref_map = {}
        self._add_ref_map(self.nom, 'nom')
        self._add_ref_map(self.origine, 'origine')
        self._add_ref_map(self.langues, 'langues', 'langue', 'lang')
        self._add_ref_map(self.attributs.vigueur, 'vigueur', 'vig', 'vi', 'v')
        self._add_ref_map(self.attributs.agilite, 'agilité', 'agilite', 'agi', 'ag')
        self._add_ref_map(self.attributs.esprit, 'esprit', 'esp', 'es', 'e')
        self._add_ref_map(self.attributs.aura, 'aura')
        self._add_ref_map(self.aptitudes_combat.initiative, 'initiative', 'init', 'ini', 'i')
        self._add_ref_map(self.aptitudes_combat.melee, 'mélée', 'mélee', 'melée', 'melee', 'mel', 'me')
        self._add_ref_map(self.aptitudes_combat.tir, 'tir', 'ti', 't')
        self._add_ref_map(self.aptitudes_combat.defense, 'défense', 'defense', 'déf', 'def', 'd')
        self._add_ref_map(self.avantages, 'avantages', 'avantage', 'av')
        self._add_ref_map(self.desavantages, 'désavantages', 'desavantages', 'désavantage', 'desavantage', 'défauts', 'defauts', 'défaut', 'defaut')
        self._add_ref_map(self.pouvoir, 'pouvoir', 'pou')
        self._add_ref_map(self.foi, 'foi')
        self._add_ref_map(self.creation, 'création', 'creation', 'créa', 'crea', 'cré', 'cre')
        self._add_ref_map(self.vitalite, 'vitalité', 'vitalite', 'vit', 'vie', 'pv')
        self._add_ref_map(self.heroisme, 'héroïsme', 'héroisme', 'heroïsme', 'heroisme', 'héros', 'heros')
        
    def _add_ref_map(self, ref, *keys):
        for k in keys:
            if k in self.ref_map:
                raise RuntimeError(f'duplicate ref key {k}')
            self.ref_map[k] = ref
            if ref.name is None:
                ref.name = k

    def parse_file(self, f):
        if isinstance(f, str):
            with open(f) as fp:
                self.parse_file(fp)
        else:
            for line in f:
                line = line.strip()
                if line != '':
                    self.parse_line(line)
 
    def parse_line(self, line):
        m = Perso.LINE_PATTERN.match(line)
        if m is not None:
            k = m.group('k').lower()
            v = m.group('v').strip()
            if k in self.ref_map:
                try:
                    self.ref_map[k].value.append(v)
                except AttributeError:
                    self.ref_map[k].value = v
            else:
                ref = Ref(v)
                self.carrieres[k] = ref
                names = [k]
                short = k[:3]
                if short != k and short not in self.ref_map:
                    names.append(short)
                self._add_ref_map(ref, *names)

    def fiche(self):
        titres = [
                [
                    Cell(12, f'{self.nom} ({self.niveau.name})'),
                ],
                [
                    Cell(2, 'Origine'),
                    Cell(10, self.origine),
                ],
                [
                    Cell(2, 'Langues'),
                    Cell(10, ', '.join(self.langues.value)),
                ],
                HLine,
                [
                    Cell(4, 'Attributs', center=True),
                    Cell(4, 'Combat', left=True, center=True),
                    Cell(4, 'Carrières', left=True, center=True),
                ],
            ]
        scores = [
                [
                    Cell(3, 'Vigueur'),
                    Cell(1, self.attributs.vigueur),
                    Cell(3, 'Initiative', left=True),
                    Cell(1, self.aptitudes_combat.initiative),
                ],
                [
                    Cell(3, 'Agilité'),
                    Cell(1, self.attributs.agilite),
                    Cell(3, 'Mélée', left=True),
                    Cell(1, self.aptitudes_combat.melee),
                ],
                [
                    Cell(3, 'Esprit'),
                    Cell(1, self.attributs.esprit),
                    Cell(3, 'Tir', left=True),
                    Cell(1, self.aptitudes_combat.tir),
                ],
                [
                    Cell(3, 'Aura'),
                    Cell(1, self.attributs.aura),
                    Cell(3, 'Défense', left=True),
                    Cell(1, self.aptitudes_combat.defense),
                    # XXX carriere
                ],
            ]
        carrieres = list(self.carrieres.items())
        for i in range(0, min(4, len(carrieres))):
            c, n = carrieres[i]
            scores[i].extend([
                    Cell(3, c.capitalize(), left=True),
                    Cell(1, n)
                ])
        for i in range(len(carrieres), 4):
            scores[i].append(Cell(4, '', left=True))
        for i in range(4, len(carrieres)):
            c, n = carrieres[i]
            scores.append([
                    Cell(8, ''),
                    Cell(3, c.capitalize(), left=True),
                    Cell(1, n)
                ])
        avantages = [
                [
                    Cell(6, 'Avantages', center=True, left=True),
                    Cell(6, 'Désavantages', center=True, left=True),
                ]
            ]
        for a, d in itertools.zip_longest(self.avantages.value, self.desavantages.value):
            avantages.append([
                    Cell(6, '' if a is None else a.capitalize(), left=True),
                    Cell(6, '' if d is None else d.capitalize(), left=True)
                ])
        gros_titres = [
                    Cell(3, 'Vitalité', center=True),
                    Cell(3, 'Héroïsme', center=True),
                ]
        gros_scores = [
                    Cell(3, self.vitalite, center=True),
                    Cell(3, self.heroisme, center=True)
            ]
        if self.pouvoir.value:
            gros_titres.append(Cell(2, 'Pouvoir', center=True))
            gros_scores.append(Cell(2, self.pouvoir, center=True))
        if self.foi.value:
            gros_titres.append(Cell(2, 'Foi', center=True))
            gros_scores.append(Cell(2, self.foi, center=True))
        if self.creation.value:
            gros_titres.append(Cell(2, 'Création', center=True))
            gros_scores.append(Cell(2, self.creation, center=True))
        result = '```'
        for line in titres + scores + [HLine, gros_titres, gros_scores, HLine] + avantages:
            for cell in line:
                result += cell.render(6)
            result+= '\n'
        return result + '```'

class Attributs:
    def __init__(self):
        self.vigueur = Ref(0)
        self.agilite = Ref(0)
        self.esprit = Ref(0)
        self.aura = Ref(0)

class AptitudesCombat:
    def __init__(self):
        self.initiative = Ref(0)
        self.melee = Ref(0)
        self.tir = Ref(0)
        self.defense = Ref(0)
        
class Cell:
    def __init__(self, span, text, left=False, right=False, center=False, fillchar=' '):
        self.span = span
        if isinstance(text, Ref):
            self.text = text.value
        else:
            self.text = text
        if self.text is None:
            self.text = '---'
        else:
            self.text = str(self.text)
        self.left = left
        self.right = right
        self.center = center
        self.fillchar = fillchar

    def render(self, width=6):
        w = width * self.span
        if self.left:
            w -= 2
        if self.right:
            w -= 2
        if self.center:
            r = self.text.center(w, self.fillchar)
        else:
            r = self.text.ljust(w, self.fillchar)
        if self.left:
            r = '| ' + r 
        if self.right:
            r += ' |'
        return r

HLine = [Cell(12, '', fillchar='-')]
