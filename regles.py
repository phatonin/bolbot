'''
Created on May 5, 2020

@author: rbossy
'''

import random
import re

DICE_PATTERN = re.compile(r'(?P<dice_number>\d+)d(?P<dice_type>\d+)(?P<additional>[MB]*)', re.RegexFlag.IGNORECASE)

def parse_dice(expr):
    m = DICE_PATTERN.match(expr)
    if m is not None:
        return {
            'dice_number': int(m.group('dice_number')),
            'dice_type': int(m.group('dice_type')),
            'bonus': m.group('additional').count('B'),
            'malus': m.group('additional').count('M'),
        }
    raise ValueError(expr)

def lance(dice_number=1, dice_type=6, bonus=0, malus=0):
    number_rolled = dice_number + bonus + malus
    dice = [random.randint(1, dice_type) for _ in range(number_rolled)]
    sorted_dice = sorted(dice)
    for _ in range(bonus):
        sorted_dice.pop(0)
    for _ in range(malus):
        sorted_dice.pop(-1)
    result = sum(sorted_dice)
    return sorted(dice), sorted_dice, result

class Reussite:
    def __init__(self, succes, name):
        self.succes = succes
        self.name = name
        
    @staticmethod
    def quel(dice, result):
        if dice == [1, 1]:
            return Reussite.ECHEC_AUTOMATIQUE
        if dice == [6, 6]:
            return Reussite.SUCCES_HEROIQUE
        if result >= 9:
            return Reussite.SUCCES
        return Reussite.ECHEC
Reussite.ECHEC_CRITIQUE = Reussite(False, 'échec critique')
Reussite.ECHEC_AUTOMATIQUE = Reussite(False, 'échec automatique')
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

def sum_scores(scores):
    score_total = sum(sign * int(ref.value) for sign, ref in scores)
    sign = 1 if score_total >= 0 else -1
    mod = abs(score_total)
    return score_total, sign, mod

def jet(scores, bonus, malus):
    dice, sorted_dice, result = lance(2, 6, bonus, malus)
    score_total, sign, mod = sum_scores(scores)
    final = result + score_total
    return sign, mod, dice, final, Reussite.quel(sorted_dice, final)



