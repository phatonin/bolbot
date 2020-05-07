'''
Created on May 5, 2020

@author: rbossy
'''

import random
import perso
import re

def lance(number_read=1, dice_type=6, bonus=0, malus=0, sign=1, mod=0):
    number_rolled = number_read + bonus + malus
    dice = [random.randint(1, dice_type) for _ in range(number_rolled)]
    sorted_dice = sorted(dice)
    for _ in range(bonus):
        sorted_dice.pop(0)
    for _ in range(malus):
        sorted_dice.pop(-1)
    result = sum(sorted_dice) + sign * mod
    return dice, sorted_dice, result

class Reussite:
    def __init__(self, succes, name):
        self.succes = succes
        self.name = name
        
    @staticmethod
    def quel(dice, result):
        if dice == [1, 1]:
            return Reussite.ECHEC_CRITIQUE
        if dice == [6, 6]:
            return Reussite.SUCCES_HEROIQUE
        if result >= 9:
            return Reussite.SUCCES
        return Reussite.ECHEC
Reussite.ECHEC_CRITIQUE = Reussite(False, 'échec critique')
Reussite.ECHEC = Reussite(False, 'échec')
Reussite.SUCCES = Reussite(True, 'succès')
Reussite.SUCCES_HEROIQUE = Reussite(True, 'succès héroïque')
Reussite.SUCCES_LEGENDAIRE = Reussite(True, 'succès légendaire')

class Difficulte:
    MAP = {}
    def __init__(self, sign, mod, name, *keys):
        self.sign = sign
        self.mod = mod
        self.name = name
        Difficulte.MAP[name] = self
        for k in keys:
            Difficulte.MAP[k] = self
Difficulte.TRES_FACILE = Difficulte(1, 2, 'très facile', 'tres facile', 'tresfacile', 'tfacile', 'tfac')
Difficulte.FACILE = Difficulte(1, 1, 'facile', 'fac')
Difficulte.MOYENNE = Difficulte(1, 0, 'moyenne', 'moy')
Difficulte.ARDUE = Difficulte(-1, 1, 'ardue', 'ard', 'hard')
Difficulte.DIFFICILE = Difficulte(-1, 2, 'difficile', 'diff')
Difficulte.TRES_DIFFICILE = Difficulte(-1, 4, 'très difficile', 'tres difficile', 'tresdifficile', 'tdifficile', 'tdiff')
Difficulte.IMPOSSIBLE = Difficulte(-1, 6, 'impossible', 'impo')
Difficulte.HEROIQUE = Difficulte(-1, 8, 'héroïque', 'héroique', 'heroïque', 'heroique')

def _try_int(v):
    try:
        int(v)
        return True
    except ValueError:
        return False        

MENTION_PATTERN = re.compile(r'^<@!\d+>$')
def parse_jet(le_perso, tokens):
    poubelle = []
    scores = []
    bonus = 0
    malus = 0
    sign = 1
    for t in tokens:
        t = t.lower()
        if MENTION_PATTERN.match(t):
            sign = 1
        elif _try_int(t):
            i = int(t)
            if i < 0:
                scores.append((-1, perso.Ref(abs(i), t)))
            else:
                scores.append((sign, perso.Ref(i, t)))
            sign = 1
        elif t == 'b' or t == 'bonus':
            bonus += 1
            sign = 1
        elif t == 'm' or t == 'malus':
            malus += 1
            sign = 1
        elif t == '-':
            sign = -1
        elif t == '+':
            sign = 1
        elif t in Difficulte.MAP:
            d = Difficulte.MAP[t]
            scores.append((d.sign, perso.Ref(d.mod, d.name)))
            sign = 1
        elif t in le_perso.ref_map:
            ref = le_perso.ref_map[t]
            if _try_int(ref.value):
                scores.append((sign, ref))
            else:
                poubelle.append(t)
            sign = 1
        elif t in le_perso.avantages.value:
            bonus += 1
            sign = 1
        elif t in le_perso.desavantages.value:
            malus += 1
            sign = 1
        elif t in perso.TOUS:
            sign = 1
        else:
            poubelle.append(t)
            sign = 1
    return scores, bonus, malus, poubelle

def jet(le_perso, tokens):
    scores, bonus, malus, poubelle = parse_jet(le_perso, tokens)
    score_total = sum(sign * int(ref.value) for sign, ref in scores)
    sign = 1 if score_total >= 0 else -1
    mod = abs(score_total)
    dice, sorted_dice, result = lance(2, 6, bonus, malus, sign, mod)
    return scores, bonus, malus, poubelle, sign, mod, dice, result, Reussite.quel(sorted_dice, result)



