'''
Created on May 4, 2020

@author: rbossy
'''

import collections
import itertools
import re
import os.path
import os
import copy
import util

def load(path):
    if os.path.isdir(path):
        for fn in os.listdir(path):
            yield from load(os.path.join(path, fn))
    elif os.path.isfile(path) and path.endswith('.fdp'):
        p = Perso()
        p.parse_file(path)
        yield p, path
        
class Niveau:
    def __init__(self, name):
        self.name = name
Niveau.PJ = Niveau('pj')
Niveau.Pietaille = Niveau('piétaille')
Niveau.Coriace = Niveau('coriace')
Niveau.Rival = Niveau('rival')

class Perso:
    LINE_PATTERN = re.compile(r'(?P<k>\w+)\s*[:=]?\s*(?P<v>.+)', re.RegexFlag.IGNORECASE)
    SHORT_PATTERN = re.compile(r'(?P<niv>\w+)\s+(?P<nom>\w+)\s+(?P<vig>\d)\s*(?P<agi>\d)\s*(?P<esp>\d)\s*(?P<aura>\d)\s+(?P<init>\d)\s*(?P<melee>\d)\s*(?P<tir>\d)\s*(?P<def>\d)\s+(?P<pv>\d+)', re.RegexFlag.IGNORECASE)

    def __init__(self):
        self.niveau = util.Ref(None)
        self.nom = util.Ref(None)
        self.origine = util.Ref(None)
        self.langues = util.Ref([])
        self.attributs = Attributs()
        self.aptitudes_combat = AptitudesCombat(self.attributs)
        self.armure = util.Ref(0)
        self.carrieres = collections.OrderedDict()
        self.avantages = util.Ref([])
        self.desavantages = util.Ref([])
        self.pouvoir = util.Ref(0, modifiable=True)
        self.foi = util.Ref(0, modifiable=True)
        self.creation = util.Ref(0, modifiable=True)
        self.vitalite = util.Ref(0, modifiable=True)
        self.heroisme = util.Ref(0, modifiable=True)
        self.ref_map = {}
        self._add_ref_map(self.niveau, 'niveau', 'niv')
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
        self._add_ref_map(self.armure, 'armure')
        self._add_ref_map(util.Ref(0), 'vigueur/2')
        self._add_ref_map(self.avantages, 'avantages', 'avantage', 'av')
        self._add_ref_map(self.desavantages, 'désavantages', 'desavantages', 'désavantage', 'desavantage', 'défauts', 'defauts', 'défaut', 'defaut')
        self._add_ref_map(self.pouvoir, 'pouvoir', 'pou')
        self._add_ref_map(self.foi, 'foi')
        self._add_ref_map(self.creation, 'création', 'creation', 'créa', 'crea', 'cré', 'cre')
        self._add_ref_map(self.vitalite, 'vitalité', 'vitalite', 'vit', 'vie', 'pv')
        self._add_ref_map(self.heroisme, 'héroïsme', 'héroisme', 'heroïsme', 'heroisme', 'héros', 'heros')
        
    def clone(self, target=None):
        if target is None:
            target = Perso()
        for k, ref in self.ref_map.items():
            target.ref_map[k].value = copy.copy(ref.value)
        return target
        
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
 
    def setv(self, k, v):
        if k in self.ref_map:
            ref = self.ref_map[k]
            try:
                ref.value.append(v)
            except AttributeError:
                try:
                    ref.value = int(v)
                    if ref.modifiable:
                        ref.max = ref.value
                    if ref == self.attributs.vigueur:
                        self.ref_map['vigueur/2'].value = int(ref.value * 0.5)
                except ValueError:
                    ref.value = v
        else:
            ref = util.Ref(v)
            self.carrieres[k] = ref
            names = [k]
            short = k[:3]
            if short != k and short not in self.ref_map:
                names.append(short)
            self._add_ref_map(ref, *names)

    def parse_line(self, line):
        m = Perso.SHORT_PATTERN.match(line)
        if m is not None:
            for k, v in m.groupdict().items():
                self.setv(k, v)
            return
        m = Perso.LINE_PATTERN.match(line)
        if m is not None:
            k = util.snorm(m.group('k'))
            v = m.group('v').strip()
            self.setv(k, v)

    def fiche(self):
        titres = [
                [
                    util.Cell(12, f'{self.nom} ({self.niveau.value})'),
                ],
                [
                    util.Cell(2, 'Origine'),
                    util.Cell(10, self.origine),
                ],
                [
                    util.Cell(2, 'Langues'),
                    util.Cell(10, ', '.join(self.langues.value)),
                ],
                util.HLine,
                [
                    util.Cell(4, 'Attributs', center=True),
                    util.Cell(4, 'Combat', left=True, center=True),
                    util.Cell(4, 'Carrières', left=True, center=True),
                ],
            ]
        scores = [
                [
                    util.Cell(3, 'Vigueur'),
                    util.Cell(1, self.attributs.vigueur),
                    util.Cell(3, 'Initiative', left=True),
                    util.Cell(1, self.aptitudes_combat.initiative),
                ],
                [
                    util.Cell(3, 'Agilité'),
                    util.Cell(1, self.attributs.agilite),
                    util.Cell(3, 'Mélée', left=True),
                    util.Cell(1, self.aptitudes_combat.melee),
                ],
                [
                    util.Cell(3, 'Esprit'),
                    util.Cell(1, self.attributs.esprit),
                    util.Cell(3, 'Tir', left=True),
                    util.Cell(1, self.aptitudes_combat.tir),
                ],
                [
                    util.Cell(3, 'Aura'),
                    util.Cell(1, self.attributs.aura),
                    util.Cell(3, 'Défense', left=True),
                    util.Cell(1, self.aptitudes_combat.defense),
                    # XXX carriere
                ],
            ]
        carrieres = list(self.carrieres.items())
        for i in range(0, min(4, len(carrieres))):
            c, n = carrieres[i]
            scores[i].extend([
                    util.Cell(3, c.capitalize(), left=True),
                    util.Cell(1, n)
                ])
        for i in range(len(carrieres), 4):
            scores[i].append(util.Cell(4, '', left=True))
        for i in range(4, len(carrieres)):
            c, n = carrieres[i]
            scores.append([
                    util.Cell(8, ''),
                    util.Cell(3, c.capitalize(), left=True),
                    util.Cell(1, n)
                ])
        avantages = [
                [
                    util.Cell(6, 'Avantages', center=True, left=True),
                    util.Cell(6, 'Désavantages', center=True, left=True),
                ]
            ]
        for a, d in itertools.zip_longest(self.avantages.value, self.desavantages.value):
            avantages.append([
                    util.Cell(6, '' if a is None else a.capitalize(), left=True),
                    util.Cell(6, '' if d is None else d.capitalize(), left=True)
                ])
        gros_titres = [
                    util.Cell(3, 'Vitalité', center=True),
                    util.Cell(3, 'Héroïsme', center=True),
                ]
        gros_scores = [
                    util.Cell(3, self.vitalite, center=True),
                    util.Cell(3, self.heroisme, center=True)
            ]
        if self.pouvoir.value:
            gros_titres.append(util.Cell(2, 'Pouvoir', center=True))
            gros_scores.append(util.Cell(2, self.pouvoir, center=True))
        if self.foi.value:
            gros_titres.append(util.Cell(2, 'Foi', center=True))
            gros_scores.append(util.Cell(2, self.foi, center=True))
        if self.creation.value:
            gros_titres.append(util.Cell(2, 'Création', center=True))
            gros_scores.append(util.Cell(2, self.creation, center=True))
        result = '```'
        for line in titres + scores + [util.HLine, gros_titres, gros_scores, util.HLine] + avantages:
            for util.Cell in line:
                result += util.Cell.render(6)
            result+= '\n'
        return result + '```'

class Attributs:
    def __init__(self):
        self.vigueur = util.Ref(0)
        self.agilite = util.Ref(0)
        self.esprit = util.Ref(0)
        self.aura = util.Ref(0)

class AptitudesCombat:
    def __init__(self, attributs):
        self.initiative = util.Ref(0, auto_ref=attributs.esprit)
        self.melee = util.Ref(0, auto_ref=attributs.vigueur)
        self.tir = util.Ref(0, auto_ref=attributs.agilite)
        self.defense = util.Ref(0)
